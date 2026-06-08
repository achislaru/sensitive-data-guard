"""CountryPack — the interface every locale pack must implement.

A pack bundles everything country-specific about PII handling:
  * recognizers   — Presidio recognizers for national identifiers
  * validators    — check-digit functions (used as false-positive filters)
  * nlp_config    — which spaCy model + NER label mapping to use
  * csv_columns   — header -> entity map for tabular data (NER fails on tables)
  * generator     — deterministic synthetic fixtures + ground truth for self-test
  * thresholds    — recall / benchmark pass bars for certification

The deliberate split: a pack owns *language model* and *country validators*
separately, so locales that share a language (ro_RO and md_MD both Romanian)
can reuse the same spaCy model while shipping different validators.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable


class CountryPack(ABC):
    #: BCP-47-ish locale code, e.g. "ro_RO" / "md_MD"
    locale: str
    #: entity types this pack contributes, e.g. ["RO_CNP", "RO_IBAN", ...]
    entities: list[str]
    #: entity type -> short pseudonym label (RO_CNP -> "CNP")
    label_map: dict[str, str]

    @abstractmethod
    def recognizers(self) -> list:
        """Presidio recognizers (custom national-ID detectors)."""

    @abstractmethod
    def validators(self) -> dict[str, Callable[[str], bool]]:
        """Check-digit validators keyed by entity type."""

    @abstractmethod
    def nlp_config(self) -> dict:
        """NlpEngineProvider configuration (spaCy model + label mapping)."""

    @abstractmethod
    def csv_columns(self) -> dict[str, str]:
        """Column-header substring -> entity type, for tabular detection."""

    @abstractmethod
    def critical_entities(self) -> set[str]:
        """Deterministic, math-validated entities → hard refuse if they leak."""

    @abstractmethod
    def generate_fixtures(self, seed: int, out_dir: Path) -> Path:
        """Write synthetic data + ground-truth lists; return the manifest path."""

    @abstractmethod
    def thresholds(self) -> dict:
        """Pass bars: {'recall_global': 0.95, 'recall_critical': 1.0, ...}."""
