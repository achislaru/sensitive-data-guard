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
- Tests: 16 passing (recall, round-trip, fail-closed, audit, passport sign/verify/tamper/expiry, tiered guard, classification).
