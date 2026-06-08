"""Column-based detection for tabular data (CSV).

NER does not detect names in tabular text (confirmed 3x in the pilot: 0/20 on
CSV). For structured files the column header decides the entity type for the
whole column. This complements — never replaces — the regex/validated
recognizers, which still run on the raw CSV text.
"""
import csv as _csv
import io as _io

from presidio_analyzer import RecognizerResult

# header substring -> entity type
CSV_HEADERS = {
    "nume": "PERSON", "prenume": "PERSON", "angajat": "PERSON", "name": "PERSON",
    "cnp": "RO_CNP", "iban": "RO_IBAN", "cont": "RO_IBAN", "account": "RO_IBAN",
    "email": "EMAIL_ADDRESS", "e-mail": "EMAIL_ADDRESS",
    "telefon": "RO_PHONE", "phone": "RO_PHONE", "adres": "LOCATION", "address": "LOCATION",
    "salariu": "SALARY", "brut": "SALARY", "net": "SALARY", "salary": "SALARY",
    "cui": "RO_CUI", "cif": "RO_CUI",
}

# entity types we never tokenize as PII from a column alone
_NON_PII = {"SALARY"}


def analyze_csv(text: str, headers: dict[str, str] = CSV_HEADERS) -> list:
    """Detect PII by column: the header classifies the whole column.

    Returns RecognizerResult objects with offsets into the raw text,
    compatible with AnalyzerEngine output.
    """
    rows = list(_csv.reader(_io.StringIO(text)))
    if len(rows) < 2:
        return []
    col_type: dict[int, str] = {}
    for i, h in enumerate(rows[0]):
        for key, etype in headers.items():
            if key in h.lower():
                col_type[i] = etype
                break
    out, cursor = [], 0
    for row in rows[1:]:
        for i, cell in enumerate(row):
            etype = col_type.get(i)
            if not etype or etype in _NON_PII or not cell.strip():
                continue
            pos = text.find(cell, cursor)
            if pos != -1:
                out.append(RecognizerResult(etype, pos, pos + len(cell), 0.9))
        # advance the cursor to the next row so we don't re-find earlier values
        if row and row[-1]:
            p = text.find(row[-1], cursor)
            if p != -1:
                cursor = p + len(row[-1])
    return out
