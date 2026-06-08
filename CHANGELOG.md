# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versions use [SemVer](https://semver.org/).

## [Unreleased]

### Added
- F0: repository scaffold, packaging (`pyproject.toml`), MIT license, `.gitignore` (secrets/state never committed).
- F1: pilot extraction into `src/sdg` — `CountryPack` interface, `ro_RO` pack (CNP/CUI/IBAN recognizers with check-digit validation, CSV column rules, deterministic synthetic-data generator), detection engine, encrypted mapping vault, fail-closed pseudonymization pipeline, types-only audit trail with retention.
