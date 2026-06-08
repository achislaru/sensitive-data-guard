"""Romanian Presidio recognizers.

Presidio does NOT natively detect CNP or Romanian CUI. We add custom
recognizers whose check-digit validation doubles as a false-positive filter.
The generic IBAN recognizer is replaced with a strict RO one (mod-97 validated)
to raise its confidence to 1.0.
"""
import re

from presidio_analyzer import (EntityRecognizer, Pattern, PatternRecognizer,
                               RecognizerResult)

from .validators import cnp_valid, cui_valid, iban_ro_valid


class CnpRecognizer(EntityRecognizer):
    """Romanian CNP — 13 digits with validated control digit."""

    def __init__(self):
        super().__init__(supported_entities=["RO_CNP"], supported_language="ro",
                         name="CnpRecognizer")

    def load(self):
        pass

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for m in re.finditer(r"\b\d{13}\b", text):
            if cnp_valid(m.group(0)):
                out.append(RecognizerResult("RO_CNP", m.start(), m.end(), 1.0))
        return out


class IbanRoRecognizer(EntityRecognizer):
    """Romanian IBAN with mod-97 validation."""

    def __init__(self):
        super().__init__(supported_entities=["RO_IBAN"], supported_language="ro",
                         name="IbanRoRecognizer")

    def load(self):
        pass

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for m in re.finditer(r"\bRO\d{2}[A-Z]{4}[A-Z0-9]{16}\b", text):
            if iban_ro_valid(m.group(0)):
                out.append(RecognizerResult("RO_IBAN", m.start(), m.end(), 1.0))
        return out


class CuiRecognizer(EntityRecognizer):
    """Romanian CUI/CIF with validated control digit.

    Bare 2-10 digits would produce many false positives, so we require either
    the RO prefix or a CUI/CIF keyword nearby.
    """

    def __init__(self):
        super().__init__(supported_entities=["RO_CUI"], supported_language="ro",
                         name="CuiRecognizer")

    def load(self):
        pass

    def analyze(self, text, entities, nlp_artifacts=None):
        out = []
        for m in re.finditer(r"\bRO(\d{2,10})\b", text):
            if cui_valid(m.group(1)):
                out.append(RecognizerResult("RO_CUI", m.start(), m.end(), 0.95))
        for m in re.finditer(r"(?:CUI|CIF)[:\s]+(\d{2,10})\b", text):
            if cui_valid(m.group(1)):
                out.append(RecognizerResult("RO_CUI", m.start(1), m.end(1), 0.95))
        return out


def phone_recognizer() -> PatternRecognizer:
    return PatternRecognizer(
        supported_entity="RO_PHONE", supported_language="ro",
        name="PhoneRoRecognizer",
        patterns=[Pattern("phone_mobile", r"\b(?:\+40|0)7\d{8}\b", 0.7),
                  Pattern("phone_fixed", r"\b(?:\+40|0)[23]\d{8}\b", 0.6)])


def date_recognizer() -> PatternRecognizer:
    return PatternRecognizer(
        supported_entity="RO_DATE", supported_language="ro",
        name="DateRoRecognizer",
        patterns=[Pattern("date_dmy", r"\b\d{2}[./-]\d{2}[./-](?:19|20)\d{2}\b", 0.6),
                  Pattern("date_iso", r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b", 0.6)])
