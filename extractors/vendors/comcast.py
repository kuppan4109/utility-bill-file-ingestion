import re
from .base import VendorFingerprint

FINGERPRINT = VendorFingerprint(
    name="comcast",
    keywords=[
        "comcast",
        "comcast business",
        "final bill for service",
        "voice network investment",
        "equipment fee",
    ],
    utility_type_hint="other",
    expects_meters=False,
    expects_usage=False,
)

MONTH_DATE = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}"

def _money(val):
    if not val:
        return None
    s = val.replace("$", "").replace("", "").replace(",", "").strip()
    credit = bool(re.search(r"\bcr\b", s, re.I))
    s = re.sub(r"\bcr\b", "", s, flags=re.I)
    try:
        n = float(s)
        return -n if credit else n
    except:
        return None

def enhance(parsed: dict, txt: str):
    out = dict(parsed or {})

    # --------------------------------------------------
    # HARD vendor authority (required)
    # --------------------------------------------------
    out["provider_name"] = "Comcast"
    out["vendor_name"] = "Comcast"
    out["utility_type"] = "other"

    # --------------------------------------------------
    # Property / Customer name (Bay Oaks Apts)
    # Appears before the address and before the symbol 
    # --------------------------------------------------
    m = re.search(r"\n\s*([A-Z][A-Za-z0-9 &.'\-]+)\s*", txt)
    if m:
        out["customer_name"] = m.group(1).strip()

    # --------------------------------------------------
    # Account number
    # --------------------------------------------------
    m = re.search(
        r"Account\s*number\s*[\r\n]+([0-9][0-9\s]{10,})",
        txt,re.I,)
    if m:
        acct = re.sub(r"\D", "", m.group(1))
        if len(acct) >= 6:
            out["account_number"] = acct

    # --------------------------------------------------
    # Bill date
    # --------------------------------------------------
    m = re.search(rf"Bill\s*date\s*({MONTH_DATE})", txt, re.I)
    if m:
        out["statement_issued"] = m.group(1)

    # --------------------------------------------------
    # Service period
    # --------------------------------------------------
    m = re.search(
        rf"Services\s+from\s+({MONTH_DATE})\s+to\s+({MONTH_DATE})",
        txt,
        re.I,
    )
    if m:
        out["service_start"] = m.group(1)
        out["service_end"] = m.group(2)

    # --------------------------------------------------
    # Previous balance / Balance forward
    # --------------------------------------------------
    m = re.search(r"Previous\s+balance\s+([\d,]+\.\d{2})", txt, re.I)
    if m:
        out["previous_balance"] = _money(m.group(1))
        out["balance_forward"] = _money(m.group(1))

    # --------------------------------------------------
    # Payments (explicit Comcast phrase)
    # --------------------------------------------------
    m = re.search(r"No\s+payment\s+received\s+([\d,]+\.\d{2})", txt, re.I)
    if m:
        out["payments"] = _money(m.group(1))

    # --------------------------------------------------
    # Current charges = "New charges"
    # Handles -115.60 cr
    # --------------------------------------------------
    m = re.search(r"New\s+charges\s+([\-$\d,\.]+\s*cr)?", txt, re.I)
    if m:
        out["current_charges"] = _money(m.group(1))

    # --------------------------------------------------
    # TOTAL AMOUNT DUE (FIXED — glyph + spacing safe)
    # --------------------------------------------------
    m = re.search(
        r"Total\s+amount\s+due\s+.*?[$]\s*([\d,]+\.\d{2})",
        txt,
        re.I,
    )
    if not m:
        m = re.search(
            r"Please\s+pay\s+.*?[$]\s*([\d,]+\.\d{2})",
            txt,
            re.I,
        )

    if m:
        out["total_amount_due"] = _money(m.group(1))

    # Comcast never has meters or usage
    out["meters"] = None
    out["total_usage"] = None

    return out
