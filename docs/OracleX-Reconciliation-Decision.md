# OracleX reconciliation decision

Prepared 18 September 2026 · Assessment of the second proposed plan · OracleX source unchanged

## Decision

The second proposal improves the product direction. Adopt its smaller two-release scope, corpus-first discovery, removal of demo claims, conditional OCR/spreadsheet decisions, simpler UI, and manual fulfillment. Do not adopt its “delete everything first” sequence, six-to-nine-week commitment, weakened accessibility gate, arbitrary-Python wording, or DPDP statement as written.

## Adopt

### Split the pilot into two releases

**Release 1 — Find and verify:** controlled sign-in, authorized document library, safe upload/versioning, evidence-backed questions, exact cited passages, honest abstention, and appropriately scoped audit events.

**Release 2 — Request and review:** request submission, assigned reviewers, immutable reviewed payloads, decisions with reasons, and manual completion recorded separately from approval.

This is a better pilot boundary than shipping document intelligence and workflow automation simultaneously. Release 1 must still be treated as decision support: a citation can be wrong or irrelevant, and people often do not open it. Retrieval and claim support need evaluation before company use.

### Decide from the real corpus

During discovery, measure file types, scanned-page proportion, languages, table/spreadsheet prevalence, average/maximum sizes, confidentiality, document ownership and update frequency. Pull OCR or deterministic spreadsheet features into Release 1 only when representative tasks justify them.

### Keep the narrower interface

Use the existing UI specification with a light default, system font stack, stable URLs, professional tables, explicit states and a conversation area with contextual evidence. Equipment/P&ID screens and refinery styling remain out of scope unless the target company requires them.

### Cut unrelated product surfaces

Remove Messages and Tasks from released navigation unless the pilot has an explicit need that is not already served by another company system. Keep autonomous execution, unsupported vision, invented reports, adaptive proposals, general connectors and streaming outside Release 1.

## Modify

### Replace “delete first” with quarantine, map, then remove

The eight disconnected pages already include `TestCenter`; describing “the eight pages plus TestCenter” double-counts it. Before deletion:

1. Create a route/module inventory and identify any useful behavior or tests in the old pages.
2. Disable demo-only and unsupported capabilities in the production route/navigation manifest.
3. Add regression tests for the security failures and the intended retained journeys.
4. Remove unreachable UI, obsolete assets and unimplemented agent routes in small reviewable changes.
5. Use migrations for stored workflow/adaptation records; do not silently discard existing data.

The anonymous-admin fallback, public demo token endpoint, public seed route, destructive lifespan seed and unconditional simulator are security defects, not ordinary cleanup. Remove or fail-close those immediately in the first security change. Scope cleanup should not delay that work.

### Keep feedback, remove “adaptation” claims

Automatic adaptation should be removed. A small feedback mechanism tied to a conversation/run and source is useful for evaluation and incident triage, provided it has ownership, access, retention and review. Do not imply that feedback retrains or improves the system automatically.

### Use typed spreadsheet operations

“Deterministic computation in Python” must not mean executing LLM-generated or user-supplied Python. Implement a small allowlist of typed operations—filter, group, sum, count, average and domain-approved formulas—in an isolated worker with row/cell limits, timeouts, authorization checks, preserved units and reproducible calculation records. Indexing table text alone is not sufficient for accurate analysis.

### Use a tiered audit design

For a low-risk pilot, truthful append-only application permissions, ordered events, database access controls, atomic mutation/event writes and tested backups may be proportionate. This does not prove that rows were not deleted or rewritten by a privileged database actor. Remove “immutable,” “cryptographic ledger” and compliance claims unless protected checkpoints or equivalent controls are implemented. Upgrade integrity controls when policy, contracts or threat analysis requires them.

### Make identity risk-based

SSO can be deferred when the company has no suitable identity provider. Password-based Release 1 still needs invitations, unique accounts, secure password storage, throttling, session expiry/revocation, recovery, final-admin protection and preferably MFA for administrators or sensitive deployments. If an IdP exists, integrating it can reduce account-lifecycle risk and should be reconsidered.

