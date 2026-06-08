"""Data classification table + a detection-based heuristic classifier.

The classification table is the single source of truth for which processing
paths a data class is allowed to use. Protocols (later) may only NARROW this,
never widen it; the guard intersects it with the machine passport.
"""
from __future__ import annotations

# data class -> allowed processing paths (baseline; ordered most→least private)
DATA_CLASS_PATHS = {
    "special_category": ["local"],
    "personal_pseudonymizable": ["local", "cloud_pseudonymized"],
    "non_personal": ["local", "cloud_pseudonymized", "cloud_direct"],
}

# entity types that, if present, force special_category (national IDs)
_SPECIAL_ENTITIES = {"RO_CNP", "MD_IDNP"}


def allowed_paths(data_class: str) -> list[str]:
    if data_class not in DATA_CLASS_PATHS:
        raise ValueError(f"unknown data class: {data_class}")
    return list(DATA_CLASS_PATHS[data_class])


def classify_text(text: str, locale: str = "ro_RO", is_csv: bool = False) -> dict:
    """Heuristic: national ID present -> special_category; other PII ->
    personal_pseudonymizable; none -> non_personal. Returns class + evidence."""
    from .detect import detect

    spans = detect(text, locale=locale, is_csv=is_csv)
    types = {}
    for d in spans:
        types[d.entity_type] = types.get(d.entity_type, 0) + 1
    if any(t in _SPECIAL_ENTITIES for t in types):
        data_class = "special_category"
    elif types:
        data_class = "personal_pseudonymizable"
    else:
        data_class = "non_personal"
    return {
        "data_class": data_class,
        "allowed_paths": allowed_paths(data_class),
        "pii_types": types,
    }
