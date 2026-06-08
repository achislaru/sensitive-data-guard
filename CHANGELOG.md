# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versions use [SemVer](https://semver.org/).

## [Unreleased]

### Added
- F0: repository scaffold, packaging (`pyproject.toml`), MIT license, `.gitignore` (secrets/state never committed).
- F1: pilot extraction into `src/sdg` — `CountryPack` interface, `ro_RO` pack (CNP/CUI/IBAN recognizers with check-digit validation, CSV column rules, deterministic synthetic-data generator), detection engine, encrypted mapping vault, fail-closed pseudonymization pipeline, types-only audit trail with retention.
- F3: certification subsystem — software component probes, machine technical audit (RAM/disk/disk-encryption/Ollama-bind/vault-key, cross-platform), local-model capability benchmark, and a signed (HMAC) machine passport with 30-day freshness + tamper/version invalidation.
- F4: tiered fail-closed guard — `resolve_paths` (disk-encryption/vault-key gate ALL PII paths; Ollama/RAM/benchmark gate the local path) and `preflight`. Data classification table (`special_category` → local only).
- F2: full CLI — `certify`, `preflight`, `classify`, `pseudonymize` (session vault, exit 2 on outbound-PII hard stop), `restore`, `audit log|retention|summary`.
- F8: work-protocol library (meta-skill). Declarative YAML protocols with a
  3-layer safety model — layer 1 structural (JSON Schema: special-category data
  cannot be routed to a cloud path; no external output sinks), layer 2 semantic
  linter (path ≤ classification baseline, ai_cloud needs non-local path + cloud
  prompt, restore-after-pseudonymize, placeholder hygiene, Art. 22 heuristic),
  layer 3 runtime (the unconditional outbound re-scan still applies). Execution
  engine with `run`/`resume` (CLI does detect/pseudonymize/restore/audit; the
  LLM only generates the ai_* step on already-pseudonymized text) and headless
  `dryrun` against synthetic fixtures. Six built-in protocols (hr-cv-screening,
  invoice-processing, payroll-analysis, contract-review, expense-reconciliation,
  gdpr-subject-request). CLI: `protocol list|validate|dryrun|run|resume|new|
  export|import`. Audit entries now carry `protocol_id`.
- Tests: 28 passing (12 new: schema/linter, the no-special-to-cloud invariant,
  undeclared-placeholder rejection, dryrun across all six built-ins).
