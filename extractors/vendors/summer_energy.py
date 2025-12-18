# extractors/vendors/summer_energy.py
import re
from .base import VendorFingerprint

FINGERPRINT = VendorFingerprint(
    name="summer_energy",
    keywords=[
        "summer energy",
        "summerenergy.com",
        "billing account number",
        "invoice date",
        "amount due",
    ],
    utility_type_hint="electricity",
    unit_type_hint="kWh",
    expects_meters=True,
    expects_usage=True,
)

def _money(val: str):
    if not val:
        return None
    s = val.replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except Exception:
        return None

def enhance(parsed: dict, txt: str):
    out = dict(parsed or {})

    # --------------------------------------------------
    # HARD OVERRIDES (vendor-authoritative)
    # --------------------------------------------------
    out["provider_name"] = "Summer Energy"
    out["vendor_name"] = "Summer Energy"
    out["utility_type"] = "electricity"
    out["usage_unit"] = "kWh"

    # --------------------------------------------------
    # Customer / Property Name
    # --------------------------------------------------
    m = re.search(
        r"Customer:\s*(.+)",
        txt,
        re.I,
    )
    if m:
        out["customer_name"] = m.group(1).strip()

    # --------------------------------------------------
    # Invoice Date (Month-name format)
    # Invoice Date: Aug 16, 2024
    # --------------------------------------------------
    m = re.search(
        r"Invoice\s+Date:\s*([A-Za-z]{3}\s+\d{1,2},\s+\d{4})",
        txt,
        re.I,
    )
    if m:
        out["statement_issued"] = m.group(1)

    # --------------------------------------------------
    # Previous Balance / Balance Forward
    # --------------------------------------------------
    m = re.search(
        r"Previous\s+Statement\s+Amount\s*\$([\d,]+\.\d{2})",
        txt,
        re.I,
    )
    if m:
        out["previous_balance"] = _money(m.group(1))
        out["balance_forward"] = _money(m.group(1))

    # --------------------------------------------------
    # Current Charges
    # --------------------------------------------------
    m = re.search(
        r"Current\s+Charges\s*\$([\d,]+\.\d{2})",
        txt,
        re.I,
    )
    if m:
        out["current_charges"] = _money(m.group(1))
    
    if out.get("current_charges") and not out.get("electric_charges"):
        out["electric_charges"] = out["current_charges"]


    # --------------------------------------------------
    # Total Amount Due (authoritative)
    # Amount Due Sep 05, 2024: $12202.63
    # --------------------------------------------------
    # Amount Due Sep 05, 2024
    m = re.search(
    r"Amount\s+Due\s+([A-Za-z]{3}\s+\d{1,2},\s+\d{4})\s*:\s*\$([\d,]+\.\d{2})",
    txt,
    re.I,
    )
    if m:
        out["due_date"] = m.group(1)
        out["total_amount_due"] = _money(m.group(2))
    
    # Fallback: Current Balance == Total Amount Due (Summer Energy)
    if not out.get("total_amount_due"):
        m = re.search(
            r"Current\s+Balance\s*\$([\d,]+\.\d{2})",
            txt,
            re.I,
        )
        if m:
            out["total_amount_due"] = _money(m.group(1))



    # --------------------------------------------------
    # Cleanup bad generic extractions
    # --------------------------------------------------
    if out.get("service_address") in ("Read    Read", "Read Read"):
        out["service_address"] = None

    # These bills do NOT show service period clearly
    out["service_start"] = None
    out["service_end"] = None

    return out
