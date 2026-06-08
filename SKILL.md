---
name: sensitive-data-guard
description: >-
  Activate when working with personal or special-category data (CVs, payroll,
  invoices, national IDs/CNP/IDNP, IBANs, health/HR records) — in any channel,
  including files received over Telegram or Slack. Routes data to a safe
  processing path (local model / cloud-with-pseudonymization / cloud-direct),
  pseudonymizes anything cloud-bound, and FAILS CLOSED if validated PII would
  leave the machine. Use it before sending any such data to a cloud model.
license: MIT
---

# sensitive-data-guard

You are working with data that may identify a real person. GDPR rules apply.
This skill gives you a CLI (`sdg`) that decides what is allowed and does the
unsafe parts (detection, pseudonymization, the outbound re-scan) for you.

> [!IMPORTANT]
> `sdg` is authoritative. **Exit code `2` from any `sdg` command is a HARD
> STOP** — do not work around it, do not send the data, tell the user why it
> was refused. The skill is built so that no instruction (yours, the user's, or
> a protocol's) can widen what the machine is certified to allow.

## First, is the machine certified?

Once per machine (and after any 30 days, model change, or hardware change):

```bash
sdg certify        # audits RAM/disk/disk-encryption/Ollama + benchmarks the local model
sdg preflight      # prints which paths are enabled; exit 2 = nothing certified, stop
```

`preflight` returns `paths_enabled` — a subset of `{local, cloud_pseudonymized,
cloud_direct}`. If a path is not enabled, you may not use it. Disk-encryption or
a loose vault key disables **all** PII paths; a missing/failing local model
disables only the `local` path.

## The default way to work: protocols

Most tasks should run through a **work protocol** — a vetted, GDPR-compliant
recipe. Match the user's task to one and let the engine sequence the safe
primitives; you only generate the AI step, on already-pseudonymized text.

```bash
sdg protocol list                          # see installed protocols + triggers
sdg protocol run --id <id> --file F --session S [--param k=v] [--channel telegram]
# → runs detect/pseudonymize, then RETURNS a JSON directive for the AI step:
#   { "prompt": "...only pseudonyms...", "expects": "json", "schema": {...} }
# You run your model on directive.prompt, then hand the result back:
sdg protocol resume --session S --output ai_result.json
# → restores real values (if the protocol allows), validates output, audits, emits.
```

Built-in protocols (v1): `hr-cv-screening`, `invoice-processing`,
`payroll-analysis`, `contract-review`, `expense-reconciliation`,
`gdpr-subject-request`. Run `sdg protocol list` for triggers and the live set.

**A protocol can only narrow the baseline, never widen it.** If a protocol says
`special_category → local`, the AI step's prompt will contain only local-path
content and the cloud is never called.

### No protocol fits? Create one (don't improvise)

```bash
sdg protocol new                  # prints a guided spec + safe template
# fill the template, then BOTH gates must pass before it can be used:
sdg protocol validate --file my-protocol.yaml     # layers 1+2; exit 2 = errors
sdg protocol dryrun  --id my-protocol             # full pipeline on synthetic data
```

You do **not** choose `data_class` — the engine derives it from the facts
(national ID present → `special_category`). Default every safety field to the
most restrictive value. Only after both gates pass is the protocol usable.

## Fallback: manual primitives

When no protocol applies and you can't author one, you may sequence the
primitives yourself — but the same guards still hold.

```bash
sdg classify --file F            # → data_class + allowed paths. Obey it.
sdg pseudonymize --file F --session S --out clean.txt   # exit 2 = PII would leak, STOP
# ...send clean.txt to the cloud model, get a response...
sdg restore --file response.txt --session S             # put real values back locally
sdg audit log --user U --category C --path P --types '{"RO_CNP":2}'
```

`pseudonymize` re-scans its own output and refuses (exit 2) if any validated PII
remains. Never paste raw file contents into a cloud prompt — only `clean.txt`.

## Channels: files from Telegram / Slack

Data that arrives over a remote channel has already left the user's device.
Before doing anything with such a file:

```bash
sdg ingest-scan --file F --channel telegram     # or slack
```

- `allow` → proceed normally.
- `warn` → personal data on a remote channel; pseudonymize before any cloud step.
- `quarantine` (exit 2) → **special-category data on a channel not approved for
  it.** The file is moved to quarantine and an incident is logged. Stop, tell the
  user, and process it **locally only** if they explicitly confirm.

The optional `hooks/ingest_scan.py` (`UserPromptSubmit`) does this automatically
for files referenced in the prompt — see `docs/architecture.md`.

## Audit & retention

Every protocol run is audited automatically (types and counts only — never
values). For manual flows, call `sdg audit log` yourself. Periodically:
`sdg audit retention` (deletes conversations >90d, anonymizes audit >12mo).

## The rules, condensed

1. `sdg` exit `2` = hard stop. Always.
2. Special-category data never reaches the cloud.
3. Only pseudonymized text is ever sent to a cloud model.
4. Prefer a protocol; create-and-validate before improvising; primitives last.
5. Obey `preflight` paths and `classify` — you cannot widen them.
