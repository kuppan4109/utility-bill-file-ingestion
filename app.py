# app.py
import os
import logging
from typing import Any, Dict, Optional, List, Tuple

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

# Extractors (existing, must remain)
from extractors.pdfco import PDFcoExtractor
from extractors.openai_extractor import OpenAIExtractor

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("bill-worker")

app = FastAPI(title="Utility Bill Parser", version="1.0.3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
#  Database Connection
# ======================================================
def _pg_conn_info() -> Dict[str, Any]:
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return {"dsn": db_url}
    return {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "5432")),
        "dbname": os.getenv("PGDATABASE", "utility_bills"),
        "user": os.getenv("PGUSER", "billuser"),
        "password": os.getenv("PGPASSWORD", "billpass123"),
    }

def get_db():
    info = _pg_conn_info()
    if "dsn" in info:
        return psycopg2.connect(info["dsn"])
    return psycopg2.connect(**info)

# ======================================================
#  Helper Functions
# ======================================================
def parse_date(x: Optional[str]) -> Optional[str]:
    if not x:
        return None
    xs = str(x).strip()
    if not xs:
        return None
    from datetime import datetime
    import re
    fmts = [
        "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y",
        "%m-%d-%y", "%Y/%m/%d", "%d-%b-%Y",
        "%b %d, %Y", "%b %d,%Y", "%B %d, %Y", "%B %d,%Y"
    ]
    for f in fmts:
        try:
            return datetime.strptime(xs, f).strftime("%Y-%m-%d")
        except Exception:
            pass
    m = re.match(r"^\s*(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\s*$", xs)
    if m:
        mm, dd, yy = m.groups()
        yy = int(yy)
        if yy < 100:
            yy = 2000 + yy
        return f"{yy:04d}-{int(mm):02d}-{int(dd):02d}"
    if re.match(r"^\d{4}-\d{2}-\d{2}$", xs):
        return xs
    return None

def normalize_fields(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map extractor output into DB contract fields (non-negotiable)."""
    def _num(x):
        try:
            return float(x) if x is not None else None
        except Exception:
            return None

    first_meter = None
    if isinstance(raw.get("meters"), list) and raw["meters"]:
        first = raw["meters"][0]
        if isinstance(first, dict):
            first_meter = first.get("meter_number")

    return {
        # property_name: fall back to customer_name (additive)
        "property_name": raw.get("property_name") or raw.get("customer_name"),
        "utility_provider": raw.get("provider_name") or raw.get("vendor_name"),
        "utility_type": raw.get("utility_type"),
        "account_number": raw.get("account_number"),
        "meter_serial_number": raw.get("meter_number") or first_meter,

        "billing_date": parse_date(raw.get("invoice_date") or raw.get("statement_issued")),
        "billing_start_date": parse_date(raw.get("service_start")),
        "billing_end_date": parse_date(raw.get("service_end")),
        "due_date": parse_date(raw.get("due_date") or raw.get("amount_due_by")),

        "current_charges": _num(raw.get("current_charges")),
        "previous_balance": _num(raw.get("previous_balance")),
        "past_due_balance": _num(raw.get("past_due_balance")),
        "total_amount_due": _num(raw.get("total_amount_due") or raw.get("amount_due")),

        "units_used": _num(raw.get("total_usage")),
        "unit_type": raw.get("usage_unit"),

        "payments": _num(raw.get("payments")),
        "balance_forward": _num(raw.get("balance_forward")),

        "water_charges": _num(raw.get("water_charges")),
        "sewer_charges": _num(raw.get("sewer_charges")),
        "storm_water_charges": _num(raw.get("storm_water_charges")),
        "environmental_fee": _num(raw.get("environmental_fee")),
        "trash_charges": _num(raw.get("trash_charges")),
        "gas_charges": _num(raw.get("gas_charges")),
        "electric_charges": _num(raw.get("electric_charges")),

        "rate_plan": raw.get("rate_plan"),
        "service_days": raw.get("service_days"),

        "confidence_score": raw.get("confidence", raw.get("confidence_score", 0.7)),
        "raw_extracted_data": raw,
    }

# ======================================================
#  Validation + Confidence (MANDATORY)
# ======================================================
def _date_ok(start: Optional[str], end: Optional[str]) -> bool:
    if not start or not end:
        return True
    try:
        from datetime import datetime
        s = datetime.strptime(start, "%Y-%m-%d").date()
        e = datetime.strptime(end, "%Y-%m-%d").date()
        return e >= s
    except Exception:
        return False

def validate_normalized(norm: Dict[str, Any]) -> Tuple[bool, List[str]]:
    issues: List[str] = []

    if not norm.get("utility_provider"):
        issues.append("missing_utility_provider")

    acct = norm.get("account_number")
    if not acct or len(str(acct)) < 6:
        issues.append("invalid_account_number")

    amt = norm.get("total_amount_due")
    try:
        if amt is None or float(amt) <= 0:
            issues.append("invalid_total_amount_due")
    except Exception:
        issues.append("invalid_total_amount_due")

    # billing_end >= billing_start when both exist
    if norm.get("billing_start_date") and norm.get("billing_end_date"):
        if not _date_ok(norm.get("billing_start_date"), norm.get("billing_end_date")):
            issues.append("service_period_inverted")

    # usage must have unit_type
    if norm.get("units_used") is not None and not norm.get("unit_type"):
        issues.append("usage_missing_unit")

    # trash bills may not have meters or usage
    if norm.get("utility_type") == "trash":
        if norm.get("meter_serial_number"):
            issues.append("trash_has_meter")
        if norm.get("units_used") is not None:
            issues.append("trash_has_usage")

    return (len(issues) == 0), issues

def score_confidence(method: str, norm: Dict[str, Any], issues: List[str]) -> float:
    conf = 0.70 if method == "pdfco" else 0.80

    # Missing required fields penalties
    for key in ("missing_utility_provider", "invalid_account_number", "invalid_total_amount_due"):
        if key in issues:
            conf -= 0.20

    # Invalid date penalty
    if "service_period_inverted" in issues:
        conf -= 0.10

    # Usage without unit penalty
    if "usage_missing_unit" in issues:
        conf -= 0.05

    # Corroboration bonus (lightweight heuristic)
    corroborated = 0
    if norm.get("billing_date") and norm.get("billing_end_date"):
        corroborated += 1
    if norm.get("previous_balance") is not None and norm.get("balance_forward") is not None:
        corroborated += 1
    if corroborated >= 2:
        conf += 0.05

    return max(0.0, min(1.0, conf))

# ======================================================
#  DB functions (unchanged)
# ======================================================
def create_bill_stub() -> int:
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO bills (created_at, updated_at)
            VALUES (NOW(), NOW())
            RETURNING id
        """)
        bill_id = cur.fetchone()[0]
        conn.commit()
        return bill_id
    finally:
        cur.close()
        conn.close()

