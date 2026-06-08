"""Moldovan column-header → entity map for tabular (CSV) detection.

Moldova's administrative language is Romanian, so the header vocabulary largely
overlaps with ro_RO; the identifiers differ (IDNP/IDNO/IBAN-MD). The scanning
logic is shared (`sdg.packs.tabular.analyze_csv`).
"""
from ..tabular import analyze_csv  # re-exported for parity with ro_RO

__all__ = ["CSV_HEADERS", "analyze_csv"]

# header substring -> entity type
CSV_HEADERS = {
    "nume": "PERSON", "prenume": "PERSON", "angajat": "PERSON", "name": "PERSON",
    "idnp": "MD_IDNP", "cod personal": "MD_IDNP",
    "idno": "MD_IDNO",
    "iban": "MD_IBAN", "cont": "MD_IBAN", "account": "MD_IBAN",
    "email": "EMAIL_ADDRESS", "e-mail": "EMAIL_ADDRESS",
    "telefon": "MD_PHONE", "phone": "MD_PHONE",
    "adres": "LOCATION", "address": "LOCATION",
    "salariu": "SALARY", "brut": "SALARY", "net": "SALARY", "salary": "SALARY",
}
