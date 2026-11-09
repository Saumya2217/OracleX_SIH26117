# OracleX roadmap and implementation plan

Living plan · Updated 10 November 2026

**Target:** a reliable, professional and offline-capable internal company document and request workspace.

## Current position

OracleX has completed the source work for its first six implementation milestones and is implementing Milestone 07 in focused batches. Milestones 03–06 still require target-host, approved-model, representative-corpus, PostgreSQL and recovery acceptance. It is a materially safer development build, but it is not ready for confidential company data or a production pilot.

| Milestone | Status | Verified outcome |
|---|---|---|
| 01 · Security foundation | **Completed** | Authentication fails closed; production demo routes are disabled; bootstrap is protected; permissions, uploads, tasks, requests and audit access were hardened |
| 02 · Migrations and UI foundation | **Completed** | Alembic baseline added; runtime schema creation removed; professional responsive shell added; disconnected prototype pages removed; frontend lint/build clean |
| 03 · Offline deployment foundation | **In progress · acceptance pending** | Offline packaging, verified model import, internal runtime networking and operator tooling are implemented; clean disconnected-host proof remains |
| 04 · Versioned document ingestion | **Implemented in source · acceptance pending** | Immutable versions, durable jobs/outbox, worker leases/retries, current-version retrieval, reconciliation, archive/restore and the professional document register pass local tests |
| 05 · Evaluated retrieval and evidence | **Implemented in source · acceptance pending** | Permission-filtered hybrid retrieval, explicit abstention/generation modes, immutable source citations and source integrity checks pass a 20-case synthetic development evaluation; approved company-corpus/model acceptance remains open |
| 06 · Persistent assistant and requests | **Implemented in source · acceptance pending** | Owned conversations, immutable citation records, contextual follow-ups and typed/versioned requests pass local tests; PostgreSQL concurrency and target restart proof remain |
| 07 · Complete professional UI | **In progress** | Core routes/pages, scoped cache with in-flight refresh, expanded OpenAPI typing, setup form and Audit pagination are implemented and selected views were checked live; full accessibility, state-matrix and staff acceptance remain |
| 08 · Operations and controlled pilot | Planned | PostgreSQL, restore, security, offline and capacity gates pass on company hardware |

The current downloadable source and Milestone 07 progress are documented in `OracleX-Milestone-07-Professional-UI-Progress.md`. Retrieval evaluation evidence remains in the Milestone 05 report and JSON record.

## Product scope

The first production release is a **single-company internal system**. It should help employees find approved company information, inspect the supporting source and submit accountable requests. It should not act as a public SaaS platform or perform arbitrary autonomous operations.

The first release must support three complete journeys:

1. **Find and verify:** sign in → find an authorized document → ask a question → inspect the cited passage and exact document version.
2. **Request and review:** create a structured request → inspect its effect → submit → assigned reviewer records a reason → requester sees the decision and separate completion state.
3. **Maintain knowledge:** authorized owner uploads a document → the system scans, extracts and indexes it → failures are visible and retryable → a replacement creates a version → archive or revocation immediately affects retrieval.

## Non-negotiable requirements

- The deployed application must operate with outbound internet access disabled after installation.
- A fresh air-gapped installation must use approved local artifacts rather than a hidden online download.
- Authentication and authorization are enforced by the backend on every protected resource.
- Document clearance does not imply administrator authority.
- Company answers show real evidence. OracleX must abstain when an authorized source does not support the answer.
- Model or index failure is visible. The application must never silently replace unavailable inference with simulated output.
- An approved request is distinct from a completed action.
- Upload, indexing and deletion failures must be recoverable and visible.
- The interface uses opaque surfaces and restrained business styling. No glassmorphism, backdrop blur, gradients, glowing panels, AI mascots or fabricated operational metrics.
- Compliance, privacy, integrity and isolation claims must be based on measured deployment evidence.

## Architecture decisions

