"""Romanian column-header → entity map for tabular (CSV) detection.

The scanning logic is shared (`sdg.packs.tabular.analyze_csv`); this module only
supplies the Romanian header vocabulary.
"""
from ..tabular import analyze_csv  # re-exported for backwards compatibility

__all__ = ["CSV_HEADERS", "analyze_csv"]

# header substring -> entity type
CSV_HEADERS = {
    "nume": "PERSON", "prenume": "PERSON", "angajat": "PERSON", "name": "PERSON",
    "cnp": "RO_CNP", "iban": "RO_IBAN", "cont": "RO_IBAN", "account": "RO_IBAN",
    "email": "EMAIL_ADDRESS", "e-mail": "EMAIL_ADDRESS",
    "telefon": "RO_PHONE", "phone": "RO_PHONE", "adres": "LOCATION", "address": "LOCATION",
    "salariu": "SALARY", "brut": "SALARY", "net": "SALARY", "salary": "SALARY",
    "cui": "RO_CUI", "cif": "RO_CUI",
}
