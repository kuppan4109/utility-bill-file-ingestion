# extractors/vendors/piedmont_natural_gas.py
import re
from .base import VendorFingerprint

FINGERPRINT = VendorFingerprint(
    name="piedmont_natural_gas",
    keywords=[
        "piedmont natural gas",
        "your natural gas bill",
        "piedmontng.com",
        "account summary - final bill",
    ],
    utility_type_hint="gas",
    unit_type_hint="CCF",
    expects_meters=False,   # final bill, no meter table
    expects_usage=False,
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
    # Vendor authority (REQUIRED)
    # --------------------------------------------------
    out["provider_name"] = "Piedmont Natural Gas"
    out["vendor_name"] = "Piedmont Natural Gas"
    out["utility_type"] = "gas"
    out["usage_unit"] = "CCF"

    # --------------------------------------------------
    # Property / Customer name
    # --------------------------------------------------
    m = re.search(r"Service\s+address\s+Bill\s+date.*?\n([A-Z0-9 &]+)", txt, re.I)

    if m:
        out["customer_name"] = m.group(1).strip()

    # --------------------------------------------------
    # Service address
    # --------------------------------------------------
    m = re.search(r"\n([0-9]+\s+[A-Z0-9\s]+)\nNASHVILLE", txt, re.I)
    if m:
        out["service_address"] = m.group(1).strip()

    # --------------------------------------------------
    # Account number
    # "6100 1204 9648" → "610012049648"
    # --------------------------------------------------
    m = re.search(r"Account\s+number\s+([0-9\s]{10,})", txt, re.I)
    if m:
        acct = re.sub(r"\D", "", m.group(1))
        if len(acct) >= 6:
            out["account_number"] = acct

    # --------------------------------------------------
    # Billing date
    # --------------------------------------------------
    m = re.search(r"Bill\s+date\s+([A-Za-z]{3}\s+\d{1,2},\s+\d{4})", txt)
    if m:
        out["statement_issued"] = m.group(1)

    # --------------------------------------------------
    # Due date
    # "Total amount due Sep 22"
    # --------------------------------------------------
    m = re.search(r"Total\s+amount\s+due\s+([A-Za-z]{3}\s+\d{1,2})", txt, re.I)
    if m:
        out["due_date"] = m.group(1)

    # --------------------------------------------------
    # Account summary
    # --------------------------------------------------
    m = re.search(r"Previous\s+balance\s+([\d.]+)", txt, re.I)
    if m:
        out["previous_balance"] = _money(m.group(1))
        out["past_due_balance"] = _money(m.group(1))

    m = re.search(
    r"Payment\(s\)\s+received\s+as\s+of\s+[A-Za-z]{3}\s+\d{1,2}\s+([\d]+\.\d{2})",
    txt,
    re.I,
    )
    if m:
        out["payments"] = _money(m.group(1))


    m = re.search(r"Total\s+current\s+charges\s+([\d.]+)", txt, re.I)
    if m:
        out["current_charges"] = _money(m.group(1))

    # --------------------------------------------------
    # TOTAL AMOUNT DUE (CRITICAL & AUTHORITATIVE)
    # Example:
    # "Total amount due Sep 22      $600.51"
    # --------------------------------------------------
    m = re.search(
        r"Total\s+amount\s+due\s+([A-Za-z]{3})\s+(\d{1,2})\s+\$([\d,]+\.\d{2})",
        txt,
        re.I,
    )

    if m:
        # ---- amount (REQUIRED) ----
        val = _money(m.group(3))
        if val is not None and val > 0:
            out["total_amount_due"] = val
            out["amount_due"] = val   # REQUIRED for normalize_fields()

        # ---- due date ----
        if out.get("statement_issued"):
            year = re.search(r"\d{4}", out["statement_issued"])
            if year:
                out["due_date"] = f"{m.group(1)} {m.group(2)}, {year.group(0)}"




    # --------------------------------------------------
    # Final bill → no usage / meter
    # --------------------------------------------------
    out["meters"] = None
    out["total_usage"] = None

    return out
