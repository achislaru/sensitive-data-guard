# sensitive-data-guard (`sdg`)

A GDPR-compliant sensitive-data workflow guard for AI agents.

`sdg` lets an AI agent work with personal and sensitive data (CVs, payroll,
invoices, national IDs) **without leaking it**. It classifies data, routes it to
the right processing path (local model / cloud-with-pseudonymization /
cloud-direct), pseudonymizes anything that goes to the cloud, and **fails closed**
— if validated PII would reach the cloud, the operation stops.

> **Status:** active development. Implemented: core pipeline + `ro_RO` country
> pack, machine certification + signed passport + tiered fail-closed guard, the
> work-protocol library (meta-skill) with 6 built-ins, the channel pre-gate for
> Telegram/Slack, and country packs for Romania (`ro_RO`) and Moldova (`md_MD`).
> On the roadmap: CI. See [`docs/architecture.md`](docs/architecture.md).

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
  are pluggable per locale. `ro_RO` (Romania) and `md_MD` (Moldova) ship today;
  Moldova reuses the Romanian language model but ships its own identifiers.

## Install

One command (creates `.venv`, installs `sdg`, pulls the spaCy model, certifies
the machine):

```bash
./install.sh
```

Or manually for development:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m spacy download ro_core_news_lg   # ~600 MB, one-time
```

## Try it

```bash
sdg certify                                # audit machine + write passport (once/30d)
sdg preflight                              # which processing paths are enabled
sdg packs                                  # list installed country packs
sdg classify --file some_file.txt          # data class + allowed paths
sdg detect --file some_invoice.txt         # detect PII (unstructured)
sdg detect --file payroll.csv --csv        # tabular: detection by column header
sdg protocol list                          # vetted, GDPR-compliant work recipes
sdg ingest-scan --file f --channel telegram  # channel pre-gate for remote files
```

## For agents

Point the skill loader at [`SKILL.md`](SKILL.md). Authoring guides:
[work protocols](docs/protocol-authoring.md),
[country packs](docs/country-pack-authoring.md), and a
[DPIA template](docs/dpia-template.md).

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
