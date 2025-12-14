# extractors/vendors/txu.py
import re
from .base import VendorFingerprint, fill_if_missing

FINGERPRINT = VendorFingerprint(
    name="txu_energy",
    keywords=[
        "txu",
        "energy",
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
    s = val.replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except Exception:
        return None

def enhance(parsed: dict, txt: str):
    out = dict(parsed or {})

    fill_if_missing(out, "provider_name", "TXU Energy")
    fill_if_missing(out, "utility_type", "electricity")
    fill_if_missing(out, "usage_unit", "kWh")

    # ----------------------------------------------------
    # TXU Account Summary table parsing (CORRECT METHOD)
    # ----------------------------------------------------
    #
    # Header:
    # Previous Balance | Credits | Balance Forward | Current Charges | Amount Due | Due Date
    #
    # Data row:
    # 2749.58 0.00 2749.58 1038.14 3787.72 12/06/2024
    #

    table_match = re.search(
        r"Account Summary.*?\n([^\n]+)\n([^\n]+)",
        txt,
        re.I | re.S,
    )

    if table_match:
        header = table_match.group(1).lower()
        row = table_match.group(2)

        # Ensure this is the correct table
        if "amount due" in header and "current charges" in header:
            nums = re.findall(r"\$?\d{1,3}(?:,\d{3})*\.\d{2}", row)

            # Expected order:
            # [previous_balance, credits, balance_forward, current_charges, amount_due]
            if len(nums) >= 5:
                val = _money(nums[4])
                if val is not None:
                    out["total_amount_due"] = val

    # ----------------------------------------------------
    # Fallback: explicit Amount Due (non-table cases)
    # ----------------------------------------------------
    if out.get("total_amount_due") is None:
        m = re.search(
            r"\bAmount Due\b\s*\$?([\d,]+\.\d{2})",
            txt,
            re.I,
        )
        if m:
            val = _money(m.group(1))
            if val is not None:
                out["total_amount_due"] = val

    out.setdefault("vendor_name", "TXU Energy")
    return out
