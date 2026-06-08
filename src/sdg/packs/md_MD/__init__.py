"""md_MD country pack — Moldova (IDNP, IDNO, IBAN-MD, phone, dates).

Shares the Romanian spaCy model (ro_core_news_lg): Romanian is Moldova's
administrative language, so the NER model is identical — only the national
identifiers and their validators differ. This is the deliberate language-model /
country-validator split in the CountryPack interface.
"""
from pathlib import Path

import yaml

from ..base import CountryPack
from . import recognizers as _rec
from .columns import CSV_HEADERS
from .generator import generate as _generate
from .validators import idnp_valid, idno_valid, iban_md_valid

_THRESHOLDS = Path(__file__).parent / "thresholds.yaml"


class MdMdPack(CountryPack):
    locale = "md_MD"
    entities = ["PERSON", "ORGANIZATION", "EMAIL_ADDRESS", "LOCATION",
                "MD_IDNP", "MD_IDNO", "MD_IBAN", "MD_PHONE", "MD_DATE"]
    label_map = {
        "PERSON": "PERSON", "MD_IDNP": "IDNP", "MD_IDNO": "IDNO",
        "MD_IBAN": "IBAN", "EMAIL_ADDRESS": "EMAIL", "MD_PHONE": "PHONE",
        "LOCATION": "ADDRESS", "ORGANIZATION": "ORG", "MD_DATE": "DATE",
    }

    def recognizers(self):
        return [_rec.IdnpRecognizer(), _rec.IdnoRecognizer(),
                _rec.IbanMdRecognizer(), _rec.phone_recognizer(),
                _rec.date_recognizer()]

    def validators(self):
        return {"MD_IDNP": idnp_valid, "MD_IDNO": idno_valid,
                "MD_IBAN": iban_md_valid}

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
        return {"MD_IDNP", "MD_IDNO", "MD_IBAN", "EMAIL_ADDRESS", "MD_PHONE"}

    def generate_fixtures(self, seed: int, out_dir: Path) -> Path:
        return _generate(seed, out_dir)

    def thresholds(self) -> dict:
        return yaml.safe_load(_THRESHOLDS.read_text(encoding="utf-8"))


PACK = MdMdPack()