| Area | Initial decision | Review condition |
|---|---|---|
| Deployment | One company instance on a private network with HTTPS ingress | Revisit only if another company or legal boundary must share infrastructure |
| Offline operation | Package all runtime artifacts locally and deny outbound traffic during acceptance testing | Mandatory before pilot |
| Primary database | PostgreSQL in deployed environments; SQLite only for isolated development/tests | PostgreSQL integration must pass before pilot |
| Schema | Alembic migrations applied before application startup | Every schema change requires upgrade and rollback/recovery evidence |
| Document files | Versioned local/company-controlled storage with generated identifiers | Object storage may replace filesystem storage if company operations require it |
| Retrieval index | One private Chroma server owns persistence; API/worker use HTTP clients; index remains rebuildable | Replace only when evaluation or operating evidence justifies it |
| Embeddings | Compare current lexical/deterministic baseline with locally packaged models | Choose using the company evaluation corpus, latency, hardware and licence |
| Inference | Local Ollama adapter with an approved preloaded model | Model/version must be recorded for each generated run |
| Model unavailable | Explicit unavailable state; optional clearly labelled extractive mode | No implicit simulator in company environments |
| Identity | Managed credentials initially; integrate company OIDC/SSO when available | Identity choice must work without public internet if the deployment is air-gapped |
| Approvals | Human decision and manual fulfillment in the first release | Typed execution can be considered only after exact approval binding and rollback exist |
| UI | Opaque, responsive business workspace using local/system assets | Light theme is current; add a dark theme only after all core pages share one system |

## Milestone 01 · Security foundation — completed

Implemented and verified:

- Protected endpoints reject missing, invalid, expired and inactive-user tokens.
- High document clearance no longer grants administrator access.
- Demo identity switching and seed routes are absent unless explicitly enabled in demo mode.
- First-company bootstrap requires an enabled setup window, a setup token and an empty installation.
- JWT secrets have no usable built-in value; weak/demo secrets and wildcard CORS fail configuration validation.
- Role capabilities protect uploads, tasks, approvals and audit access.
- User relationships must belong to the same company; self-supervision and removal of the final administrator are blocked.
- Uploads use generated contained paths, a file-type allowlist, size bounds, explicit audience and duplicate hashes.
- Search results are rechecked against current SQL state and authorization.
- Self-approval, arbitrary decision values and task overexposure are blocked.
- The AI simulator is disabled by default and cannot silently replace a failed model.

The detailed evidence remains in `OracleX-Milestone-01-Security-Foundation.md`.

## Milestone 02 · Migrations and UI foundation — completed

Implemented and verified:

- Added an Alembic migration baseline for the current relational schema.
- Removed implicit runtime table creation.
- Docker and Windows development startup apply migrations before launching the API.
- Added upgrade → drift check → downgrade → reapply migration testing.
- Replaced the generic dark prototype shell with a restrained light business interface.
- Removed the external Google Fonts request and used local/system fonts.
- Added responsive sidebar navigation and a mobile drawer.
- Rebuilt sign-in with proper labels, password visibility and error semantics.
- Frontend visibility follows administrator flags and role capabilities rather than clearance.
- Removed fabricated people/department counts and inaccurate sovereignty/compliance statements.
- Replaced the old system screen with measured model availability.
- Removed unreachable prototype screens and every backdrop blur.
- Frontend lint, TypeScript and production build pass.
- Desktop and 390 × 844 authenticated layouts were visually checked.

Current verification baseline:

| Check | Result |
|---|---|
| Backend tests | 53 passed, 4 PostgreSQL-only tests skipped |
| Migration lifecycle | Passed on isolated SQLite |
| Frontend lint | 0 warnings, 0 errors |
| TypeScript and Vite build | Passed |
| Docker runtime | Not verified because Docker is unavailable on the current host |
| Live Ollama quality | Not evaluated |
| Air-gapped installation | Packaging/tooling implemented; clean disconnected-host verification pending |

## Milestone 03 · Offline deployment foundation — in progress

### Goal

Produce a reproducible installation that works on a clean disconnected company host and makes no unintended outbound request during normal operation.

### Current status

The source implementation is complete on the current development host:

- Python's Linux/amd64 transitive dependency set is exact and hash-locked; a 99-package wheelhouse was downloaded and verified against the lock.
- Direct frontend dependencies and all production container images are version-pinned. Base build images are also recorded by digest.
- Runtime Compose has no model/package download step, sets `pull_policy: never`, and places all services on an internal Docker network.
- The unconditional Ollama pull was replaced by an explicit GGUF importer that requires a checksum, licence and provenance record.
- The API reports separate liveness and detailed readiness. A missing configured model is reported as degraded and cannot become simulated live inference.
- The production frontend image contains only compiled static assets and nginx. Node.js and npm are absent from the runtime image.
- Complete install, start, stop, model import, backup, restore, update, rollback, diagnostics and outbound-denial commands are implemented.
- Dependency source/licence inventory, image provenance, release manifest and whole-bundle checksums are generated by the release process.

Acceptance remains open because Docker is not installed on the current host and no company target-host profile or approved redistributable model artifact has been supplied. The milestone cannot truthfully pass its clean disconnected-host exit gate until those inputs are available.

