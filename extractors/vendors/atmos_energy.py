# extractors/vendors/atmos_energy.py
import re
from .base import VendorFingerprint

FINGERPRINT = VendorFingerprint(
    name="atmos_energy",
    keywords=[
        "atmos energy",
        "natural gas",
        "gas usage trend",
        "ccf",
        "account summary",
    ],
    utility_type_hint="gas",
    unit_type_hint="CCF",
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

    # -------------------------------
    # Vendor authority
    # -------------------------------
    out["provider_name"] = "Atmos Energy"
    out["vendor_name"] = "Atmos Energy"
    out["utility_type"] = "gas"
    out["usage_unit"] = "CCF"

    # -------------------------------
    # Customer / Property name
    # -------------------------------
    m = re.search(r"Customer\s+Name:\s*(.+)", txt, re.I)
    if m:
        out["customer_name"] = m.group(1).strip()

    # -------------------------------
    # Account number
    # -------------------------------
    m = re.search(r"Account\s+Number[:\s]+(\d{6,})", txt, re.I)
    if not m:
        m = re.search(r"\b(\d{10,})\b", txt)  # barcode/footer fallback

    if m:
        out["account_number"] = m.group(1)

    # -------------------------------
    # Service address
    # -------------------------------
    m = re.search(r"Service\s+Address:\s*(.+)", txt, re.I)
    if m:
        out["service_address"] = m.group(1).strip()

    # -------------------------------
    # Billing & Due dates
    # -------------------------------
    m = re.search(r"Billing\s+Date:\s*(\d{1,2}/\d{1,2}/\d{2,4})", txt)
    if m:
        out["statement_issued"] = m.group(1)

    m = re.search(r"Due\s+Date\s+Total\s+Due\s*\n(\d{2}/\d{2}/\d{2})", txt)
    if m:
        out["due_date"] = m.group(1)

    # -------------------------------
    # Service period
    # -------------------------------
    m = re.search(
        r"Meter\s+Serial\s+#.*?\n\s*\S+\s+(\d{2}/\d{2}/\d{2})\s+(\d{2}/\d{2}/\d{2})",
        txt,
        re.S,
    )
    if m:
        out["service_start"] = m.group(1)
        out["service_end"] = m.group(2)

    # -------------------------------
    # Meter + Usage
    # -------------------------------
    m = re.search(r"Meter\s+Serial\s+#\s*(\S+)", txt)
    if not m:
        m = re.search(r"\n(\d{6,})\s+\d{1,2}/\d{1,2}/\d{2}", txt)

    if m:
        out["meters"] = [{"meter_number": m.group(1)}]

    m = re.search(r"Actual\s+Usage\s+in\s+CCF:\s*([\d.]+)", txt)
    if m:
        out["total_usage"] = float(m.group(1))

    # -------------------------------
    # Account summary values
    # -------------------------------
    m = re.search(r"Previous\s+Balance\s+([\d.]+)", txt)
    if m:
        out["previous_balance"] = _money(m.group(1))

    m = re.search(r"Payment\(s\)\s+(-[\d.]+)", txt)
    if m:
        out["payments"] = _money(m.group(1))

    m = re.search(r"Current\s+Charges\s+([\d.]+)", txt)
    if m:
        out["current_charges"] = _money(m.group(1))

    m = re.search(r"TOTAL\s+AMOUNT\s+DUE\s+\$([\d.]+)", txt, re.I)
    if m:
        out["total_amount_due"] = _money(m.group(1))

    # -------------------------------
    # Gas charges + rate plan
    # -------------------------------
    m = re.search(r"CURRENT\s+GAS\s+CHARGE\s+TOTAL\s+([\d.]+)", txt)
    if m:
        out["gas_charges"] = _money(m.group(1))

    m = re.search(r"(Commercial\s+\w+)", txt)
    if m:
        out["rate_plan"] = m.group(1)

    return out
