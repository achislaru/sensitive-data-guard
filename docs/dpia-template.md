# DPIA template

A Data Protection Impact Assessment (GDPR Art. 35) is required before processing
that is likely to result in a high risk to individuals — which using AI on
special-category or large-scale personal data usually is. Fill one out **per
work protocol** before putting it into production. `sdg` enforces the technical
controls; this document records the legal reasoning that justifies them.

> This is a working template, not legal advice. Have it reviewed by your DPO or
> counsel.

---

## 1. Identification

- **Protocol id / version:**
- **Owner (controller):**
- **DPO / reviewer:**
- **Date / review-by date:**
- **Legal basis (Art. 6):** _(e.g. legitimate interest, contract, consent)_
- **Special-category condition (Art. 9), if applicable:**

## 2. Processing description (Art. 35(7)(a))

- **Purpose:** _what the protocol does and why._
- **Data subjects:** _e.g. job candidates, employees, customers._
- **Data categories:** _map to detected entities (PERSON, RO_CNP, IBAN, …)._
- **`data_class` (derived):** `special_category` / `personal_pseudonymizable` /
  `non_personal`
- **`required_path`:** `local` / `cloud_pseudonymized` / `cloud_direct`
- **Recipients / sub-processors:** _local model only? which cloud model?_
- **Retention:** _audit `retention_class`; conversations 90d / audit 12mo._
- **Channels:** _CLI / Telegram / Slack — note the channel pre-gate policy._

## 3. Necessity & proportionality (Art. 35(7)(b))

- **Data minimization:** _why each input is needed; what is excluded._
- **Why AI:** _why automated processing is necessary for the purpose._
- **Pseudonymization:** _confirm cloud paths send pseudonyms only (`sdg`
  enforces fail-closed)._
- **Automated decision-making (Art. 22):** _does the output decide about a
  person? If yes, `hitl.art22_decision: true` and a human gate are required._

## 4. Risks to data subjects (Art. 35(7)(c))

| Risk                                   | Likelihood | Severity | Mitigation (`sdg` control)                              |
| -------------------------------------- | ---------- | -------- | ------------------------------------------------------- |
| PII leaks to a cloud model             |            |          | Fail-closed outbound re-scan; pseudonymize-before-cloud |
| Special-category data on a wrong path  |            |          | Schema + classification baseline; `local`-only routing  |
| Special-category data over Telegram    |            |          | Channel pre-gate → quarantine + incident log            |
| Re-identification from the audit log   |            |          | Types-only audit (never values)                         |
| Processing on an unqualified machine   |            |          | `certify` + signed passport + `preflight` gate          |
| Unsafe protocol / instruction          |            |          | Linter + dryrun gates; runtime guard is authoritative   |
| Over-retention                         |            |          | `sdg audit retention` (90d / 12mo)                      |

## 5. Measures to address risks (Art. 35(7)(d))

- **Technical:** _list the `sdg` controls relied on (above)._
- **Organizational:** _access control, training, incident response, the
  quarantine-review process for `ingest-scan` incidents._
- **Residual risk after mitigation:** _low / medium / high — and acceptance._

## 6. Outcome

- **Approved by:**
- **Date:**
- **Conditions / follow-up:**
- **Next review:**

---

### Art. 33 note

`sdg` quarantines special-category data that arrives on an unapproved channel
and logs an **incident-candidate** — this is an Art. 33 *assessment trigger*,
not an automatic breach notification. A human must assess whether the 72-hour
notification duty applies. The incident log lives in the state quarantine
directory.