### Backend and model work

1. Pin Python dependencies to tested exact versions and produce a hash-verified wheelhouse.
2. Pin PostgreSQL, Ollama and base container images by version/digest. Remove floating `latest` references.
3. Replace the unconditional `ollama pull` startup service with an explicit offline model-import step.
4. Select the initial model only after checking target CPU/RAM/GPU, licence, storage and expected latency.
5. Package the approved model or approved local import artifact with a checksum and licence record.
6. Make the API start with a clear degraded state when the model is missing; document/search administration must remain usable where safe.
7. Separate liveness from readiness. Readiness should report database migration, storage, worker, index and configured-model status precisely.
8. Add outbound-denial defaults for containers and document the local ports required inside the deployment network.

### Frontend and packaging work

1. Ship the compiled frontend; production installation must not run `npm install`.
2. Remove unused starter assets and documentation that imply online dependencies.
3. Build an offline release bundle containing application images/builds, database image, model artifact, configuration template, checksums, licences and runbooks.
4. Provide install, start, stop, update, rollback, backup and diagnostic commands.
5. Validate exact origins and company LAN URL configuration without hardcoded localhost assumptions.

### Tests

- **Passed locally:** 38 backend tests, including readiness, missing-model and offline configuration checks; 4 PostgreSQL-only tests skipped.
- **Passed locally:** frontend `npm ci`, lint, TypeScript and production build; npm reported no known vulnerabilities.
- **Passed locally:** Python Linux/amd64 wheel download from the hash lock, release-script parsing, YAML parsing and dependency inventory generation.
- **Pending target host:** install on a clean disposable host with networking disabled.
- **Pending target host:** start, migrate, bootstrap, sign in, upload, search and ask using only packaged artifacts.
- **Pending target host:** capture browser, backend, container and DNS traffic during the core journeys.
- **Pending target host:** restart/persistence, deliberate migration failure, backup, update and rollback exercises.

### Exit gate

- Zero unintended outbound requests during agreed core journeys.
- Clean disconnected installation succeeds from the release bundle.
- Every artifact has a checksum and recorded licence/source.
- No container or package uses an unpinned production version.
- Operators can update and roll back without deleting company data.

## Milestone 04 · Versioned document ingestion — implemented in source, acceptance pending

### Current status

The local source implementation is complete. Uploads now commit a document, immutable version, ingestion job and outbox event together. A separate worker claims jobs with a lease, validates retained files, parses bounded inputs, writes stable version-aware chunks/vectors, verifies the index count and activates the new version only after success. Failed replacements leave the prior ready version active.

Search and assistant retrieval recheck both SQL authorization and the active version ID. Archive removes the active vectors; restore and the reconciliation command rebuild them from retained SQL chunks. The document UI now presents a professional register, real processing states, version history, safe failures, retry, archive/restore and administrator-only permanent deletion.

Local verification passed with **45 backend tests and 4 PostgreSQL-only skips**, clean frontend lint, a successful TypeScript/Vite build, migration drift/rollback coverage, static Compose/operator-script checks and a live 762 px browser review against a seeded local backend. Acceptance remains open for Docker, PostgreSQL concurrency, real worker/container restart, filesystem fault injection, approved malware scanning if required, and clean backup/restore on the target host.

### Data model

Add migrations for:

- `document_versions`: immutable version ID, document ID, sequence, original filename, media type, size, content hash, storage key, parser version, created by/at and lifecycle status.
- `ingestion_jobs`: version ID, job type, state, attempt count, lease/heartbeat, error code, safe error message and timestamps.
- `outbox_events`: transactionally records work to be processed after the upload transaction commits.
- Optional extraction records for page/section/sheet/row coverage when that data should not live in generic chunk metadata.

### Processing flow

1. Stream upload into a generated quarantine path while enforcing size and content-type rules.
2. Calculate the content hash and create the document/version/job/outbox records in one transaction.
3. Return a durable job identifier rather than blocking the upload request through parsing and indexing.
4. Worker claims the job using a lease, scans the file, parses it with bounded resources, creates source-located chunks and indexes version-aware vector IDs.
5. Mark the version ready only after SQL metadata and index writes are complete and verified.
6. Retry idempotently. A repeated job must not create duplicate versions, chunks or vectors.
7. Reconciliation compares ready SQL versions with storage and vector state and repairs or reports divergence.
8. Archive removes the version from current retrieval immediately; restore and supersession remain explicit operations.

### UI work

