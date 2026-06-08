# sensitive-data-guard (`sdg`)

A GDPR-compliant sensitive-data workflow guard for AI agents.

`sdg` lets an AI agent work with personal and sensitive data (CVs, payroll,
invoices, national IDs) **without leaking it**. It classifies data, routes it to
the right processing path (local model / cloud-with-pseudonymization /
cloud-direct), pseudonymizes anything that goes to the cloud, and **fails closed**
— if validated PII would reach the cloud, the operation stops.

> **Status:** early development. Phases F0–F1 (packaging + core pipeline + the
> `ro_RO` country pack) are implemented. Certification, the guard/passport, the
> protocol library, the Moldova pack, and the channel pre-gate are on the
> roadmap — see `docs/architecture.md` (to be added).

## How it works (in one picture)

```
input → detect PII → pseudonymize → [cloud AI] → restore → output
                          │
                          └─ re-scan: if validated PII remains → REFUSE (exit ≠ 0)
```

Local-only data (CNP, payroll, CVs) never leaves the machine — it is processed
by a local model (Ollama). Only pseudonymized text is ever sent to a cloud model.

## Core guarantees (validated)

- **100% detection recall** on synthetic fixtures; **100%** for the critical
  identifiers (CNP, IBAN), enforced by check-digit validation.
- **Fail-closed outbound guard**: pseudonymized text is re-scanned; residual
  validated PII raises an error instead of being sent.
- **Types-only audit trail**: the log records PII *types and counts*, never
  values — the log can't become a leak. Retention deletes conversations after
  90 days and anonymizes audit entries after 12 months.
- **Country packs**: PII recognizers, validators and synthetic-data generators
  are pluggable per locale. `ro_RO` (Romania) ships first.

## Install (development)

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m spacy download ro_core_news_lg   # ~600 MB, one-time
```

## Try it

```bash
sdg version
sdg packs                                  # list installed country packs
sdg detect --file some_invoice.txt         # detect PII (unstructured)
sdg detect --file payroll.csv --csv        # tabular: detection by column header
```

## Test

```bash
.venv/bin/pytest            # detection recall, round-trip, fail-closed, audit
```

## Privacy & repo hygiene

This repository contains **zero real PII**. All test data is generated
deterministically with valid-but-fictitious check digits and the
`@exemplu-fictiv.ro` domain. Secrets and machine-local state (vault key,
mapping DB, passport, audit logs, quarantine) are never committed — see
`.gitignore`.

## License

MIT — see `LICENSE`.
