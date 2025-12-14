# extractors/pdfco.py
import os, re, logging, requests
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

PDFCO_BASE = "https://api.pdf.co/v1"
PDFCO_API_KEY = os.getenv("PDFCO_API_KEY", "ganeshraju@gmail.com_kTEordfTmPmBRfq5UyPcUputhDRdcl6PqzRNr3Ld4zrKxlmxnGFSY7KiH3OfZljh")

# Vendor enhancement dispatcher (vendor-specific logic lives in vendor modules)
try:
    from extractors.vendors import apply_vendor_enhancements
except Exception:
    apply_vendor_enhancements = None

def pdf_to_text(pdf_bytes: bytes) -> str:
    if not PDFCO_API_KEY:
        raise RuntimeError("PDFCO_API_KEY not set")
    up = requests.post(
        f"{PDFCO_BASE}/file/upload",
        headers={"x-api-key": PDFCO_API_KEY},
        files={"file": ("bill.pdf", pdf_bytes, "application/pdf")},
        timeout=120,
    )
    up.raise_for_status()
    file_url = up.json()["url"]

    conv = requests.post(
        f"{PDFCO_BASE}/pdf/convert/to/text",
        headers={"x-api-key": PDFCO_API_KEY, "Content-Type": "application/json"},
        json={"url": file_url, "inline": True},
        timeout=120,
    )
    conv.raise_for_status()
    data = conv.json()
    if data.get("error"):
        raise RuntimeError(f"PDF.co convert error: {data.get('message')}")
    return data.get("body", "") or ""

def _clean_amt(v: str | None) -> float | None:
    """Common numeric cleaner (safe across vendors)."""
    if not v:
        return None
    s = str(v)
    s = s.replace("$", "").replace("", "").replace(",", "").strip()
    credit = "cr" in s.lower()
    s = re.sub(r"\bcr\b", "", s, flags=re.I).strip()
    s = re.sub(r"[^0-9.\-+]", "", s)
    try:
        n = float(s)
        return -n if credit else n
    except Exception:
        return None

def _find(pat: str, txt: str, flags=re.IGNORECASE):
    m = re.search(pat, txt, flags)
    return m.group(1).strip() if m else None

def _find_all(pat: str, txt: str, flags=re.IGNORECASE):
    return re.findall(pat, txt, flags)