- Documents table with owner, audience, classification, version, status and updated date.
- Upload flow showing file limits, effective audience and upload/job progress.
- Document details with versions, extraction coverage and failure/retry actions.
- Separate archive, restore and permanent-deletion controls according to capability.
- Clear states for queued, scanning, parsing, indexing, ready, partially extracted, failed, superseded and archived.

### Tests

- **Passed locally:** duplicate content rejection, misleading signatures, invalid UTF-8, vector outage, replacement/supersession, archive/restore, index repair, expired leases, idempotent retry, transactional outbox records and historical-version authorization.
- **Passed locally:** empty/unsupported/contained upload behavior from the existing security suite; migration upgrade, metadata drift check, downgrade and reapply on SQLite.
- **Pending target host:** PostgreSQL worker concurrency and row-lock behavior, real worker/container termination, simultaneous archive/search, SQL/storage failure injection, disk-full and permission-denied cases.
- **Pending policy/input:** encrypted-file rejection and approved local malware scanning/content-disarm integration require representative fixtures and the company's chosen scanning engine.

### Exit gate

- No false-ready document state and no silent partial ingestion.
- Worker restart and retry do not duplicate data.
- Archived/revoked content is immediately absent from new retrieval.
- Operators can identify and recover every failed job.
- Original files and version metadata survive service restarts and a tested backup/restore.

The first four points have source-level evidence. The final recovery point, plus PostgreSQL concurrency and real worker restart, remains part of target-host acceptance and prevents Milestone 04 from being marked fully accepted.

## Milestone 05 · Evaluated retrieval and evidence — implemented in source, acceptance pending

### Current status

OracleX now retrieves only authorized, indexed chunks from the current immutable document version, combines lexical rank with the local vector rank, and applies a relative lexical relevance gate before evidence reaches the assistant. The response contract reports `evidence_status`, `generation_mode`, model identity when applicable, and exact document/version/chunk plus page, section or table location. The UI shows the cited excerpt and downloads the retained source only after a fresh permission and checksum check.

Unsupported image analysis is rejected explicitly. Questions without relevant authorized company evidence abstain. If local inference is unavailable, supported questions return a visibly labelled extractive answer instead of a simulated model response. Fabricated reasoning traces, answer confidence percentages, fixed vision citations, report-agent behavior and invented data-agent telemetry have been removed.

A frozen 20-case synthetic NovaWorks development set covers answerable, unsupported and permission-denied queries. Lexical and hybrid retrieval each achieved 100% recall@5, abstention and access-control accuracy on that small set; vector-only retrieval achieved 100% recall@5 and access-control accuracy but 0% abstention, which is why it is not trusted by itself. These figures validate the harness and current fixtures only. They do not satisfy the pilot gate for a representative company corpus, holdout questions, approved semantic embeddings or generated-claim citation fidelity.

### Evaluation before model selection

1. Build a company-approved corpus and a labelled set of answerable, unanswerable, conflicting, superseded and adversarial questions.
2. Freeze a development set and a separate holdout set.
3. Measure lexical search, the current deterministic vector baseline and locally deployable semantic embedding candidates.
4. Keep the implemented hybrid lexical gate unless an approved semantic candidate improves the representative holdout without reducing abstention or ACL safety.
5. Document versions now record embedding implementation and dimensions; validate full rebuild on the target restore rehearsal.

### Evidence contract

- Every citation identifies the document, immutable version, page/section/sheet/row and excerpt.
- The API returns evidence status plus whether the result used a local model, extractive fallback, explicitly enabled demo simulation or no generation.
- The UI shows the exact location label and excerpt and permission-checks the retained-source download. Exact in-document highlighting remains a pilot candidate where the file format supports stable anchors.
- Prompt assembly rechecks authorization against current SQL metadata.
- Conflicting-current-source detection remains to be implemented and evaluated on the approved company corpus.
- Superseded versions may be viewed by authorized users but are never presented as current evidence.
- Document text is treated as untrusted input; prompt-injection instructions inside documents do not change system policy or trigger actions.

### Proposed pilot gates

These are targets to validate against the real corpus, not claims about current performance:

- Relevant-source recall@5 ≥ 90% on answerable holdout questions.
- At least 95% of sampled material factual claims supported by the cited passage.
- Correct abstention ≥ 95% on clearly unsupported company questions.
- Zero citations to inaccessible or nonexistent versions in the authorization suite.
- Deleted, archived and revoked versions absent from new queries immediately.

## Milestone 06 · Persistent assistant and accountable requests — implemented in source

Implemented and locally verified:

