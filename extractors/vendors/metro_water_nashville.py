# extractors/vendors/metro_water_nashville.py
import re
from .base import VendorFingerprint

FINGERPRINT = VendorFingerprint(
    name="metro_water_nashville",
    keywords=[
        "metro water services",
        "mws customer service center",
        "nashville.gov/water",
        "account summary as of",
        "wa water charges",
    ],
    utility_type_hint="water",
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

    # --------------------------------------------------
    # Vendor authority
    # --------------------------------------------------
    out["provider_name"] = "Metro Water Services"
    out["vendor_name"] = "Metro Water Services"
    out["utility_type"] = "water"
    out["usage_unit"] = "CCF"

    # --------------------------------------------------
    # Customer / Property
    # --------------------------------------------------
    m = re.search(
    r"Customer\s+Name:\s*(.*?)\s{2,}(?:www\.|BillingDate:|AccountNumber:)",
    txt,
    re.I,
    )
    if m:
        out["customer_name"] = m.group(1).strip()


    # --------------------------------------------------
    # Account number
    # --------------------------------------------------
    m = re.search(r"Account\s*Number[:\s]*([0-9]{6,})", txt, re.I)
    if m:
        out["account_number"] = m.group(1)

    # --------------------------------------------------
    # Service address
    # --------------------------------------------------
    m = re.search(r"Service\s+Address:\s*(.+)", txt, re.I)
    if m:
        out["service_address"] = m.group(1).strip()

    # --------------------------------------------------
    # Billing & Due dates
    # --------------------------------------------------
    m = re.search(r"BillingDate:\s*(\d{2}/\d{2}/\d{4})", txt)
    if m:
        out["statement_issued"] = m.group(1)

    m = re.search(r"Due\s+Date:\s*(\d{2}/\d{2}/\d{4})", txt)
    if m:
        out["due_date"] = m.group(1)

    # --------------------------------------------------
    # Service period + days
    # Service From 10/16/25 - 11/13/25 (28 Days)
    # --------------------------------------------------
    m = re.search(
        r"Service\s+From\s+(\d{2}/\d{2}/\d{2})\s*-\s*(\d{2}/\d{2}/\d{2}).*?\((\d+)\s+Days\)",
        txt,
        re.I,
    )
    if m:
        out["service_start"] = m.group(1)
        out["service_end"] = m.group(2)
        out["service_days"] = int(m.group(3))

    # --------------------------------------------------
    # Usage (WA Water Usage History)
    # NOV 2025 - 133 CCF
    # --------------------------------------------------
    m = re.search(r"NOV\s+\d{4}\s*-\s*(\d+)\s+CCF", txt)
    if m:
        out["total_usage"] = float(m.group(1))

    # --------------------------------------------------
    # Account summary
    # --------------------------------------------------
    m = re.search(r"Current\s+Charges\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["current_charges"] = _money(m.group(1))

    m = re.search(r"Prior\s+Balance\s+-\s+Past\s+Due\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["previous_balance"] = _money(m.group(1))
        out["past_due_balance"] = _money(m.group(1))

    m = re.search(r"Total\s+Amount\s+Due\s+Upon\s+Receipt\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["total_amount_due"] = _money(m.group(1))

    # --------------------------------------------------
    # Charge breakdown (Account Detail)
    # --------------------------------------------------
    m = re.search(r"WA\s+Water\s+Charges\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["water_charges"] = _money(m.group(1))

    m = re.search(r"SW\s+Sewer\s+Charges\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["sewer_charges"] = _money(m.group(1))

    m = re.search(r"ST\s+Stormwater\s+Charges\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["storm_water_charges"] = _money(m.group(1))

    m = re.search(r"Water\s+Infrastructure\s+Replacement\s+Fee\s*\$([\d,]+\.\d{2})", txt)
    if m:
        out["environmental_fee"] = _money(m.group(1))

    return out
