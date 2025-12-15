# extractors/vendors/houston_water.py
import re
from .base import VendorFingerprint

FINGERPRINT = VendorFingerprint(
    name="houston_water",
    keywords=[
        "city of houston",
        "houston water",
        "utility bill",
        "billed usage history",
        "detailed meter usage",
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
    except:
        return None

def enhance(parsed: dict, txt: str):
    out = dict(parsed or {})

    # -----------------------------------
    # Vendor authority
    # -----------------------------------
    out["provider_name"] = "City of Houston"
    out["vendor_name"] = "City of Houston"
    out["utility_type"] = "water"
    out["usage_unit"] = "KGAL"

    # -----------------------------------
    # Customer / Property
    # -----------------------------------
    m = re.search(r"Customer\s+Name:\s*(.+)", txt, re.I)
    if m:
        out["customer_name"] = m.group(1).strip()

    # -----------------------------------
    # Account number
    # -----------------------------------
    m = re.search(r"Account\s+Number:\s*([\d\-]+)", txt, re.I)
    if m:
        out["account_number"] = m.group(1)

    # -----------------------------------
    # Service address
    # -----------------------------------
    m = re.search(r"Service\s+Address:\s*(.+)", txt, re.I)
    if m:
        out["service_address"] = m.group(1).strip()

    # -----------------------------------
    # Billing & Due dates
    # -----------------------------------
    m = re.search(r"Bill\s+Date:\s*(\d{2}/\d{2}/\d{4})", txt)
    if m:
        out["statement_issued"] = m.group(1)

    m = re.search(r"Due\s+Date:\s*(\d{2}/\d{2}/\d{4})", txt)
    if m:
        out["due_date"] = m.group(1)

    # -----------------------------------
    # Billing period (read dates)
    # -----------------------------------
    m = re.search(
        r"Previous\s+Read\s+Date\s+(\d{2}/\d{2}/\d{4}).*?Current\s+Read\s+Date\s+(\d{2}/\d{2}/\d{4})",
        txt,
        re.S,
    )
    if m:
        out["service_start"] = m.group(1)
        out["service_end"] = m.group(2)

    # -----------------------------------
    # Meter + usage
    # -----------------------------------
    m = re.search(r"WATER\s+MULTIF\s+([A-Z0-9\-\.]+)", txt)
    if m:
        out["meters"] = [{"meter_number": m.group(1)}]

    m = re.search(r"Gallons\s+in\s+Thousands\s+(\d+)", txt)
    if m:
        out["total_usage"] = float(m.group(1))

    # -----------------------------------
    # Account summary
    # -----------------------------------
    m = re.search(r"Previous\s+Balance\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["previous_balance"] = _money(m.group(1))

    m = re.search(r"Payment\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["payments"] = _money(m.group(1))

    m = re.search(r"Past\s+Due\s+Amount.*?\$([\d,]+\.\d{2})", txt)
    if m:
        out["past_due_balance"] = _money(m.group(1))

    m = re.search(r"Current\s+Charges\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["current_charges"] = _money(m.group(1))

    m = re.search(r"Total\s+Amount\s+Due\s*\$([\d,]+\.\d{2})", txt, re.I)
    if m:
        out["total_amount_due"] = _money(m.group(1))

    # -----------------------------------
    # Charge breakdown (page 2 table)
    # -----------------------------------
    m = re.search(r"Multifamily\s+Base\s+Water\s+Charge\s*\$([\d,]+\.\d{2})", txt)
    base_water = _money(m.group(1)) if m else 0.0

    m = re.search(r"Multifamily\s+Consumption\s+Water\s+Charge\s*\$([\d,]+\.\d{2})", txt)
    cons_water = _money(m.group(1)) if m else 0.0

    if base_water or cons_water:
        out["water_charges"] = base_water + cons_water

    m = re.search(r"Multifamily\s+Base\s+Sewer\s+Charge\s*\$([\d,]+\.\d{2})", txt)
    base_sewer = _money(m.group(1)) if m else 0.0

    m = re.search(r"Multifamily\s+Consumption\s+Sewer\s+Charge\s*\$([\d,]+\.\d{2})", txt)
    cons_sewer = _money(m.group(1)) if m else 0.0

    if base_sewer or cons_sewer:
        out["sewer_charges"] = base_sewer + cons_sewer

    m = re.search(r"Drainage\s+Charge\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["storm_water_charges"] = _money(m.group(1))

    m = re.search(r"TCEQ\s+Fee\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["environmental_fee"] = _money(m.group(1))

    return out