- Added conversations, ordered messages, agent runs and immutable citation snapshots with company/owner scope, classification, archive state and a retention-policy date field.
- Persisted completed and failed runs with model, prompt version, generation/retrieval mode and exact source-version identifiers.
- Added bounded follow-up context from prior user questions and reauthorization/redaction of saved cited answers after source access changes.
- Added real archive, retry and copy controls while retaining the removal of reasoning traces and artificial confidence.
- Replaced product use of generic approvals with controlled-change, access and purchase requests using validated typed fields.
- Added immutable versions and draft, submitted, assigned, approved, rejected, cancelled and completed transitions.
- Bound every decision to the exact submitted version; required reviewer reasons; blocked self-review and assigned-reviewer bypass.
- Added optimistic locking, duplicate-decision/fulfillment prevention, separate completion records, recipient notifications and readable timelines.
- Rebuilt Ask OracleX and Requests with opaque professional layouts and verified the main employee journey live.

Local exit evidence is complete. Target acceptance remains open for PostgreSQL simultaneous-decision execution, Docker/process restart persistence, company retention enforcement and formal multi-viewport/accessibility review.

## Milestone 07 · Complete professional UI

The shell, principal page designs and nine focused source batches are implemented, but the milestone exit gate is still open.

### Implemented in the current batch

- Canonical URLs for the principal pages and document versions, conversations and requests; safe sign-in return, authorization-aware navigation and browser back/forward behavior.
- Shared page headers, notices, empty/error states, status labels and an accessible dialog foundation.
- Rebuilt Overview, My work, People, Teams, Roles and Audit pages using opaque business layouts. System status now reports measured model state and distinguishes an unknown health result from an unavailable runtime.
- Retryable load failures on the principal registers so a service error cannot appear as a successful empty list or endless loading state.
- Selected live browser checks at 390, 768 and 1440 CSS pixels, including employee/admin routing, request and conversation deep links, document-version selection and no page-width overflow on the checked views.
- A repair migration for databases stamped with the earlier Milestone 06 revision before its two conversation columns were included.
- Company/user-scoped, short-lived in-memory caching for selected server reads; page/logout cancellation and invalidation after writes. In-flight GETs restart when a write invalidates them. Four focused state tests cover scope separation and invalidation races.
- Generated OpenAPI schema types and a drift check. Shared response type names now alias generated schemas; optional flags/permissions are handled explicitly. Task writes use generated input schemas, and company setup expects its actual token/user response.
- Responsive, labeled first-company setup form; removed unused prototype pages and page/component inline styles.
- Typed/authenticated model health, audit integrity, team-delete and feedback responses. Audit records use stable cursor pagination; replaced filter/page requests are cancelled. The current backend suite passes 82 tests, with 5 PostgreSQL-only tests skipped.
- Frontend lint, production build, eighteen state/field/error/capability/draft/notification tests and the 60-schema OpenAPI drift check pass. The current full backend result is 82 passed and 5 PostgreSQL-only tests skipped.
- The fourth batch adds a common modal/mobile-drawer focus boundary, inert backgrounds, Escape/return focus, a skip link, stronger muted-text contrast and labeled controls. Documents and Requests retain page state across record URLs; document previews no longer cancel themselves. Active-view re-selection no longer sticks on loading.
- Request payloads use guarded scalar readers and null for cleared typed values. Six frontend state/field tests and two focused backend request tests pass. Live checks covered a synthetic employee draft/save/submit and separate reviewer approval of exact version 2, plus administrator modal controls. Add person no longer preselects a privileged role.
- The fifth batch handles history/archive/copy failures, typed validation messages and failed assignee lookup. Live API interruption/retry checks recovered task, directory and history data. A saved citation downloaded a checksum-matching retained file. Mobile saved-history controls are present, and the long-title Archive action is visible at 390/768/1440 pixels.

- The sixth batch fixes live document-detail polling, in-dialog feedback, active-version labeling and focus recovery after disabled/removed actions. It also resolves a discovered API/worker embedded-index problem by using a single private Chroma server. A real separate worker processed a third synthetic version while the running API immediately retrieved it. Index outages are visible 503 errors; restart/retry recovery passed locally. Revised Compose/startup and container recovery still need target-host acceptance.

- The seventh batch adds unsaved-version submission protection, owner cancellation, assignment-aware review controls, conflict/reload states and safe payload validation. A synthetic employee/reviewer purchase flow passed through saved version 3 to separate completion. A second-view conflict, API read interruption/retry, unrelated-user denial and selected request reflow passed locally. At that point notification UI, broader navigation protection and other request-type browser journeys remained open.

