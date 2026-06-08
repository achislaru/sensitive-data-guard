"""Moldovan national-identifier check-digit validators.

Used as false-positive filters, exactly like the ro_RO ones: a 13-digit string
with a wrong control digit is NOT flagged. The IDNP (natural person) and IDNO
(legal entity) state identification numbers share the same 13-digit format and
the same control algorithm — weights 7,3,1 repeating over the first 12 digits,
sum mod 10. They are told apart by context, not by the checksum.
"""
import re

_WEIGHTS = [7, 3, 1] * 4  # 12 weights


def _idn_control(d12: str) -> str:
    """Control digit for a Moldovan IDNP/IDNO body (first 12 digits)."""
    s = sum(int(a) * w for a, w in zip(d12, _WEIGHTS))
    return str(s % 10)


def idnp_valid(c: str) -> bool:
    """IDNP — 13 digits, control digit via weights 7,3,1 (mod 10)."""
    if not re.fullmatch(r"\d{13}", c):
        return False
    return _idn_control(c[:12]) == c[12]


# IDNO (legal entities) uses the identical format and checksum.
idno_valid = idnp_valid


def iban_md_valid(i: str) -> bool:
    """Moldovan IBAN — MD + 2 check digits + 20 alphanumeric (24 total), mod-97."""
    if not re.fullmatch(r"MD\d{2}[A-Z0-9]{20}", i):
        return False
    num = "".join(str(int(ch, 36)) for ch in i[4:] + i[:4])
    return int(num) % 97 == 1
