"""Compare big-O complexity strings tolerantly.

Tolerates whitespace, case, '*' vs juxtaposition for products. Doesn't try to
reduce expressions algebraically - if the seed says O(n) and Opus said
O(n+1), they're not equal here. Be deliberate in the seed CSV."""
from __future__ import annotations


def normalize(s: str) -> str:
    s = s.lower().replace(" ", "").replace("\t", "")
    # treat 'n*m' and 'nm' as identical for two-input forms
    s = s.replace("*", "")
    return s


def equal(a: str, b: str) -> bool:
    return normalize(a) == normalize(b)