- The eighth batch implements the recipient inbox with unread/read state, safe local links, bounded cursor pagination and outage recovery. Scoped memory-only pending request text survives workspace/history navigation; stale recovered drafts block writes. Sign-out confirmation was checked live. Reload/close warnings and failed-session/crash recovery remain unverified or unsupported; do not claim durable unsaved drafts.

- The ninth batch adds minimal eligible-reviewer lookup, new/draft reviewer selection, version-bound save/submit, assigned-reviewer/admin reassignment and recipient notifications. Local browser checks passed for access rejection, controlled-change approval/separate completion, submitted/assigned cancellation and lookup failure/retry. Submission rechecks reviewer eligibility. The full suite was refreshed on 10 November: 82 passed and five PostgreSQL-only skips.

### Remaining before Milestone 07 exit

- Validate the implemented reviewer-selection and access/change/rejection/cancellation journeys on target PostgreSQL with independent sessions and representative staff. Validate native reload/close warnings in supported browsers and agree whether durable draft recovery is required. Administrator upload/worker/retry/replacement/search passed locally on 20 October. Shared response aliases and dynamic request-field guards are implemented.
- Add shared permission/feedback patterns only where repeated workflows need them. Field and Audit pagination are implemented; avoid a generic table or toast without a concrete use.
- Complete all three pilot journeys, screen-reader speech/navigation, all-page contrast, live reduced-motion and true 200% zoom/reflow. Selected keyboard paths passed; browser zoom was unavailable through the in-app shortcut, so that manual gate stays open.
- Review all pages and states at 390, 768 and 1440 pixels, including long, empty, partial, denied and server-error fixtures.
- Observe representative employees, reviewers and administrators completing the workflows, and resolve or explicitly accept findings.

### Shared application foundation

- Implemented: stable URLs, safe sign-in return, selected scoped cache with cancellation and in-flight refresh, generated OpenAPI schema view, PageHeader, Dialog, Field, StatusLabel, EmptyState, ErrorState and Audit pagination.
- Remaining: workflow-specific permission/feedback patterns where useful; complete pilot journeys, screen-reader, contrast, zoom and live reduced-motion checks. A generic DataTable or toast is not an exit requirement by itself.
- Page/component inline styles have been removed from the current frontend source.

### Page order

1. Documents list, upload and version detail — completed in Milestone 04.
2. Ask OracleX conversation plus evidence panel — completed in Milestone 06.
3. Requests list, detail, decision and timeline — completed in Milestone 06.
4. My work — implemented in the current source batch.
5. People, teams and read-only roles — implemented in source; effective-access review remains.
6. Audit and measured model status — implemented in source; operational status requires target-host integration.
7. Overview from permission-scoped operational data — implemented in source; full partial/degraded-state review remains.

### Design requirements

- Opaque canvas/surfaces, restrained blue accent and practical tables.
- No blur, glass, gradients, glows, decorative AI imagery or fabricated activity.
- One primary action per section and plain business wording.
- Loading, empty, no-results, denied, failed, partial and success states must be distinct.
- Responsive behavior at 390, 768 and 1440px plus 200% zoom.
- Keyboard navigation, visible focus, programmatic labels, screen-reader names and non-colour status cues.
- WCAG 2.2 AA contrast and interaction checks.

### Exit gate

- Employee, reviewer and administrator can complete the three pilot journeys keyboard-only.
- Exact source evidence and request status are understandable without training.
- No inaccessible controls or unintended page overflow at required viewports.
- Network/service failure never appears as a successful empty workspace.
- Representative staff complete observed usability tasks; findings are resolved or accepted explicitly.

## Milestone 08 · Operations and controlled pilot

### Security and administration

- Effective-capability viewer and controlled role editor.
- Invitation, password reset and session revocation, or approved company OIDC/SSO integration.
- Login rate limiting, security-event logging and configurable session policy.
- Complete audit-event coverage with redaction and transactional outbox semantics.
- Append-only database permissions and independently protected checkpoints when stronger integrity assurance is required.
- Threat model and dependency/licence review.

### Operations

- PostgreSQL integration, migration and concurrency tests.
- Non-root services, internal networking, HTTPS ingress and exact CORS origins.
- Readiness/status for database, worker, storage, model and index.
- Metrics for job age, failed ingestion, inference latency, disk capacity and authentication anomalies without exposing confidential content.
- Backup and full restore of database, original/versioned documents and configuration.
- Index rebuild, signing-key rotation, model rollback and failed-release rollback drills.
- Capacity tests on the actual company CPU/RAM/GPU and expected concurrent load.