def save_to_database(bill_id: int, data: Dict[str, Any], method: str):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE bills SET
                property_name=%(property_name)s,
                utility_provider=%(utility_provider)s,
                utility_type=%(utility_type)s,
                account_number=%(account_number)s,
                meter_serial_number=%(meter_serial_number)s,
                billing_date=%(billing_date)s,
                billing_start_date=%(billing_start_date)s,
                billing_end_date=%(billing_end_date)s,
                due_date=%(due_date)s,
                current_charges=%(current_charges)s,
                previous_balance=%(previous_balance)s,
                past_due_balance=%(past_due_balance)s,
                total_amount_due=%(total_amount_due)s,
                units_used=%(units_used)s,
                unit_type=%(unit_type)s,
                payments=%(payments)s,
                balance_forward=%(balance_forward)s,
                water_charges=%(water_charges)s,
                sewer_charges=%(sewer_charges)s,
                storm_water_charges=%(storm_water_charges)s,
                environmental_fee=%(environmental_fee)s,
                trash_charges=%(trash_charges)s,
                gas_charges=%(gas_charges)s,
                electric_charges=%(electric_charges)s,
                rate_plan=%(rate_plan)s,
                service_days=%(service_days)s,
                extraction_method=%(extraction_method)s,
                confidence_score=%(confidence_score)s,
                requires_review=%(requires_review)s,
                raw_extracted_data=%(raw_extracted_data)s,
                updated_at=NOW()
            WHERE id=%(bill_id)s
            """,
            {
                **data,
                "extraction_method": method,
                "requires_review": (data.get("confidence_score") or 0) < 0.70,
                "raw_extracted_data": Json(data.get("raw_extracted_data", {})),
                "bill_id": bill_id,
            },
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()

# ======================================================
#  Routes
# ======================================================
@app.get("/health")
def health():
    return {"ok": True}

@app.post("/parse-file")
async def parse_file(file: UploadFile = File(...)):
    """
    Strategy (STRICT ORDER):
    1. Attempt PDF.co extraction FIRST if API key exists
    2. Validate extracted data + compute confidence
    3. If validation fails OR confidence < 0.70 -> FALL BACK to OpenAI
    4. Save best result
    """
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    bill_id = create_bill_stub()

    extractor_used = None
    raw: Dict[str, Any] = {}
    norm: Dict[str, Any] = {}

    pdfco_key = os.getenv("PDFCO_API_KEY", "").strip()

    if pdfco_key:
        logger.info("Extractor attempted: pdfco")
        try:
            raw = PDFcoExtractor().extract(pdf_bytes)
            norm = normalize_fields(raw)
            ok, issues = validate_normalized(norm)
            conf = score_confidence("pdfco", norm, issues)
            norm["confidence_score"] = conf
            norm["raw_extracted_data"]["confidence"] = conf

            logger.info("Fingerprint matched: %s", raw.get("vendor_name"))
            logger.info("Confidence score: %.2f", conf)

            if (not ok) or conf < 0.70:
                logger.warning("Fallback triggered: pdfco invalid (%s)", issues)
                raise ValueError(f"pdfco invalid: {issues}")

            extractor_used = "pdfco"
        except Exception as e:
            logger.warning("PDF.co failed -> OpenAI fallback (%s)", e)

    if extractor_used is None:
        logger.info("Extractor attempted: openai")
        raw = OpenAIExtractor().extract(pdf_bytes)
        norm = normalize_fields(raw)
        ok, issues = validate_normalized(norm)
        conf = score_confidence("openai", norm, issues)
        norm["confidence_score"] = conf
        norm["raw_extracted_data"]["confidence"] = conf

        logger.info("Confidence score: %.2f", conf)
        extractor_used = "openai"

    save_to_database(bill_id, norm, extractor_used)

    return JSONResponse(
        {
            "status": "success",
            "bill_id": bill_id,
            "extraction_method": extractor_used,
            "data": norm,
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8080")),
        reload=True,
    )