### Keep accessibility acceptance, defer certification

Formal accessibility certification can be later. Keyboard operation, visible focus, labels, contrast, semantic dialogs, reduced motion, 200% zoom and 320–390 px reflow remain Release 1 acceptance criteria. They are inexpensive when built into the component system and expensive to retrofit.

## Reject or correct

### Six-to-nine weeks is an optimistic best case

One engineer cannot genuinely overlap the documents, UI, deployment and evaluation work described in weeks 3–7. A six-to-nine-week window is plausible only for a sharply constrained proof of concept with mostly digital text, no sensitive pilot data, no OCR, no spreadsheet analysis and limited deployment hardening. For a controlled internal Release 1 from this codebase, use **8–12 weeks as an initial planning range for one focused engineer**, then revise after week-1 corpus and environment discovery. Add roughly **2–4 weeks** if production-quality OCR or spreadsheet analysis enters scope; actual effort depends on formats, languages, accuracy and hardware.

### Security repair must precede broad deletion

Do not spend the first week removing presentation code while protected endpoints remain anonymously accessible. The first executable change should fail closed on authentication and disable destructive/demo production paths, with isolated regression tests. Cleanup can follow in the same first phase.

### “Nothing writes except documents” is inaccurate

Release 1 also writes identities/sessions, audit events, ingestion jobs, document versions, conversations and possibly feedback. The intended restriction should be: Release 1 performs no autonomous external business action and does not modify source business systems.

### DPDP wording needs precision

OracleX is not automatically “the operator” under the statute. The company may be a Data Fiduciary when it determines the purposes and means of processing; vendors may be processors depending on the deployment arrangement. The Act defines a child as an individual under 18. The 13 November 2025 commencement notification brings the central substantive processing, consent, child-data, rights and many fiduciary provisions into force eighteen months after publication, while other provisions have earlier dates. See the official [DPDP Act](https://www.meity.gov.in/static/uploads/2024/02/Digital-Personal-Data-Protection-Act-2023-1.pdf), [commencement notification](https://www.meity.gov.in/static/uploads/2025/11/c56ceae6c383460ca69577428d36828b.pdf), and [DPDP Rules 2025](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf).

Week 1 should still identify the organization’s role, purposes, lawful basis or consent path, personal-data categories, children’s data, access, retention, deletion and incident handling with qualified legal/privacy advice where required. Excluding customer, student and person-level operational records from the pilot can reduce scope, but OracleX still processes employee/account and audit data.

## Improved execution order

1. **Immediate security gate:** isolate test/runtime storage; remove anonymous admin, production demo impersonation, destructive seeding and silent simulator fallback; rotate secrets; restrict origins; add regression tests.
2. **Discovery and release contract:** name the company owner, pilot department, users, corpus, supported file types, personal-data exclusions, target hardware and 3–5 real questions. Define Release 1 non-goals.
3. **Scope cleanup:** hide unsupported routes, preserve useful behavior/tests, then remove obsolete pages/agents/assets with migrations where stored data exists.
4. **Identity and authorization:** invitations or IdP, sessions, recovery, capabilities, audience/classification policy, relationship validation and final-admin protection.
5. **Document foundation:** safe storage keys, versions, idempotent ingestion, durable jobs, parser coverage, exact locations, tombstone deletion, reconciliation and backup.
6. **Evaluated answers:** authorization-aware retrieval, real-company evaluation set, local model/embedding benchmark, evidence mapping and abstention.
7. **Professional UI and accessibility:** Documents → Ask → Source flow, explicit loading/error/denied states, stable URLs and responsive component checks.
8. **Operations and pilot:** reproducible build, meaningful readiness, restore rehearsal, limited non-sensitive pilot, feedback review and measured release decision.

This order preserves the useful simplification in the proposal while keeping the security, evidence and operating controls required for a real company tool.
