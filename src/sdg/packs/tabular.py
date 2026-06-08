"""Locale-agnostic column-based detection for tabular data (CSV).

NER does not detect names in tabular text (confirmed in the pilot: 0/20 on CSV).
For structured files the column header decides the entity type for the whole
column. This complements — never replaces — the validated recognizers, which
still run on the raw CSV text. The header→entity map is supplied by each country
pack (`pack.csv_columns()`); the scanning logic here is shared.
"""
import csv as _csv
import io as _io

from presidio_analyzer import RecognizerResult

# entity types we never tokenize as PII from a column alone (not identifiers)
NON_PII = {"SALARY"}


def analyze_csv(text: str, headers: dict[str, str], non_pii: set[str] = NON_PII) -> list:
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
            if not etype or etype in non_pii or not cell.strip():
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