def parse_bill_text(txt: str) -> Dict[str, Any]:
    # -----------------------------
    # Generic extraction ONLY.
    # Vendor-specific operations are applied via apply_vendor_enhancements().
    # -----------------------------
    provider_name   = _find(r"(?im)^(.*?(Utilities|Energy|Water|Power).*)$", txt)

    if (not provider_name) or re.search(r"""(?i)amount\s*due|keep this portion|
                                        please return|and\s+services|help\s+your\s+neighbors|
                                        sharing\s+the\s+warmth|please\s+pay\s+past\s+due""", provider_name or ""):
        tight = (
            _find(r"(?im)^\s*(ATMOS\s+ENERGY)\b.*$", txt)
            or _find(r"(?im)^\s*(Dallas\s+Water\s+Utilities)\b.*$", txt)
            or _find(r"(?im)^\s*(City\s+of\s+Dallas(?:\s+Water\s+Utilities)?)\b.*$", txt)
            or _find(r"(?im)^\s*(TXU\s+Energy)\b.*$", txt)
            or _find(r"(?im)^\s*(Reliant\s+Energy)\b.*$", txt)
        )
        if tight:
            provider_name = tight

    customer_name   = _find(r"Customer\s*Name:\s*(.+)", txt)
    if customer_name:
        customer_name = re.sub(r"\s{2,}DUE\s*DATE.*$", "", customer_name, flags=re.I).strip()

    # Existing account regex (kept)
    account_number  = _find(r"(?:Account(?:\s*Number)?|Acct\.?\s*No\.?)\s*[:#]?\s*([A-Za-z0-9\-]{6,})", txt)

    # Additive: prefer numeric account numbers if present (prevents capturing 'summary')
    m_num = re.search(r"(?i)\bAccount\s*number\s*([0-9][0-9\s]{5,})", txt)
    if m_num:
        acct = re.sub(r"\D+", "", m_num.group(1))
        if len(acct) >= 6:
            account_number = acct

    service_address = _find(r"Service\s*Address:\s*(.+)", txt)
    mailing_address = _find(r"Mail(?:ing)?\s*Address:\s*(.+)", txt)

    statement_issued = _find(r"(?:Invoice\s*Issued|Issued|Statement\s*Date|Bill\s*Date)\s*([0-9/.\-]+)", txt)
    amount_due_by    = _find(r"Amount\s*Due\s*by\s*([0-9/.\-]+)", txt)
    due_date_pref    = _find(r"(?i)\bDUE\s*DATE\s*[:\-]?\s*([0-9/.-]+)", txt) or amount_due_by
    amount_due_after = _find(r"Amount\s*Due\s*after\s*([0-9/.\-]+)", txt)
    service_start    = _find(r"Service\s*(?:Period\s*)?(?:From)?\s*([0-9/.\-]+)\s*to", txt)
    service_end      = _find(r"\bto\b\s*([0-9/.\-]+)\s*(?:for\s*\d+\s*days)?", txt)

    if not statement_issued:
        statement_issued = _find(r"(?i)Billing\s*Date\s*[:\-]?\s*([0-9/.-]+)", txt)

    if not service_start or not service_end:
        _m = re.search(r"(?im)^\s*\d{5,}\s+([0-9/.-]+)\s+([0-9/.-]+)\s+\d+", txt)
        if _m:
            service_start = service_start or _m.group(1)
            service_end   = service_end or _m.group(2)

    total_amount_due       = _clean_amt(_find(r"(?:Total\s*Amount\s*Due|Amount\s*Due|Total\s*Due)\s*[:$]?\s*([\d,]+\.\d{2})", txt))
    total_current_charges  = _clean_amt(_find(r"(?:Total\s*Current\s*Charges|Current\s*Charges)\s*[:$]?\s*([\d,]+\.\d{2})", txt))
    previous_balance       = _clean_amt(_find(r"Previous\s*Balance\s*[:$]?\s*([\d,]+\.\d{2})", txt))
    payments               = _clean_amt(_find(r"Payment\(s\)\s*\(?\$?\s*([\d,]+\.\d{2})\)?", txt))
    balance_forward        = _clean_amt(_find(r"Balance\s*Forward\s*[:$]?\s*([\d,]+\.\d{2})", txt))
    past_due               = _clean_amt(_find(r"(?:Past\s*Due|Past\s*Due\s*Balance)\s*[:$]?\s*([\d,]+\.\d{2})", txt))

    water_charges          = _clean_amt(_find(r"Water\s*Charges\s*[:$]?\s*([\d,]+\.\d{2})", txt))
    sewer_charges          = _clean_amt(_find(r"Sewer\s*Charges\s*[:$]?\s*([\d,]+\.\d{2})", txt))
    storm_water_charges    = _clean_amt(_find(r"Storm\s*Water\s*Charges\s*[:$]?\s*([\d,]+\.\d{2})", txt))
    environmental_fee      = _clean_amt(_find(r"Environmental\s*(?:Cleanup\s*)?Fee\s*[:$]?\s*([\d,]+\.\d{2})", txt))
    trash_charges          = _clean_amt(_find(r"(?:Trash|Refuse)\s*Charges\s*[:$]?\s*([\d,]+\.\d{2})", txt))
    gas_charges            = _clean_amt(_find(r"Gas\s*Charges\s*[:$]?\s*([\d,]+\.\d{2})", txt))
    electric_charges       = _clean_amt(_find(r"(?:Electric|Electricity)\s*Charges\s*[:$]?\s*([\d,]+\.\d{2})", txt))

    invoice_id = _find(r"\bINVOICE-\d{5}-\d{6,}\b", txt) or _find(r"\bInvoice\s*ID[:#]?\s*([A-Z0-9\-]+)", txt)
    issue_id   = _find(r"\bID-\d{8}\b", txt) or _find(r"\bIssue\s*ID[:#]?\s*([A-Z0-9\-]+)", txt)

    meter_rows = _find_all(
        r"(?im)^\s*(?P<meter>[0-9]{5,})[^\n]*?(?:Prev(?:ious)?\s*Read)?[^\n]*?(?P<prev>[0-9,\.]+)?[^\n]*?"
        r"(?:Usage|Units|100\s*GALS)\s*[^\n]*?(?P<usage>[0-9,\.]+)[^\n]*?"
        r"(?:Base\s*Charge)?[^\n]*?(?P<base>\$?[0-9,\.]+)?[^\n]*?"
        r"(?:Usage\s*Charge)?[^\n]*?(?P<usechg>\$?[0-9,\.]+)?[^\n]*?"
        r"(?:Total)\s*[^\n]*?(?P<total>\$?[0-9,\.]+)?[^\n]*?$",
        txt
    )

    meters: List[Dict[str, Any]] = []
    for m in meter_rows:
        meter_number, prev, usage, base, usechg, total = m
        meters.append({
            "meter_number": meter_number or None,
            "previous_read": prev or None,
            "usage": _clean_amt(usage) if usage else None,
            "base_charge": _clean_amt(base) if base else None,
            "usage_charge": _clean_amt(usechg) if usechg else None,
            "total": _clean_amt(total) if total else None,
        })

    rate_plan   = _find(r"(?:Rate\s*Plan|Rate\s*Code)\s*[:#]?\s*([A-Za-z0-9\-]+)", txt)
    days        = _find(r"\bfor\s*(\d+)\s*days\b", txt)
    usage_total = _clean_amt(_find(r"Total\s*Usage\s*[:#]?\s*([\d,\.]+)", txt))

    def _infer_utility_type():
        pn = (provider_name or "").lower()
        if gas_charges:
            return "gas"
        if electric_charges:
            return "electricity"
        if water_charges or sewer_charges or storm_water_charges or "water" in pn or "sewer" in pn:
            return "water"
        if trash_charges:
            return "trash"
        if "reliant" in pn or "txu" in pn or "electric" in pn or "power" in pn:
            return "electricity"
        if "atmos" in pn:
            return "gas"
        return None

    extracted: Dict[str, Any] = {
        "provider_name": provider_name,
        "utility_type": _infer_utility_type(),
        "customer_name": customer_name,
        "account_number": account_number,
        "service_address": service_address,
        "mailing_address": mailing_address,
        "invoice_id": invoice_id,
        "issue_id": issue_id,
        "statement_issued": statement_issued,
        "service_start": service_start,
        "service_end": service_end,
        "amount_due_by": amount_due_by,
        "due_date": due_date_pref,
        "amount_due_after": amount_due_after,
        "previous_balance": previous_balance,
        "payments": payments,
        "balance_forward": balance_forward,
        "past_due_balance": past_due,
        "current_charges": total_current_charges,
        "water_charges": water_charges,
        "sewer_charges": sewer_charges,
        "storm_water_charges": storm_water_charges,
        "environmental_fee": environmental_fee,
        "trash_charges": trash_charges,
        "gas_charges": gas_charges,
        "electric_charges": electric_charges,
        "total_amount_due": total_amount_due,
        "rate_plan": rate_plan,
        "service_days": int(days) if days and str(days).isdigit() else None,
        "total_usage": usage_total,
        "meters": meters if meters else None,
        "confidence": 0.7,
        "raw_text_sample": txt[:2000],
    }

    vendor = None
    if callable(apply_vendor_enhancements):
        try:
            extracted, vendor = apply_vendor_enhancements(extracted, txt)
        except Exception as e:
            logger.warning("Vendor enhancement failed: %s", e)

    if vendor:
        extracted["vendor_name"] = extracted.get("vendor_name") or vendor
        logger.info("Fingerprint matched: %s", vendor)

    return extracted

class PDFcoExtractor:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or PDFCO_API_KEY

    def extract(self, pdf_bytes: bytes) -> Dict[str, Any]:
        text = pdf_to_text(pdf_bytes)
        data = parse_bill_text(text)
        if not any([data.get("total_amount_due"), data.get("account_number"), data.get("provider_name")]):
            raise ValueError("Parsed text but no key fields found")
        return data