### Pilot sequence

1. Name an IT operator and departmental product owner.
2. Use approved noncritical documents in one department.
3. Begin with document retrieval and manual requests; no automatic business execution.
4. Review sampled answers, access denials, ingestion failures and user confusion weekly.
5. Expand only after the acceptance checklist is signed by engineering, IT and the product owner.

### Exit gate

- No unresolved critical/high security exposure.
- All required tests run; no required PostgreSQL/offline/restore checks remain skipped.
- Restore meets the agreed recovery point and recovery time.
- Retrieval and usability gates pass on the actual pilot corpus and hardware.
- Company owner accepts operating limits and incident procedures.

## Target architecture

```text
Employee browser
    │ HTTPS, same origin; bundled local assets
Reverse proxy ─── React production build
    │ /api
FastAPI modular application
    ├── Identity/session and authorization policy
    ├── Documents/version metadata ───────────── PostgreSQL
    ├── Conversations/runs/requests ──────────── PostgreSQL
    ├── Audit/outbox/job queue ───────────────── PostgreSQL
    ├── Versioned document storage ───────────── company-controlled protected disk/storage
    ├── Retrieval index ──────────────────────── Chroma, rebuildable
    └── Local inference adapter ──────────────── Ollama, approved preloaded model

Durable ingestion worker
    ├── Quarantine and structural validation; approved malware scan when supplied
    ├── Bounded parsing with source locations
    └── Version-aware indexing and reconciliation

Offline release bundle
    ├── Pinned application/service images or executables
    ├── Approved model and dependency artifacts
    ├── Checksums, licences and configuration template
    └── Install/update/rollback/backup runbooks
```

Use the relational database as the initial durable job queue if it meets pilot throughput. Add a dedicated broker only when measured retry scheduling or volume justifies another service. Do not introduce Kubernetes, microservices or a new frontend framework for appearance alone.

## Data-model implementation order

| Order | Status | Add/change | Core invariant |
|---|---|---|---|
| 1 | Completed | Role capabilities, company ownership, explicit document audience | Backend authorizes every protected operation |
| 2 | Completed | Alembic history and protected bootstrap configuration | Startup never invents or replaces company data |
| 3 | Implemented in source | DocumentVersion, IngestionJob, OutboxEvent | Only ready authorized immutable versions enter retrieval |
| 4 | Implemented in source; acceptance pending | Extraction/source-location and embedding identity metadata | Citation locations map to exact stored versions; target-format highlighting remains open |
| 5 | Implemented in source | Conversation, Message, AgentRun, Citation | Owned/classified records with prompt/model metadata and exact source versions |
| 6 | Implemented in source | Typed Request, RequestVersion, Decision, Fulfillment | Decision binds exact payload; fulfillment is separate and once-only |
| 7 | Planned | Expanded AuditEvent and protected checkpoint | Business mutation and event are atomic and scoped |
| 8 | Partially implemented | Recipient-scoped request notifications and conversation retention field | Retention enforcement and governed evaluation records remain |

Migration procedure for populated environments: back up → add compatible structures → migrate/backfill → validate → deploy consuming code → verify → remove obsolete fields in a later release. Never point the new application at an unknown populated demonstration database and assume the initial migration is safe.

## Updated implementation work packages

| Work package | Status | Scope | Required evidence |
|---|---|---|---|
| WP01 | Completed | Test isolation, fail-closed authentication, safe bootstrap and demo separation | Authentication/config regression suite |
| WP02 | Completed | Authorization, user relationships, task/request/audit controls and upload storage | Permission and upload regression suite |
| WP03 | Completed | Alembic baseline and startup integration | Upgrade/check/downgrade/reapply test |
| WP04 | Completed | Professional shell, sign-in, responsive navigation and prototype cleanup | Lint/build plus desktop/mobile visual QA |
| WP05 | Implemented in source; acceptance pending | Pinned offline artifacts, model import and network-denial harness | Clean disconnected installation report |
| WP06 | Implemented in source; acceptance pending | Document version/job/outbox migrations and upload contract | Migration/API/idempotency tests |
| WP07 | Implemented in source; acceptance pending | Worker, validation, parsing, index reconciliation and recovery UI | Interruption/retry/rebuild tests |
| WP08 | Implemented in source; acceptance pending | Retrieval evaluation harness, deterministic baseline, hybrid relevance gate and source contract | Synthetic frozen evaluation and ACL tests pass; representative company holdout remains open |
| WP09 | Completed in source | Persistent conversations and evidence UI | Ownership/history/follow-up/failure/access-revocation tests passed |
| WP10 | Completed in source; PostgreSQL proof pending | Typed requests, decisions, fulfillment and notifications | Local state/version tests passed; simultaneous PostgreSQL race test is present and skipped without the service |
| WP11 | Next | Remaining professional page rebuilds, shared primitives and stable routing | Role journeys, responsive and accessibility checks |
| WP12 | Planned | Audit, PostgreSQL, backup/restore, security and pilot bundle | Restore, offline, security and operations sign-off |

