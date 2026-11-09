# OracleX review comparison and improvements

Prepared 18 September 2026 · Comparison only · OracleX source unchanged

## Conclusion

The pasted review is strongest as a defect list for the original hackathon/demo build. Its verified security, retrieval, ingestion, workflow and repository findings substantially agree with the main OracleX audit. It did not reveal a missing critical security category. It did add useful concrete evidence in a few areas, now incorporated into the audit.

Its product strategy should not be adopted unchanged. It assumes OracleX must impress MRPL/SIH judges, that the target domain is a refinery, that six people can work for about three weeks, and that the machine has a particular RTX 4060 configuration. The current requirement is an internal tool for a real company. Company workflows, documents, identity, retention rules, deployment hardware and risk policy must determine the design.

## What the pasted review added

| Addition | Assessment | Improved treatment |
|---|---|---|
| The archive has 22 page files | Correct | Fourteen are imported by the active App and eight are disconnected. Count and distinguish source inventory from shipped navigation. |
| Six duplicate Travel Policy database rows | Correct and useful | Treat this as evidence that ingestion lacks idempotency/deduplication. Use document/version identities, content hashes where useful, an idempotency key, and a deliberate “new version vs duplicate” choice. |
| Login does not normalize email | Correct | Normalize consistently before lookup and enforce normalized uniqueness at the database boundary. This is smaller than the auth bypass but belongs in the identity fix. |
| `our` matches `hour`, `your`, and `four` | Correct | Remove substring-based policy/routing decisions. Use explicit modes or token-aware deterministic classification and evaluate it on representative prompts. |
| DOCX/PPTX can fall through to text parsing | Correct in effect | Reject unsupported formats before storage/indexing or add real parsers. Never label undecodable binary content as indexed. |
| No root `.gitignore` or `.env.example` | Correct | Add clean-build exclusions and a reviewed environment template with no usable secrets. This belongs to reproducible deployment, not core product functionality. |
| Default nginx lacks an API proxy and SPA fallback | Correct | Serve UI and API from one controlled HTTPS origin, proxy `/api`, and route valid client paths to the SPA entry point. |
| Ollama startup/model preparation is incomplete | Correct | Add an explicit model provisioning step, exact version/profile, readiness checks, failure reporting and an offline installation manifest. Do not equate a started container with usable inference. |

## Already covered well in the main audit

The following were already present with evidence, impact, changes and acceptance conditions: anonymous administrator access; public impersonation and seeding; destructive startup seeding; hardcoded secrets and broad CORS; missing endpoint capability checks; approval and audit information leaks; upload traversal and overwrite; company-wide audience defaults; inconsistent retrieval authorization; self-approval and arbitrary states; non-executing approvals; weak audit integrity; incomplete audit coverage; fake vision/data/report behavior; hash embeddings; misleading simulation and confidence; missing conversation persistence; row truncation and missing OCR; disconnected pages; local tab navigation; Google Fonts; hardcoded API origin; fake Messages; stale README/test claims; dependency and migration problems; weak health checks; missing limits and observability; and accessibility/responsive defects.

The main audit goes further in areas the pasted review underplays: destructive production startup; indirect data leakage through approval payloads and raw audit queries; department-only uploads becoming company-wide; cross-company foreign IDs and final-admin lockout; failed deletion leaving searchable vectors and files; prompt injection; test fixtures touching configured storage; transaction boundaries around audit writes; concurrency/idempotency; retention, backup and restore; error states that look like empty success; accessibility; and the distinction between classification, role and administrative permission.

## Recommendations that need improvement

### Do not reseed for MRPL unless the real company is a refinery

A fictional refinery demo, MOC workflow, P&ID tag matching, corrosion calculations and ISA-101 visual language are sensible only for an industrial pilot with those actual needs. For a general company tool they create another layer of convincing-looking fiction. Replace the demo corpus with a sanitized, approved sample of the target company's real document classes and workflows. If those cannot be obtained yet, use neutral fixtures clearly marked as illustrative.

### Do not choose model names before evaluation

“Use a 7–8B model,” `nomic-embed-text`, or `bge-m3` is a hypothesis, not a design decision. Benchmark candidate local models on the actual languages, abbreviations, document formats, answer tasks and deployment hardware. Record quality, memory, latency, concurrency and license constraints. Maintain one supported production profile per hardware tier; repeatedly swapping several large models can produce poor latency and operational complexity.

### Avoid a framework-first agent rewrite

