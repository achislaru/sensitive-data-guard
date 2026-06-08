# Authoring a country pack

A **country pack** supplies the locale-specific half of detection: the PII
recognizers, their check-digit validators, the synthetic-data generator, tabular
column rules, and detection thresholds. The detection *engine* and the
pseudonymization *pipeline* are locale-agnostic — a pack just plugs into them.

`ro_RO` (Romania) ships first. `md_MD` (Moldova) is the reference second pack and
demonstrates a key separation: **the language model and the country validators
are independent.** Moldova shares the Romanian spaCy NER model
(`ro_core_news_lg`) because Romanian is an official language there, but brings
its own identifiers (IDNP, IDNO, IBAN-MD, +373 phones).

## The interface

A pack subclasses `CountryPack` (`src/sdg/packs/base.py`) and exports a module
singleton `PACK`:

```python
class CountryPack(ABC):
    locale: str               # e.g. "md_MD"
    entities: list[str]       # e.g. ["MD_IDNP", "MD_IDNO", "MD_IBAN", "MD_PHONE"]
    label_map: dict           # entity_type -> pseudonym label, e.g. {"MD_IDNP": "IDNP"}

    def recognizers(self): ...        # Presidio recognizers for this locale
    def validators(self): ...         # {entity_type: callable(str) -> bool}
    def nlp_config(self): ...         # spaCy model + entity label mapping
    def csv_columns(self): ...        # tabular column-header → entity rules
    def critical_entities(self): ...  # entities that must hit 100% recall
    def generate_fixtures(self, seed, out_dir): ...   # deterministic synthetic data
    def thresholds(self): ...         # recall targets + benchmark counts
```

Directory layout (mirror `src/sdg/packs/ro_RO/`):

```
src/sdg/packs/md_MD/
  __init__.py        # defines the MdMdPack and exports PACK
  validators.py      # idnp_valid(), idno_valid(), iban_md_valid()
  recognizers.py     # Presidio PatternRecognizers + custom recognizers
  columns.py         # CSV_HEADERS + analyze_csv() for tabular data
  generator.py       # deterministic synthetic IDNP/IDNO/IBAN/names
  thresholds.yaml    # recall_global, recall_critical, benchmark counts
  fixtures/          # generated synthetic test data (no real PII, ever)
```

## Validators are where correctness lives

A recognizer's regex finds *candidate* spans; a **validator** confirms them via
the official check-digit algorithm, which is what gives the pack its high
precision and lets critical entities reach 100% recall without false positives.
Romanian examples: CNP (13 digits, weighted check digit `279146358279`), IBAN-RO
(mod-97), CUI (key `753217532`). Moldova: IDNP (13-digit personal code), IDNO
(organization code), IBAN-MD (mod-97). Implement and unit-test the check digit
before anything else.

## Register the pack

The registry (`src/sdg/packs/registry.py`) discovers packs by locale. After
adding the package, declare its data files in `pyproject.toml`:

```toml
[tool.setuptools.package-data]
"sdg.packs.md_MD" = ["thresholds.yaml", "fixtures/*"]
```

If the pack reuses an existing spaCy model, map its locale to that model in
`install.sh` (`MODEL_FOR[md_MD]="ro_core_news_lg"`) so the installer doesn't
download a second model.

## Hook special-category entities into classification

National-ID entities must force `special_category`. Add the new identifier to
`_SPECIAL_ENTITIES` in `classify.py`:

```python
_SPECIAL_ENTITIES = {"RO_CNP", "MD_IDNP"}
```

## Prove it

Every pack must ship tests that:

1. Validate check digits on known-good and known-bad fixtures.
2. Hit the pack's declared `recall_global` (e.g. 0.95) and `recall_critical`
   (1.0) on generated fixtures (see `tests/test_detection_recall.py`).
3. Round-trip pseudonymize → restore cleanly.

Run `sdg packs` to confirm the locale is discovered, then
`sdg detect --file <fixture> --locale md_MD` to see it work.

## Privacy rule

Fixtures are generated deterministically with valid-but-fictitious check digits
and a clearly fictional domain. **No pack may contain real personal data.**