Keep each work package reviewable. Split unrelated risks rather than creating a large “production-ready” change. Hiding an unsafe frontend button never counts as an authorization fix.

## Quality gates

| Area | Gate | How it is verified |
|---|---|---|
| Authentication | Every protected endpoint rejects missing/invalid/inactive sessions | Automated endpoint inventory and negative requests |
| Authorization | Zero unauthorized record, content or mutation in the defined scope suite | Cross-company, cross-department, ownership and derived-data tests |
| Migration | Upgrade is reproducible; deployed revision matches code | Fresh and populated-fixture migration checks plus backup/rollback plan |
| Offline | Zero unintended outbound requests during core journeys | Disconnected install and captured network-denial test |
| Ingestion | No false-ready state, silent truncation or unrecoverable partial job | Corrupt/large/scanned files, worker death, disk/index/database failure tests |
| Versioning | Exact version is preserved, cited and superseded explicitly | Replacement/archive/restore tests |
| Retrieval | Proposed relevant-source recall@5 ≥ 90% | Human-labelled frozen holdout set |
| Grounding | Proposed ≥ 95% sampled material claims supported by cited passages | Blind source-version review |
| Abstention | Proposed ≥ 95% on clearly unsupported company questions | Separate no-answer/adversarial set |
| Removal | Archived/revoked content excluded from new queries immediately | Retrieval while cleanup/reconciliation fails |
| Requests | No self-review, duplicate decision/fulfillment or stale-payload approval | Concurrent integration tests |
| UI accessibility | Core journeys keyboard usable at 200% zoom | Manual and automated WCAG checks |
| UI layouts | No hidden actions or unintended overflow at 390/768/1440px | Visual regression with long/empty/error fixtures |
| Recovery | Pilot RPO/RTO agreed and demonstrated | Full restore rehearsal, not backup-job status alone |
| Release | No open P0; required P1 work complete; no required test skipped | Engineering, IT and product-owner checklist |

Numerical retrieval targets apply only to the defined evaluated tasks. They do not establish correctness for financial authorization, engineering measurements or unrestricted automation.

## Immediate next build backlog

1. Finish the complete employee, reviewer and administrator pilot journeys, then check screen-reader speech/navigation, all-page contrast, live reduced motion and true 200% zoom. Selected modal/navigation and synthetic request keyboard paths passed.
2. Verify every page at 390, 768 and 1440 px with empty, loading, error, partial and long-content fixtures. Audit and setup have selected live viewport checks, not a complete state matrix.
3. Complete independent-session, revocation and race acceptance for the implemented reviewer and request journeys; validate pending-text reload/session recovery policy before target-host acceptance. Recipient inbox and workspace/history draft recovery passed selected local checks; selected employee/reviewer purchase completion and draft cancellation now pass locally; the local administrator upload/worker/retry/replacement/search path passed on 20 October; shared response aliases, error messages and request-field guards are implemented. Add permission/feedback UI only where workflows need it.
4. Observe representative staff using the three pilot journeys and resolve or explicitly accept their findings.
5. On a target-equivalent host, run the five PostgreSQL tests, restart persistence, Docker/offline and recovery checks already listed in the pre-launch checklist.
6. Standardize UTC/offset timestamp handling across the remaining pages and API contract; notification dates now handle legacy UTC correctly. Verify time-zone and daylight-saving behavior.
7. Obtain the approved non-confidential company corpus, holdout questions, model licence and target hardware record needed to close Milestones 03–06 acceptance.

## Deferred until after the pilot

- Autonomous learning or self-modifying policies.
- General-purpose tool execution.
- Drag-and-drop workflow builders.
- Broad vision or multimodal claims.
- Automatic financial, HR, legal or production-system actions.
- Public multi-tenant SaaS, billing and self-service company registration.
- External connectors without end-to-end ACL, deletion and offline behavior.

High-value post-pilot candidates are saved searches, document review/acknowledgment dates, source-scoped templates, evidence-backed report drafts, validated spreadsheet analysis and carefully scoped read-only connectors.
