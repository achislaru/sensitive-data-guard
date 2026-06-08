"""sensitive-data-guard — GDPR-compliant sensitive-data workflow guard for AI agents."""

from pathlib import Path

__all__ = ["__version__"]


def _read_version() -> str:
    # VERSION file is the single source of truth; fall back to package metadata.
    here = Path(__file__).resolve()
    for parent in here.parents:
        vf = parent / "VERSION"
        if vf.exists():
            return vf.read_text(encoding="utf-8").strip()
    return "0.0.0"


__version__ = _read_version()
