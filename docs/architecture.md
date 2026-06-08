# Architecture

`sdg` is a GDPR-compliant guard for AI agents that work with personal and
special-category data. It is a Python CLI plus an optional skill layer. The
design goal is simple to state and hard to violate: **validated PII never
reaches a cloud model, and no instruction can widen what the machine is
certified to allow.**

## The one-line model

```
input → classify → [pre-gate] → detect → pseudonymize → AI step → restore → emit
                                              │
                                              └── re-scan output: residual
                                                  validated PII → REFUSE (exit 2)
```

Local-only data (national IDs, payroll, CVs) is processed by a local model and
never leaves the machine. Cloud models only ever see pseudonymized text.

## Subsystems

```
┌─────────────────────────────────────────────────────────────────┐
│ 6. protocols/        work-protocol library (the meta-skill)       │
│    schema · linter · engine(run/resume) · loader · 6 builtins     │
│    ── can only NARROW the layers below, never widen them ──       │
├─────────────────────────────────────────────────────────────────┤
│ 5. channels.py       channel × data-class pre-gate                │
│    (Telegram/Slack special-category → quarantine + incident)      │
├─────────────────────────────────────────────────────────────────┤
│ 4. guard.py          tiered fail-closed gate + preflight          │
│    passport.py       HMAC-signed machine passport (30-day fresh)  │
│    certify.py · components.py · machine.py · benchmark.py         │
├─────────────────────────────────────────────────────────────────┤
│ 3. classify.py       data-class → allowed-paths baseline table    │
├─────────────────────────────────────────────────────────────────┤
│ 2. pipeline.py       fail-closed pseudonymize (outbound re-scan)  │
│    vault.py          encrypted, stable pseudonym mapping          │
│    audit.py          types-only log + retention                   │
├─────────────────────────────────────────────────────────────────┤
│ 1. detect.py         detection engine (Presidio + spaCy)          │
│    packs/            country packs: recognizers + validators +    │
│                      synthetic generators (ro_RO, md_MD)          │
└─────────────────────────────────────────────────────────────────┘
```

Each layer is authoritative for its own invariant; higher layers can restrict
but not relax. A protocol cannot bring weaker recognizers (detection belongs to
the country pack), cannot route special-category data to the cloud (the schema
makes that unrepresentable), and cannot suppress the outbound re-scan (it is
unconditional).

## Processing paths and the classification baseline

Three paths, ordered most → least private:

| data class                  | allowed paths                                   |
| --------------------------- | ----------------------------------------------- |
| `special_category`          | `local`                                         |
| `personal_pseudonymizable`  | `local`, `cloud_pseudonymized`                  |
| `non_personal`              | `local`, `cloud_pseudonymized`, `cloud_direct`  |

National-ID entities (`RO_CNP`, `MD_IDNP`) force `special_category`. The table
lives in `classify.py` and is the single source of truth; protocols intersect
with it, the guard intersects it with the machine passport.

## Certification and the passport (fail-closed, tiered)

`sdg certify` audits the machine and writes an HMAC-signed passport
(`~/.local/state/sdg/passport.json`, 30-day freshness, invalidated by version,
model, or tamper changes). `sdg preflight` verifies it on every sensitive task.

`guard.resolve_paths()` applies the tiers:

- **Tier 1 — encryption / key.** Disk encryption OFF or a loose-permission
  vault key disables **all** PII paths (`local` and `cloud_pseudonymized`);
  `cloud_direct` (non-PII only) survives.
- **Tier 2 — local prerequisites.** Ollama unreachable / wrong bind / RAM too
  low / model benchmark fail disables only the `local` path.
- **Detection stack.** A broken Presidio/spaCy/cryptography stack disables both
  PII paths.
- **Pack self-test.** A failing country pack disables PII paths for that locale.

The local-model **benchmark** gate is real: a model that can't reliably echo
synthetic CNPs/IBANs (e.g. one stuck in mandatory "thinking" mode) fails and the
local path is withheld. `gemma3:27b` passes 20/20; `qwen3-vl` does not.

## The fail-closed guarantee

