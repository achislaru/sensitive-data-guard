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
- F9: channel pre-gate (`src/sdg/channels.py`, CLI `ingest-scan`). Channel ×
  data-class policy matrix — special-category data arriving on a remote channel
  (Telegram/Slack) is quarantined (file moved to state, DPIA incident-candidate
  logged) with a remediation message; personal data warns; non-personal allows.
  Local channels (cli) never quarantine. Binary attachments on remote channels
  warn (cannot be content-scanned). Optional, transport-agnostic
  `hooks/ingest_scan.py` (`UserPromptSubmit`) infers the channel from the file
  path and blocks/annotates the turn — zero modifications to cortextOS code, and
  fail-open on hook errors (the CLI/protocol layer stays authoritative).
- Tests: 32 passing (4 new: special-category on Telegram quarantined + incident
  logged, special-category on a local channel allowed, non-personal on Telegram
  allowed, missing file allowed).
- F7: Moldova country pack (`md_MD`) — IDNP (person) and IDNO (legal entity)
  state-ID validators (shared 7-3-1 mod-10 checksum, disambiguated by context),
  IBAN-MD (mod-97), `+373` phones, deterministic synthetic generator, and
  Romanian-language CSV column rules. Reuses the Romanian spaCy model
  (`ro_core_news_lg`) — proving the language-model / country-validator split.
  `MD_IDNP` forces `special_category`. The generic CSV scanner moved to a shared
  `sdg.packs.tabular` module (ro_RO/md_MD supply only header vocab). Tests:
  validators, 100%-recall IDNP/IBAN detection, special-category routing.
- F6: agent-facing layer. `SKILL.md` (skill frontmatter + triggers; protocol-
  first workflow, manual primitives as fallback, the condensed rules). One-
  command `install.sh` (venv + editable install + spaCy model per locale, with
  `md_MD` mapped to the shared Romanian model, then `certify`). `docs/`:
  architecture (subsystem map, paths, certification tiers, channels, protocols,
  state layout), protocol-authoring, country-pack-authoring, and a DPIA template
  (Art. 35). README status refreshed.
