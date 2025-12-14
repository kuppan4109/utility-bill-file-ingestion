from dataclasses import dataclass
from typing import List, Optional

@dataclass(frozen=True)
class VendorFingerprint:
    name: str
    keywords: List[str]
    utility_type_hint: Optional[str] = None
    unit_type_hint: Optional[str] = None
    expects_meters: Optional[bool] = None
    expects_usage: Optional[bool] = None

    def score(self, txt_lower: str) -> int:
        return sum(1 for kw in self.keywords if kw.lower() in txt_lower)

def match_fingerprint(txt: str, fps):
    t = (txt or "").lower()
    best = None
    best_score = 0
    for fp in fps:
        s = fp.score(t)
        if s >= 2 and s > best_score:
            best = fp
            best_score = s
    return best

def fill_if_missing(d: dict, key: str, value):
    if d.get(key) is None and value not in (None, ""):
        d[key] = value