`pipeline.pseudonymize()` re-scans its own output and raises `OutboundPiiError`
(CLI exit `2`) if any validated PII remains. This is unconditional — it runs
regardless of protocol, path, or caller. The mapping vault (`vault.py`,
SQLite + Fernet) refuses to open with a loose-permission key and produces
stable `[LABEL_NNN]` pseudonyms so `restore` is exact.

## Audit trail

`audit.py` logs **types and counts only — never values** (an assertion rejects
any non-int count, so the log can't become a leak). Entries carry the
processing path, source channel, and `protocol_id`. `apply_retention()` deletes
conversations after 90 days and anonymizes audit entries after 12 months.

## Channels: Telegram / Slack

In an agent ecosystem the transport is a **dumb pipe** — it never calls a cloud
AI itself; files land on the same machine as the local model. But data that
arrived over a remote channel has *already* transited a provider's servers, so
`channels.py` applies a channel × data-class policy:

| data class                  | local channel | remote (Telegram/Slack) |
| --------------------------- | ------------- | ----------------------- |
| `non_personal`              | allow         | allow                   |
| `personal_pseudonymizable`  | allow         | **warn**                |
| `special_category`          | allow         | **quarantine**          |

Quarantine moves the file into state and logs a DPIA incident-candidate
(Art. 33 *assessment*, not auto-notification). Binary attachments on a remote
channel can't be content-scanned, so they `warn`. `sdg ingest-scan` exits `2`
on quarantine.

The optional `hooks/ingest_scan.py` (`UserPromptSubmit`) automates this: it
finds file paths in the prompt, infers the channel from the path
(`telegram-images/` → telegram, `slack-files/` → slack), runs `ingest-scan`,
and either blocks the turn (quarantine) or injects a warning. It is
**transport-agnostic and requires zero modifications to the host agent
runtime**, and it fails *open* on its own errors — the CLI/protocol layer stays
authoritative.

Install it in Claude Code `settings.json`:

```json
{ "hooks": { "UserPromptSubmit": [
  { "hooks": [ { "type": "command",
    "command": "python3 ~/.claude/skills/sensitive-data-guard/hooks/ingest_scan.py" } ] }
] } }
```

## Work protocols (the meta-skill)

Rather than improvising every task, agents run vetted, declarative **work
protocols** (`protocols/`). A protocol is pure YAML — id, triggers, data
contract, `data_class → required_path`, pipeline steps, per-path prompt
templates, output rules, audit class, Art. 22 human-in-the-loop gates. Safety is
three layers:

1. **Structural (JSON Schema).** Illegal states are unrepresentable — no "cloud"
   value for special-category data, no external output sinks, no "skip
   detection".
2. **Semantic linter** (`sdg protocol validate`). Path ≤ classification
   baseline, `ai_cloud` needs a non-local path + a cloud prompt, restore must
   follow pseudonymize, placeholder hygiene, an Art. 22 heuristic.
3. **Runtime.** The guard, classification, detection, and the unconditional
   outbound re-scan still apply — a lying protocol cannot beat the gate.

At runtime the engine is a deterministic state machine: `sdg protocol run`
sequences the CLI primitives and stops at `ai_*` steps, handing the agent a JSON
directive (rendered prompt + expected output schema) over **already-pseudonymized
text**; the agent runs the model and returns via `sdg protocol resume`. The CLI
owns the gate, classification, detection, pseudonymization, restore, output
validation, audit, and retention. The LLM owns **only** the generation step.

See [protocol-authoring.md](protocol-authoring.md) to write one and
[country-pack-authoring.md](country-pack-authoring.md) to add a locale.

## State layout (XDG; never committed)

```
~/.local/state/sdg/      vault.db · vault.key · passport.json · audit/ ·
                         quarantine/ · conversations/ · sessions/
~/.config/sdg/           protocols/ (user-authored)
~/.local/share/sdg/      builtin data
```

Secrets and machine-local state are never committed (`.gitignore`). The repo
contains zero real PII; all fixtures are deterministic with valid-but-fictitious
check digits.
