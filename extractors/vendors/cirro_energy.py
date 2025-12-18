# extractors/vendors/cirro_energy.py
import re
from .base import VendorFingerprint

FINGERPRINT = VendorFingerprint(
    name="cirro_energy",
    keywords=[
        "cirro energy",
        "us retailers, llc dba cirro energy",
        "account summary",
        "electric usage detail",
        "kwh usage",
    ],
    utility_type_hint="electricity",
    unit_type_hint="kWh",
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

    # --------------------------------------------------
    # Vendor authority
    # --------------------------------------------------
    out["provider_name"] = "Cirro Energy"
    out["vendor_name"] = "Cirro Energy"
    out["utility_type"] = "electricity"
    out["usage_unit"] = "kWh"

    # --------------------------------------------------
    # Property / Customer name
    # --------------------------------------------------
    m = re.search(
    r"Customer\s+Name:\s*(.*?)\s{2,}Bill\s+Date",
    txt,
    re.I,
    )
    if m:
        out["customer_name"] = m.group(1).strip()

    # --------------------------------------------------
    # Account number (strip spaces/dashes)
    # Account #: 19 495 161 - 2
    # --------------------------------------------------
    m = re.search(r"Account\s+#:\s*([0-9\s\-]+)", txt, re.I)
    if m:
        acct = re.sub(r"\D", "", m.group(1))
        if len(acct) >= 6:
            out["account_number"] = acct

    # --------------------------------------------------
    # Billing & Due dates
    # --------------------------------------------------
    m = re.search(r"Bill\s+Date:\s*(\d{2}/\d{2}/\d{4})", txt)
    if m:
        out["statement_issued"] = m.group(1)

    m = re.search(r"Due\s+Date\s*(\d{2}/\d{2}/\d{4})", txt)
    if m:
        out["due_date"] = m.group(1)

    # --------------------------------------------------
    # Service period
    # From 05/22/2025 To 06/23/2025
    # --------------------------------------------------
    m = re.search(
        r"From\s+(\d{2}/\d{2}/\d{4})\s+To\s+(\d{2}/\d{2}/\d{4})",
        txt,
    )
    if m:
        out["service_start"] = m.group(1)
        out["service_end"] = m.group(2)

    # --------------------------------------------------
    # Meter + usage
    # --------------------------------------------------
    m = re.search(r"Meter\s+Number:\s*(\S+)", txt)
    if m:
        out["meters"] = [{"meter_number": m.group(1)}]

    m = re.search(r"kWh\s+Usage\s+(\d+)", txt, re.I)
    if m:
        out["total_usage"] = float(m.group(1))

    # --------------------------------------------------
    # Account summary
    # --------------------------------------------------
    m = re.search(r"Previous\s+Amount\s+Due\s*\$([\d.]+)", txt)
    if m:
        out["previous_balance"] = _money(m.group(1))

    m = re.search(r"Payment\s+([\d.]+)", txt)
    if m:
        out["payments"] = _money(m.group(1))

    m = re.search(r"Balance\s+Forward\s+([\d.]+)", txt)
    if m:
        out["balance_forward"] = _money(m.group(1))

    m = re.search(r"Current\s+Charges\s+([\d.]+)", txt)
    if m:
        out["current_charges"] = _money(m.group(1))
        out["electric_charges"] = _money(m.group(1))

    # --------------------------------------------------
    # Total amount due
    # --------------------------------------------------
    m = re.search(
        r"Total\s+Amount\s+Due\s+by\s+\d{2}/\d{2}/\d{4}\s*\$([\d.]+)",
        txt,
        re.I,
    )
    if m:
        out["total_amount_due"] = _money(m.group(1))

    # --------------------------------------------------
    # Rate plan + service days
    # --------------------------------------------------
    m = re.search(r"(Smart\s+Lock\s+Business)", txt)
    if m:
        out["rate_plan"] = m.group(1)

    m = re.search(r"(\d+)\s+Day\s+Billing\s+Period", txt)
    if m:
        out["service_days"] = int(m.group(1))

    return out
