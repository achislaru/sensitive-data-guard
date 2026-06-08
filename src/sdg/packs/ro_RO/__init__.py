"""ro_RO country pack — Romania (CNP, CUI, IBAN-RO, phone, dates)."""
from pathlib import Path

import yaml

from ..base import CountryPack
from . import recognizers as _rec
from .columns import CSV_HEADERS
from .generator import generate as _generate
from .validators import cnp_valid, cui_valid, iban_ro_valid

_THRESHOLDS = Path(__file__).parent / "thresholds.yaml"


class RoRoPack(CountryPack):
    locale = "ro_RO"
    entities = ["PERSON", "ORGANIZATION", "EMAIL_ADDRESS", "LOCATION",
                "RO_CNP", "RO_IBAN", "RO_CUI", "RO_PHONE", "RO_DATE"]
    label_map = {
        "PERSON": "PERSON", "RO_CNP": "CNP", "RO_IBAN": "IBAN",
        "RO_CUI": "CUI", "EMAIL_ADDRESS": "EMAIL", "RO_PHONE": "PHONE",
        "LOCATION": "ADDRESS", "ORGANIZATION": "ORG", "RO_DATE": "DATE",
    }

    def recognizers(self):
        return [_rec.CnpRecognizer(), _rec.IbanRoRecognizer(), _rec.CuiRecognizer(),
                _rec.phone_recognizer(), _rec.date_recognizer()]

    def validators(self):
        return {"RO_CNP": cnp_valid, "RO_IBAN": iban_ro_valid, "RO_CUI": cui_valid}

    def nlp_config(self) -> dict:
        return {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "ro", "model_name": "ro_core_news_lg"}],
            "ner_model_configuration": {
                "model_to_presidio_entity_mapping": {
                    "PERSON": "PERSON", "ORGANIZATION": "ORGANIZATION",
                    "GPE": "LOCATION", "LOC": "LOCATION",
                },
                "labels_to_ignore": ["DATETIME", "NUMERIC_VALUE", "ORDINAL",
                                     "MONEY", "QUANTITY", "PERIOD", "FACILITY",
                                     "WORK_OF_ART", "EVENT", "NAT_REL_POL",
                                     "LANGUAGE", "PRODUCT"],
            },
        }

    def csv_columns(self) -> dict:
        return CSV_HEADERS

    def critical_entities(self) -> set:
        return {"RO_CNP", "RO_IBAN", "RO_CUI", "EMAIL_ADDRESS", "RO_PHONE"}

    def generate_fixtures(self, seed: int, out_dir: Path) -> Path:
        return _generate(seed, out_dir)

    def thresholds(self) -> dict:
        return yaml.safe_load(_THRESHOLDS.read_text(encoding="utf-8"))


PACK = RoRoPack()
