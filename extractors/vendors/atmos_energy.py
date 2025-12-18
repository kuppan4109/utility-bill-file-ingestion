# extractors/vendors/atmos_energy.py
import re
from .base import VendorFingerprint

FINGERPRINT = VendorFingerprint(
    name="atmos",
    keywords=[
        "atmos energy",
        "natural gas",
        "ccf",
        "gas usage",
        "total amount due",
    ],
    utility_type_hint="gas",
    unit_type_hint="CCF",
    expects_meters=True,
    expects_usage=True,
)

def _money(val: str):
    if not val:
        return None
    s = (
        val.replace("$", "")
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
    out["provider_name"] = "Atmos Energy"
    out["vendor_name"] = "Atmos Energy"
    out["utility_type"] = "gas"
    out["usage_unit"] = "CCF"

    # --------------------------------------------------
    # Customer / Property Name
    # Example:
    # Customer Name: 6520 RED SIERRA LLC
    # --------------------------------------------------
    m = re.search(
    r"Customer\s+Name:\s*([A-Z0-9 &()]+?)\s{2,}",
    txt,
    )
    if m:
        out["customer_name"] = m.group(1).strip()


    # --------------------------------------------------
    # Account Number
    # --------------------------------------------------
    m = re.search(
        r"Account\s+Number:\s*(\d{6,})",
        txt,
    )
    if m:
        out["account_number"] = m.group(1)

    # --------------------------------------------------
    # Billing Date
    # --------------------------------------------------
    m = re.search(
        r"Billing\s+Date:\s*(\d{2}/\d{2}/\d{2,4})",
        txt,
    )
    if m:
        out["statement_issued"] = m.group(1)

    # --------------------------------------------------
    # Service Period
    # Example:
    # From 10/24/25 To 11/21/25
    # --------------------------------------------------
    m = re.search(
        r"From\s+(\d{2}/\d{2}/\d{2,4})\s+To\s+(\d{2}/\d{2}/\d{2,4})",
        txt,
    )
    if m:
        out["service_start"] = m.group(1)
        out["service_end"] = m.group(2)

    # --------------------------------------------------
    # Meter Serial Number (table row, NOT header)
    # Example:
    # Meter Serial #
    # 12R100223
    # --------------------------------------------------
    m = re.search(
    r"Meter\s+Serial\s+#.*?\n.*?\n\s*([A-Z0-9]{6,})\s+\d{2}/\d{2}/\d{2,4}\s+\d{2}/\d{2}/\d{2,4}",
    txt,
    re.I | re.S,
    )
    if m:
        out["meters"] = [{"meter_number": m.group(1)}]


    # --------------------------------------------------
    # Usage (CCF)
    # --------------------------------------------------
    m = re.search(
        r"Consumption\s+\(CCF\).*?\n\s*(\d+)",
        txt,
        re.I | re.S,
    )
    if m:
        try:
            out["total_usage"] = float(m.group(1))
        except Exception:
            pass

    # --------------------------------------------------
    # Rate Plan
    # --------------------------------------------------
    m = re.search(
        r"Rate\s+Plan:\s*([A-Z0-9 ]+)",
        txt,
    )
    if m:
        out["rate_plan"] = m.group(1).strip()

    # --------------------------------------------------
    # Account Summary (AUTHORITATIVE)
    # --------------------------------------------------
    # Previous Balance
    m = re.search(
        r"Previous\s+Balance\s+([\d,]+\.\d{2})",
        txt,
    )
    if m:
        out["previous_balance"] = _money(m.group(1))

    # Payments (shown as negative in bill → store positive)
    m = re.search(
        r"Payment\(s\)\s+(-[\d,]+\.\d{2})",
        txt,
    )
    if m:
        out["payments"] = abs(_money(m.group(1)))

    # Current Charges
    m = re.search(
        r"Current\s+Charges\s+([\d,]+\.\d{2})",
        txt,
    )
    if m:
        out["current_charges"] = _money(m.group(1))

    # Gas Charges (subset of current charges)
    m = re.search(
        r"Gas\s+Charges\s+([\d,]+\.\d{2})",
        txt,
    )
    if m:
        out["gas_charges"] = _money(m.group(1))

    # --------------------------------------------------
    # Total Amount Due (LOCKED)
    # --------------------------------------------------
    m = re.search(
        r"TOTAL\s+AMOUNT\s+DUE\s+\$([\d,]+\.\d{2})",
        txt,
        re.I,
    )
    if m:
        out["total_amount_due"] = _money(m.group(1))

    # --------------------------------------------------
    # Due Date (page-1 summary table)
    # Example:
    # Account Number Due Date Total Amount Due
    # 4045700489 12/08/2025 $121.67
    # --------------------------------------------------
    m = re.search(
        r"\d{6,}\s+(\d{2}/\d{2}/\d{2,4})\s+\$[\d,]+\.\d{2}",
        txt,
    )
    if m:
        out["due_date"] = m.group(1)
    
    if out.get("current_charges") and not out.get("gas_charges"):
        out["gas_charges"] = out["current_charges"]


    return out
