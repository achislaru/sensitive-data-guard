# Authoring a work protocol

A work protocol is a vetted, declarative recipe for one kind of task on personal
data. It is **pure YAML — no free prose** (so it can be linted), and it can only
*narrow* the safety baseline, never widen it. This guide shows the format and
the two gates every protocol must pass before it can run.

## Start from the template

```bash
sdg protocol new            # prints a guided spec + a safe template (all
                            # safety fields default to the most restrictive value)
```

You do **not** choose `data_class`. The engine derives it from the data
contract: if an input declares a national-ID entity (`RO_CNP`, `MD_IDNP`), the
class is `special_category` and the only legal `required_path` is `local`. You
cannot sub-classify your way to the cloud.

## The fields

```yaml
schema: 1
id: my-protocol                 # unique, kebab-case
name: "Human-readable name"
version: 1.0.0                  # SemVer; changing it forces re-validate + re-dryrun
author: your-name
locale_scope: [ro_RO]           # locales this protocol DECLARES support for
triggers: ["phrase a", "frază b"]   # task phrases that match this protocol
params: [role]                  # caller-supplied values usable in prompts as {{role}}

inputs:
  - role: candidate_cv          # logical name, usable in prompts as {{candidate_cv}}
    formats: [pdf, docx, txt]
    expected_entities: [PERSON, RO_CNP, EMAIL_ADDRESS]

classification:
  data_class: special_category  # DERIVED, not chosen — must match the inputs
required_path: local            # enum; ≤ the classification baseline

steps:                          # the pipeline, in order
  - { id: detect, op: detect }
  - { id: score, op: ai_local, prompt_ref: score_local,
      expects_output: json, output_schema_ref: cv_score }
  - { id: out, op: emit, handling: local_only }

prompts:                        # the ONLY natural-language content; placeholders
  local:                        # must be declared inputs or params
    score_local: |
      Score this CV for "{{role}}". Decision support only; a human decides.
      {{candidate_cv}}
  cloud: {}                     # empty unless the path allows cloud

schemas:                        # output schemas referenced by steps
  cv_score:
    type: object
    required: [score, rationale]
    properties: { score: {type: integer}, rationale: {type: string} }

output:
  contains_pii: false           # true is only legal on a local path
  destination: file             # enum; NO external sinks exist

audit:
  category: hr_recruitment      # drives retention class + Art. 22 heuristic
  retention_class: short

hitl:
  art22_decision: true          # require a human decision gate (Art. 22)
  gate_message: "AI output is support only; a human makes the decision."
```

## Pipeline ops

| op            | what it does                                                    |
| ------------- | --------------------------------------------------------------- |
| `detect`      | run PII detection (country-pack recognizers)                    |
| `pseudonymize`| replace PII with stable pseudonyms (needed before any cloud step) |
| `ai_local`    | local-model generation; uses `prompts.local`                    |
| `ai_cloud`    | cloud-model generation; needs a non-local path + `prompts.cloud`|
| `restore`     | put real values back (must come after `pseudonymize`)           |
| `emit`        | produce output; `handling: local_only` keeps it on-machine      |

`ai_*` steps are where the **engine hands control to the agent**: it renders the
prompt over already-pseudonymized text and returns a JSON directive; the agent
runs the model and calls `sdg protocol resume`.

## The two gates (mandatory)

```bash
sdg protocol validate --file my-protocol.yaml    # layers 1 (schema) + 2 (semantic)
sdg protocol dryrun  --id my-protocol            # full pipeline on synthetic data,
                                                 # cloud step stubbed, re-scan included
```

`validate` exits `2` on any error and prints exact remediation. What the
semantic linter enforces (beyond the schema):

- `required_path` must be within the classification baseline (more restrictive
  only).
- `ai_cloud` requires a non-local path and a non-empty `prompts.cloud`;
  `ai_local` requires `prompts.local`.
- `restore` must be preceded by `pseudonymize`.
- At least one `locale_scope` locale must be installed (warns per missing one —
  `locale_scope` is *declared* support, not a per-machine requirement).
- Every `{{placeholder}}` must be a declared input role or param.
- Every `output_schema_ref` must resolve to a `schemas` entry.
- `output.contains_pii: true` is illegal on a non-local path.
- Art. 22 heuristic: HR/credit/discipline/performance categories warn unless
  `hitl.art22_decision: true`.

`dryrun` runs the whole pipeline against synthetic fixtures with the cloud step
stubbed and the outbound re-scan active — proving the recipe is executable and
leak-free before any real data touches it. A protocol can only be used once
**both** gates pass; the engine records a checksum, and editing the file forces
re-validate + re-dryrun.

## Sharing

```bash
sdg protocol export --id my-protocol > my-protocol.yaml   # appends a checksum
sdg protocol import --file my-protocol.yaml               # re-runs validate + dryrun
```

Distribution adds no authority: an imported protocol must pass both gates on the
importing machine before it is installed to `~/.config/sdg/protocols/`. Built-in
protocols live read-only in the package; community protocols go through PRs with
CI running `validate` + `dryrun` on each.

## Built-ins to learn from

`hr-cv-screening` (special-category, strictly local), `invoice-processing`,
`payroll-analysis` (aggregate-only), `contract-review` (cloud-pseudonymized),
`expense-reconciliation` (tabular, column rules), `gdpr-subject-request`
(Art. 15, strictly local). Read them under `src/sdg/protocols/builtin/`.