LangGraph does not make unreliable tools reliable. First ship a narrow evidence-backed document answer flow, deterministic calculations for explicitly supported tables, and a typed request/approval state machine. Add orchestration only when a measured user journey genuinely needs multi-step tool use. Every tool needs a schema, authorization, time/resource limit, idempotency behavior, audit event, error contract and human review rule.

### Fix retrieval with a full authorization and indexing design

Adding only `clearance_level <= user_level` to Chroma is insufficient. Eligibility also depends on company, audience, department, current document version, lifecycle state and explicit grants. Filter candidates using the canonical policy, then recheck current SQL state before prompt assembly. Use a durable ingestion job/outbox, index generation and parser/model versions, reconciliation metrics and an explicit rebuild command. Automatically rebuilding everything at every startup is expensive and can hide corruption.

### Do not call similarity “confidence”

Retrieval distance is not a probability that an answer is correct. The UI should show source support such as supported, partial, or no company evidence, based on an evaluated claim-to-source process. Numeric confidence should appear only if it has been calibrated and validated for a defined task.

### Make approval execution explicit and recoverable

Approval should bind to an immutable payload/version, block self-review, validate the reviewer's scope and use a conditional state transition. Approval and completion are different. An execution worker needs idempotency, reauthorization, receipts, retry, failure and rollback/compensation behavior. For the first company pilot, manual fulfillment recorded as a separate completion may be safer than automatic execution.

### Strengthen audit integrity beyond a hash chain

A chained sequence plus database rules detects more tampering than the current row checks, but a privileged database writer can rewrite a whole chain. Canonicalize complete events, use append-only application permissions, ordered per-company sequences, protected signing/checkpoint keys and independently stored checkpoints or immutable retention if company policy requires it. “Integrity verified” must state the checked range and checkpoint; it must not claim legal compliance.

### Prove offline operation outside the application

A `psutil` counter inside OracleX is not adequate proof of network isolation and can miss DNS, child processes, containers and blocked attempts. Enforce egress controls at the host/network boundary and verify browser, API, model runtime and update paths with packet capture/firewall logs during representative journeys. The app can display measured readiness, but it should not certify its own isolation.

### Treat OCR and vision as assisted extraction

OCR is useful when the pilot corpus needs it. P&ID interpretation, engineering measurements and pass/fail decisions need domain-specific evaluation and qualified review. Preserve the source image/page, bounding boxes, extracted text, model/version and corrections. Never turn a vision response directly into an operational action.

### Keep the UI enterprise-focused

The pasted visual rules—opaque surfaces, restrained color, local fonts, dense tables, stable URLs and evidence links—are good. ISA-101 and equipment/P&ID screens should be conditional on the company domain. A two-pane conversation plus contextual evidence drawer is easier to use at common laptop widths than a permanently crowded three-pane workbench. Keep run details optional and never present scripted reasoning as proof. System fonts are the safest offline default; a self-hosted font is reasonable after licensing and packaging review.

### Use a real-company schedule

The pasted 15-day plan is a competition cut-down, not a responsible internal rollout. It combines security repair, identity, retrieval replacement, OCR, multimodal inference, workflow execution, audit hardening, complete UI replacement and evaluation. The roadmap's 10–14 calendar-week estimate assumes two engineers plus part-time design, QA/security and IT support and still requires a controlled pilot. A solo implementation is more plausibly four to six months. These are planning estimates; actual scope depends on the pilot corpus, IdP, deployment environment and approval policy.

## Revised priority order

1. Remove anonymous/demo access and destructive seeding; rotate secrets and isolate production storage.
2. Define the target company's identity, authorization, document audience, retention and approval policies.
3. Make uploads safe, versioned, idempotent and recoverable; add explicit supported-format coverage.
4. Repair route contracts, stable URLs, session handling and the Documents → Ask → Request journey.
5. Build evaluated, authorization-aware retrieval with exact evidence links and honest abstention.
6. Implement persistent conversations and reviewable requests; automate only narrow approved actions.
7. Add append-only audit events, protected checkpoints, measured health, backups and restore rehearsal.
8. Run a limited pilot, measure retrieval/support/latency and expand only from observed company needs.

## Changes made to the review materials

The main audit now records the six duplicate Travel Policy rows, login normalization mismatch, `our` substring bug, PPTX/DOCX fall-through, exact count of 22 pages and 852 inline style attributes, missing root deployment files, default nginx gaps and incomplete model readiness. No OracleX application or source file was changed.
