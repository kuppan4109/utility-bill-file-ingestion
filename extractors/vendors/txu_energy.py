# extractors/vendors/txu_energy.py
import re
from .base import VendorFingerprint

FINGERPRINT = VendorFingerprint(
    name="txu",
    keywords=[
        "txu",
        "txu energy",
        "account summary",
        "kwh",
        "esi id",
    ],
    utility_type_hint="electricity",
    unit_type_hint="kWh",
    expects_meters=True,
    expects_usage=True,
)

def _money(val: str):
    if not val:
        return None
    s = (
        val.replace("$", "")
        .replace("", "")   # TXU private currency glyph
        .replace(",", "")
        .strip()
    )
    try:
        return float(s)
    except Exception:
        return None

def enhance(parsed: dict, txt: str):
    out = dict(parsed or {})

    # --------------------------------------------------
    # Vendor authority
    # --------------------------------------------------
    out["provider_name"] = "TXU Energy"
    out["vendor_name"] = "TXU Energy"
    out["utility_type"] = "electricity"
    out["usage_unit"] = "kWh"

    # --------------------------------------------------
    # Customer / Property name (trim padded junk)
    # --------------------------------------------------
    m = re.search(
        r"Customer\s+Name:\s*([A-Z0-9 ()&.'\-]+?)\s{2,}",
        txt,
    )
    if m:
        out["customer_name"] = m.group(1).strip()

    # --------------------------------------------------
    # Account number (authoritative)
    # --------------------------------------------------
    m = re.search(r"Account\s+Number:\s*(\d{6,})", txt)
    if m:
        out["account_number"] = m.group(1)

    # --------------------------------------------------
    # Billing date
    # --------------------------------------------------
    m = re.search(r"Invoice\s+Date:\s*(\d{2}/\d{2}/\d{4})", txt)
    if m:
        out["statement_issued"] = m.group(1)

    # --------------------------------------------------
    # TXU ACCOUNT SUMMARY ROW (SINGLE SOURCE OF TRUTH)
    # Matches:
    # $2,749.58  $0.00  $2,749.58  $1,038.14  $3,787.72  12/06/2024
    # --------------------------------------------------
    summary_row = re.search(
        r"\$([\d,]+\.\d{2})\s+"
        r"\$([\d,]+\.\d{2})\s+"
        r"\$([\d,]+\.\d{2})\s+"
        r"\$([\d,]+\.\d{2})\s+"
        r"\$([\d,]+\.\d{2})\s+"
        r"(\d{2}/\d{2}/\d{4})",
        txt,
    )

    if summary_row:
        out["previous_balance"] = _money(summary_row.group(1))
        out["payments"] = _money(summary_row.group(2))
        out["balance_forward"] = _money(summary_row.group(3))
        out["current_charges"] = _money(summary_row.group(4))
        out["total_amount_due"] = _money(summary_row.group(5))
        out["due_date"] = summary_row.group(6)

    # --------------------------------------------------
    # TXU does NOT reliably publish service period
    # Never guess → explicitly remove if present
    # --------------------------------------------------
    out.pop("service_start", None)
    out.pop("service_end", None)

    # --------------------------------------------------
    # Optional usage (non-blocking)
    # --------------------------------------------------
    m = re.search(r"Total\s+kWh\s+Usage\s+([\d,]+)", txt, re.I)
    if m:
        try:
            out["total_usage"] = float(m.group(1).replace(",", ""))
        except Exception:
            pass

    # --------------------------------------------------
    # Optional rate plan
    # --------------------------------------------------
    m = re.search(r"Rate\s+Plan:\s*([A-Z0-9 \-]+)", txt)
    if m:
        out["rate_plan"] = m.group(1).strip()

    return out
