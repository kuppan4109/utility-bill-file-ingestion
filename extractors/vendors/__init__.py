from .base import VendorFingerprint, match_fingerprint
from . import comcast,txu_energy,summer_energy,atmos_energy,houston_water,cirro_energy

VENDOR_MODULES = [
    comcast,
    txu_energy,
    summer_energy,
    atmos_energy,
    houston_water,
    cirro_energy
                  ]

def apply_vendor_enhancements(parsed: dict, txt: str):
    fps = [m.FINGERPRINT for m in VENDOR_MODULES]
    fp = match_fingerprint(txt, fps)
    if not fp:
        return parsed, None
    for m in VENDOR_MODULES:
        if m.FINGERPRINT.name == fp.name:
            return m.enhance(parsed, txt), fp.name
    return parsed, fp.name

