# extractors/vendors/arlington_utilities.py
import re
from .base import VendorFingerprint

FINGERPRINT = VendorFingerprint(
    name="arlington_utilities",
    keywords=[
        "arlington utilities",
        "combined utility billing",
        "arlingtontx.gov/water",
        "meter information (in 1000 gallons)",
    ],
    utility_type_hint="water",
    unit_type_hint="KGAL",
    expects_meters=True,
    expects_usage=True,
)

def _money(val):
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
    # Vendor authority
    # --------------------------------------------------
    out["provider_name"] = "Arlington Utilities"
    out["vendor_name"] = "Arlington Utilities"
    out["utility_type"] = "water"
    out["usage_unit"] = "KGAL"

    # --------------------------------------------------
    # Property / Customer name (AUTHORITATIVE)
    # Appears under "Name and Service Address"
    # --------------------------------------------------
    m = re.search(r"Name\s+and\s+Service\s+Address.*?\n([^\n]+)", txt, re.I | re.S)
    if m:
        line = m.group(1)

        # Split by large spacing to separate columns
        parts = re.split(r"\s{2,}", line)

        if len(parts) >= 2:
            candidate = parts[-1].strip()

            # Guard against left-column noise
            if not re.search(r"\bemergency\b|\bgarbage\b|\bdrinking\b|817-", candidate, re.I):
                out["customer_name"] = candidate


    # --------------------------------------------------
    # Account number
    # Account Number 36-0209.303
    # --------------------------------------------------
    m = re.search(r"Account\s+Number\s+([\d\-\.]+)", txt)
    if m:
        out["account_number"] = m.group(1)

    # --------------------------------------------------
    # Service address
    # --------------------------------------------------
    m = re.search(r"Name\s+and\s+Service\s+Address\s*\n([^\n]+)", txt)
    if m:
        out["service_address"] = m.group(1).strip()

    # --------------------------------------------------
    # Billing & Due dates
    # --------------------------------------------------
    m = re.search(r"Billing\s+Date\s+(\d{1,2}/\d{1,2}/\d{4})", txt)
    if m:
        out["statement_issued"] = m.group(1)

    m = re.search(r"Due\s+Date\s+(\d{1,2}/\d{1,2}/\d{4})", txt)
    if m:
        out["due_date"] = m.group(1)

    # --------------------------------------------------
    # Meter + service period + usage
    # --------------------------------------------------
    m = re.search(
        r"(M\d+)\s+(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})\s+(\d+)\s+\d+\s+\d+\s+(\d+)",
        txt,
    )
    if m:
        out["meters"] = [{"meter_number": m.group(1)}]
        out["service_start"] = m.group(2)
        out["service_end"] = m.group(3)
        out["service_days"] = int(m.group(4))
        out["total_usage"] = float(m.group(5))

    # --------------------------------------------------
    # Account activity
    # --------------------------------------------------
    m = re.search(r"Previous\s+Balance\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["previous_balance"] = _money(m.group(1))

    m = re.search(r"Payments\s*\$\-([\d,]+\.\d{2})", txt)
    if m:
        out["payments"] = -_money(m.group(1))

    m = re.search(r"Balance\s+Forward\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["balance_forward"] = _money(m.group(1))

    m = re.search(r"Current\s+Charges\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["current_charges"] = _money(m.group(1))

    m = re.search(r"TOTAL\s+AMOUNT\s+DUE\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["total_amount_due"] = _money(m.group(1))

    # --------------------------------------------------
    # Charge breakdown
    # --------------------------------------------------
    m = re.search(r"Total\s+Water\s+Charges\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["water_charges"] = _money(m.group(1))

    m = re.search(r"Total\s+Sewer\s+Charges\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["sewer_charges"] = _money(m.group(1))

    m = re.search(r"Total\s+Drainage\s+Charges\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["storm_water_charges"] = _money(m.group(1))

    return out
