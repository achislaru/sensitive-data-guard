"""Moldovan Presidio recognizers.

Presidio does not natively detect IDNP/IDNO or Moldovan IBANs. We add custom
recognizers whose check-digit validation doubles as a false-positive filter.

IDNP (natural person) and IDNO (legal entity) share format and checksum, so they
are disambiguated by context: a valid 13-digit number qualified by an "IDNO"
keyword is an organization code (MD_IDNO); otherwise a valid 13-digit number is
treated as a person code (MD_IDNP). Defaulting bare numbers to IDNP is the safe
direction — IDNP forces the special-category path.
"""
import re

from presidio_analyzer import (EntityRecognizer, Pattern, PatternRecognizer,
                               RecognizerResult)

from .validators import idnp_valid, iban_md_valid

# "IDNO" appearing just before the number marks it as an organization code
_IDNO_CTX = re.compile(r"IDNO[:\s]+(\d{13})\b")
# does an IDNO keyword sit within ~8 chars before this position?
_IDNO_BEFORE = re.compile(r"IDNO[:\s]+$")


class IdnpRecognizer(EntityRecognizer):
    """Moldovan IDNP — 13 digits, validated control digit, person default."""

    def __init__(self):
        super().__init__(supported_entities=["MD_IDNP"], supported_language="ro",
                         name="IdnpRecognizer")

    def load(self):
        pass

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for m in re.finditer(r"\b\d{13}\b", text):
            if not idnp_valid(m.group(0)):
                continue
            # skip if this number is explicitly an IDNO (organization)
            if _IDNO_BEFORE.search(text[:m.start()]):
                continue
            out.append(RecognizerResult("MD_IDNP", m.start(), m.end(), 1.0))
        return out


class IdnoRecognizer(EntityRecognizer):
    """Moldovan IDNO — legal-entity state ID; requires an IDNO keyword."""

    def __init__(self):
        super().__init__(supported_entities=["MD_IDNO"], supported_language="ro",
                         name="IdnoRecognizer")

    def load(self):
        pass

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for m in _IDNO_CTX.finditer(text):
            if idnp_valid(m.group(1)):  # IDNO shares the IDNP checksum
                out.append(RecognizerResult("MD_IDNO", m.start(1), m.end(1), 1.0))
        return out


class IbanMdRecognizer(EntityRecognizer):
    """Moldovan IBAN with mod-97 validation."""

    def __init__(self):
        super().__init__(supported_entities=["MD_IBAN"], supported_language="ro",
                         name="IbanMdRecognizer")

    def load(self):
        pass

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for m in re.finditer(r"\bMD\d{2}[A-Z0-9]{20}\b", text):
            if iban_md_valid(m.group(0)):
                out.append(RecognizerResult("MD_IBAN", m.start(), m.end(), 1.0))
        return out


def phone_recognizer() -> PatternRecognizer:
    return PatternRecognizer(
        supported_entity="MD_PHONE", supported_language="ro",
        name="PhoneMdRecognizer",
        patterns=[Pattern("phone_mobile", r"\b(?:\+373|0)[67]\d{7}\b", 0.7),
                  Pattern("phone_fixed", r"\b(?:\+373|0)22\d{6}\b", 0.6)])


def date_recognizer() -> PatternRecognizer:
    return PatternRecognizer(
        supported_entity="MD_DATE", supported_language="ro",
        name="DateMdRecognizer",
        patterns=[Pattern("date_dmy", r"\b\d{2}[./-]\d{2}[./-](?:19|20)\d{2}\b", 0.6),
                  Pattern("date_iso", r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b", 0.6)])
