"""Pseudonymization pipeline with the fail-closed outbound guard.

    input -> detect -> pseudonymize -> [cloud AI] -> restore -> output

Central guarantee: text destined for the cloud is re-scanned; if it still
contains critical (math-validated) PII, the pipeline RAISES (the caller must
treat this as a hard stop / non-zero exit).
"""
from __future__ import annotations

from .detect import detect
from .packs.registry import load_pack
from .vault import Vault


class OutboundPiiError(RuntimeError):
    """Raised when pseudonymized text still contains critical PII."""


def pseudonymize(text: str, vault: Vault, locale: str = "ro_RO",
                 is_csv: bool = False) -> str:
    pack = load_pack(locale)
    spans = detect(text, locale=locale, is_csv=is_csv)
    out, cursor = [], 0
    for d in spans:
        out.append(text[cursor:d.start])
        out.append(vault.pseudonym(text[d.start:d.end], d.entity_type))
        cursor = d.end
    out.append(text[cursor:])
    result = "".join(out)

    # GUARANTEE: re-scan before declaring the text cloud-safe.
    critical = pack.critical_entities()
    residual = [r for r in detect(result, locale=locale, is_csv=False)
                if r.entity_type in critical]
    if residual:
        leaked = [(r.entity_type, result[r.start:r.end]) for r in residual]
        raise OutboundPiiError(
            f"refusing cloud send: {len(residual)} critical PII remained "
            f"after pseudonymization: {leaked}")
    return result
