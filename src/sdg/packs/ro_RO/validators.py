"""Romanian national-identifier check-digit validators.

These are used as false-positive filters: a 13-digit string with a wrong
control digit is NOT flagged as a CNP. Ported verbatim (behavior-preserving)
from the validated pilot.
"""
import re


def cnp_valid(c: str) -> bool:
    """CNP — 13 digits, weighted control digit (constant 279146358279)."""
    if not re.fullmatch(r"\d{13}", c) or c[0] == "0":
        return False
    s = sum(int(a) * int(b) for a, b in zip(c[:12], "279146358279"))
    k = s % 11
    return str(1 if k == 10 else k) == c[12]


def iban_ro_valid(i: str) -> bool:
    """Romanian IBAN — RO + 2 check digits + 4-letter bank + 16 alnum, mod-97."""
    if not re.fullmatch(r"RO\d{2}[A-Z]{4}[A-Z0-9]{16}", i):
        return False
    num = "".join(str(int(ch, 36)) for ch in i[4:] + i[:4])
    return int(num) % 97 == 1


def cui_valid(c: str) -> bool:
    """CUI/CIF — fiscal code with weighted control digit (key 753217532)."""
    d = c.upper().removeprefix("RO")
    if not re.fullmatch(r"\d{2,10}", d):
        return False
    body, ctrl = d[:-1], d[-1]
    s = sum(int(a) * int(b) for a, b in zip(body.zfill(9), "753217532"))
    k = (s * 10) % 11
    return str(0 if k == 10 else k) == ctrl
