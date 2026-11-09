# OracleX pre-launch, unfinished-work and validation checklist

Living control document · Updated 10 November 2026

This is the single list of work that could not be tested on the current development computer, work that remains incomplete across the complete OracleX rebuild, and the actions required before the system can be treated as installed, operational and suitable for a controlled company pilot.

Passing a source test on this computer does not prove the corresponding Docker, PostgreSQL, model, network, hardware or operational behavior on the company host. Do not load confidential company data until every **pilot-blocking** item below is complete and its evidence is retained.

## Current milestone position

| Milestone | Engineering status | Acceptance status |
|---|---|---|
| 01 · Security foundation | Implemented | Source tests passed; target security review remains |
| 02 · Migrations and UI foundation | Implemented | SQLite lifecycle and UI checks passed; PostgreSQL/target-host checks remain |
| 03 · Offline deployment foundation | Implemented in source | **Open:** Docker, approved model and disconnected-host proof remain |
| 04 · Versioned document ingestion | Implemented in source | **Open:** PostgreSQL/Docker concurrency, worker restart, filesystem faults and recovery proof remain |
| 05 · Evaluated retrieval and evidence | Implemented in source | **Open:** approved company corpus/holdout, semantic embedding/model comparison and generated-claim fidelity review remain |
| 06 · Persistent assistant and requests | Implemented in source | **Open:** PostgreSQL simultaneous-decision, Docker/process restart and company retention-policy enforcement remain |
| 07 · Complete professional UI | In progress | Core pages/routes, scoped cache with in-flight refresh, expanded OpenAPI typing and live setup/Audit checks completed; accessibility/state-matrix and staff acceptance remain |
| 08 · Operations and controlled pilot | Planned | Not started |

## 20 October update: ingestion and shared-index boundary

- [x] Run synthetic administrator upload, queued processing, replacement failure, Retry and active-content preview through the browser and real separate worker processes, with inline ingestion disabled.
- [x] Verify a separate worker's new version is searchable through the already-running API using one local Chroma server; observe explicit search failure and recovery after a Chroma restart.
- [x] Keep empty-upload validation inside the dialog; observe focus recovery after submission and Escape returning to the opener.
- [x] Add production/server configuration and outage regressions; full backend suite: 67 passed, 5 PostgreSQL-only skipped, 351 warnings. Frontend: 8 tests, lint/build and OpenAPI drift passed.
- [ ] Run the revised Compose Chroma service on target Docker: CLI startup under its read-only filesystem, health dependency ordering, sole index-volume ownership, private-port isolation and container restart recovery. Only YAML/topology and PowerShell syntax were verified here.
- [ ] Back up an existing pilot stack, stop embedded clients, switch the retained index volume to the sole server owner, reconcile and prove replacement/search plus backup/restore on target PostgreSQL/Docker.
- [ ] Run `start_oraclex.ps1` end to end with the intended native virtual environment and configuration. Its syntax passed; this computer's live checks used explicit service commands.
- [ ] Accept document-search relevance on the approved corpus. Raw vector neighbors can still include weak/unrelated results; the deterministic embedding is not an approved semantic model.

## Seventh-batch update: requests and remaining UI work

- [x] Browser: employee draft/save/submit, reviewer claim/decision, separate QA completion and requester read-back of version 3, with zero cost retained. These were synthetic records and sequential role sign-ins.
- [x] Browser: real two-view stale-edit conflict, explicit reload, draft cancellation with timeline reasons, unrelated employee denied a private request, and API read interruption/retry recovery.
- [x] Reject invalid typed fields with safe 422 responses; reject whitespace-only basics/reasons; retain the saved version on invalid updates; deny a decision by another assigned reviewer in focused backend tests.
- [x] Gate New request/upload/review controls by actual capability and record ownership/assignment. Observe employee upload hidden, request/denial focus and selected 390/768/1440 request layouts.
- [x] Add a recipient-scoped inbox/read/local-request-link UI, unread filtering, stable pagination and retry. Selected recipient, read persistence and API outage/recovery journeys passed in the eighth batch.
- [x] Implement new/draft reviewer selection and assigned-reviewer/admin reassignment, minimal company-scoped choices, exact-version preservation, timeline and recipient notifications. Selected local browser journeys passed.
- [x] Retain pending request fields/notes across workspace/history navigation using account/company-scoped memory; restore stale edits with writes blocked. Verify confirmed sign-out clears text and cancellation/Escape keeps it.
- [ ] Verify native refresh/tab-close warnings in the supported real browsers. The automated browser reloaded without exposing the warning; this is not a passed gate.
- [ ] Agree and document the required recovery policy for accepted reload, crashes, expired sessions and process loss. The current memory buffer is not durable; saving a company draft is the available persistent path.
- [ ] Verify pending-note recovery on reviewer-specific actions, rapid navigation while a write is in flight, account/session expiry and permission revocation. Unit tests cover late-success buffer deletion, but not the complete browser race matrix.
- [ ] Standardize the remaining pages/API timestamps as explicit UTC or offsets and verify local-time/daylight-saving display. Notification timestamps now handle suffix-free UTC correctly.
- [x] Run selected local Access request/reassignment/rejection and Controlled change/version-2 approval/separate-completion journeys; observe requester cancellation while Submitted and Assigned. All used synthetic local records.
- [ ] Repeat these journeys with revocation while open, remaining role/state combinations and independent sessions on target PostgreSQL.
- [ ] Complete all-page screen-reader, contrast, true zoom, reduced-motion and state/viewport checks; current request reflow checks cover selected completed/cancelled states only.

## Eighth-batch evidence, 20 October

- Full backend: **74 passed, 5 PostgreSQL-only skipped, 377 warnings**. Frontend: **18 tests passed**, lint/build clean; 59-schema OpenAPI drift check passed.
- Inbox: 25-to-30 pagination, page-tail read/removal without skipped older records, read persistence, safe local links despite an external-link fixture, sequential recipient isolation, API failure/retry and empty unread state observed.
- Drafts: new text/zero restoration after navigation and Back; saved-record field/note restoration; newer server version detected while old text remained visible; Keep working, Escape/focus return, explicit sign-out discard and account cleanup observed.
- Inbox/pending header had no page-width overflow in the selected 390/768/1440 states. This does not close all-page accessibility or state coverage.
- Runtime fixture: disposable SQLite `work/m06-ui`; no real company data, purchase, access grant or external action. Native unload prompts, durable recovery and PostgreSQL concurrency remain open.

## Ninth-batch and publication verification

- Source/browser batch: 20 October 2026. Refreshed local checks: 10 November 2026.
- Full backend: **82 passed, 5 PostgreSQL-only skipped, 497 warnings**. Frontend: **18 tests passed**, lint/build clean, 60-schema contract drift check passed.
- Reviewer eligibility, reassignment authority and immutable submitted versions are enforced by the backend. Local reviewer lookup outage/retry and selected responsive form checks passed.
- Publishing source to GitHub does not close Docker, PostgreSQL, offline, model/corpus, durable recovery, accessibility or staff acceptance gates.

## What could not be tested on this computer

### Docker and disconnected deployment — pilot-blocking

- [ ] Install Docker Engine and Docker Compose v2 on a controlled Linux/amd64 test host.
- [ ] Build the complete offline release with `deployment/scripts/build-release.ps1` on a connected Docker build host.
- [ ] Confirm the backend and frontend images build with Docker networking disabled.
- [ ] Confirm every pinned base/runtime image is present in the exported image archive.
- [ ] Transfer the bundle through the company's approved removable-media or internal-release process.
- [ ] Run `verify-release.ps1` on the disconnected target and retain the output.
- [ ] Load all images and start OracleX while DNS and outbound internet are denied.
- [ ] Confirm `pull_policy: never` produces an actionable failure when an image is deliberately omitted.
- [ ] Run `test-network-isolation.ps1` and retain the result.
- [ ] Capture browser, container, DNS and host traffic during sign-in, upload, search and ask; prove zero unintended outbound requests.
- [ ] Confirm only the approved frontend/HTTPS ingress is reachable from the company LAN.
- [ ] Confirm PostgreSQL, Chroma, Ollama and the backend have no published host ports.

The current computer has no Docker executable, so Compose configuration was parsed and statically tested but no container was started here.

### PostgreSQL — pilot-blocking

- [ ] Provision an explicitly disposable PostgreSQL test database matching the pinned production major version.
- [ ] Set `POSTGRES_TEST_URL` only to that disposable database and run the five skipped PostgreSQL tests, including the simultaneous request-decision race.
- [ ] Apply every Alembic migration to a fresh PostgreSQL database.
- [ ] Exercise the supported upgrade path on a populated copy of representative non-production data.
- [ ] Verify indexes, foreign keys, enum/value constraints and transaction behavior under PostgreSQL.
- [ ] Deliberately fail a disposable migration and confirm startup stops with an actionable message without corrupting data.
- [ ] Validate database connection limits, timeouts, deadlock handling and concurrent writes at expected company load.
- [ ] Prove backup and restore with PostgreSQL custom-format dumps.

The SQLite migration lifecycle passed. It is not a substitute for PostgreSQL acceptance.

### Local model and Ollama — pilot-blocking

- [ ] Record the target host OS/architecture, CPU model and cores, available RAM, GPU/VRAM if any, free disk, simultaneous users and acceptable latency.
- [ ] Select one model and quantisation using those constraints and representative company questions.
- [ ] Obtain security/legal approval for the exact model licence and local redistribution terms.
- [ ] Add `model.gguf`, `model.sha256`, `MODEL-LICENSE.txt`, `model-source.json` and `Modelfile` to the controlled release input.
- [ ] Import the model using `import-model.ps1` with internet access disabled.
- [ ] Confirm the checksum is rejected after deliberately changing a copied artifact.
- [ ] Confirm the configured exact model tag is active and an arbitrary installed model is never substituted.
- [ ] Measure first-token latency, complete-answer latency, memory/VRAM usage, concurrency and sustained thermal behavior.
- [ ] Remove the model and confirm explicit degraded/unavailable behavior with no simulator response.
- [ ] Evaluate answer quality and evidence fidelity in Milestone 05 before relying on assistant output.

No live Ollama inference or model-quality claim has been tested on the current computer.

### Storage, restart and recovery — pilot-blocking

- [ ] Confirm database records, originals, approved model and index survive a full service and host restart.
- [ ] Test upload and index volumes with the exact production ownership and filesystem permissions.
- [ ] Test disk-full, read-only, permission-denied and interrupted-write behavior.
- [ ] Run `backup.ps1`, store the backup outside the host and verify its checksums.
- [ ] Restore that backup onto a clean disposable installation and compare records and original-file hashes.
- [ ] Test `update.ps1` with non-production data.
- [ ] Test `rollback.ps1` using the matching pre-update backup.
- [ ] Confirm none of the operator scripts delete named volumes implicitly.
- [ ] Define backup frequency, retention, encryption, off-host location, restore-time objective and recovery-point objective.

### Network, TLS and identity — pilot-blocking

- [ ] Assign the production DNS name and exact HTTPS origin.
- [ ] Configure an approved reverse proxy/ingress and certificate lifecycle; the current release does not terminate company TLS itself.
- [ ] Set exact `ALLOWED_ORIGINS`; never use a wildcard.
- [ ] Decide whether local managed credentials are acceptable for the pilot or company OIDC/SSO is required first.
- [ ] If SSO is required, implement and test it without assuming public internet access.
- [ ] Configure firewall rules, time synchronization, host hardening and restricted administrator access.
- [ ] Store `SECRET_KEY`, database password and bootstrap token in the approved secret-management process.
- [ ] Rotate/remove the bootstrap token and set `BOOTSTRAP_ENABLED=false` immediately after first setup.

## Incomplete product and engineering work

### Milestone 04 · versioned document ingestion — source implemented, target acceptance pilot-blocking

- [x] Immutable document-version records and version sequencing.
- [x] Durable ingestion jobs and transactional outbox records.
- [x] Generated quarantine storage, signature/checksum validation, parse, index and verification states.
- [x] Lease/heartbeat, bounded retry and expired-worker recovery logic.
- [x] Stable vector identifiers, duplicate-content protection and idempotent chunk replacement.
- [x] Dry-run/repair reconciliation between SQL, retained originals and vector state.
- [x] Explicit supersede, archive, restore and administrator-only permanent deletion.
- [x] Operator-visible processing/failure/retry UI, immutable version history and extraction coverage metadata.
- [x] Active-version authorization rechecks across document, chunk, direct search and assistant retrieval paths.
- [ ] Integrate and verify a company-approved local malware scanner/content-disarm stage if company policy requires it; the current `SCANNING` stage performs structural, signature and checksum validation only.
- [ ] Prove PostgreSQL concurrent job claiming, real worker/container restart and retry on the target stack.
- [ ] Prove disk-full, read-only and permission-denied upload/index behavior on production-like volumes.
- [ ] Prove clean-host backup/restore of SQL records, retained originals and rebuilt active indexes.

### Milestone 05 · evaluated retrieval and evidence — pilot-blocking

- [x] Add and freeze a 20-case synthetic permission-labelled development corpus covering answerable, unsupported and access-denied queries.
- [ ] Replace/extend the fixture corpus with approved representative company documents, conflicting/superseded/adversarial questions and a separate holdout set.
- [x] Compare lexical, deterministic-vector and hybrid retrieval on the development corpus; retain the lexical relevance gate because vector-only retrieval failed abstention.
- [ ] Compare the deterministic baseline with legally approved local semantic embedding and language-model options on representative target hardware.
- [x] Define and measure recall@5, abstention and access-control leakage in a machine-readable evaluation report.
- [ ] Sample generated factual claims against cited passages and meet the agreed citation-fidelity gate on the company holdout.
- [x] Return exact document, immutable version, chunk, page/section/sheet/row and excerpt locations.
- [x] Add permission-checked retained-source download, checksum validation and visible evidence panels.
- [ ] Add exact in-document highlighting for formats where stable anchors are available, if the pilot requires it.
- [x] Remove uncalibrated answer confidence, hidden reasoning traces, fixed vision citations, unsupported report behavior and invented data-agent telemetry.
- [x] Label supported, insufficient-evidence, access-denied and unsupported-input results; label local-model, extractive, demo-simulation and no-generation modes.
- [x] Ensure archived/superseded content disappears from new retrieval immediately at the version filter and vector layer.

### Milestone 06 · persistent assistant and accountable requests — source implemented, target acceptance pilot-blocking

- [x] Persist owned/classified conversations, ordered messages, prompt/model/run metadata, exact citations, source versions and safe failures.
- [x] Recheck current source access before returning saved cited answers; redact content/citations after access revocation.
- [x] Add bounded contextual follow-ups based on prior user questions without reusing cached assistant content.
- [x] Add controlled-change, access and purchase requests with validated fields, immutable versions and preview-before-submit.
- [x] Separate reviewer decision from once-only fulfillment/completion.
- [x] Add reviewer reason, assigned reviewer, timestamps, recipient notifications and optimistic-concurrency handling.
- [x] Test repeated submission, stale versions/actions, self-review, duplicate decision/fulfillment and notification scope on the isolated development database.
- [ ] Run the new two-reviewer simultaneous-decision race on disposable PostgreSQL; it is included in the suite and is one of five tests skipped on this device.
- [ ] Prove conversation/request survival across API/container and host restart on the target stack.
- [ ] Approve the retention duration, legal-hold/deletion behavior and scheduled enforcement for `retention_until`.

### Milestone 07 · complete professional UI — pilot-blocking

- [x] Complete the professional Documents register and document detail/version-history workflow.
- [x] Complete the Requests and Ask OracleX designs.
- [x] Complete People, Teams, Audit, My work and Overview source designs.
- [x] Add canonical routes, safe sign-in return and deep links for document versions, conversations and requests.
- [x] Distinguish initial load failures from successful empty registers on the core pages.
- [x] Add company/user-scoped, short-lived caching for selected reads, page/logout cancellation and mutation invalidation. In-flight GETs restart after a write; four focused state tests passed.
- [x] Replace shared frontend response interfaces with generated OpenAPI aliases and pass the drift check. The current contract has 60 schemas, including typed bootstrap status; company setup correctly expects token/user.
- [x] Guard dynamic request fields, retain zero cost and other payload data, and send null when clearing numeric/date/select fields. Six frontend state/field tests passed; a synthetic purchase draft/save/submit/reviewer decision passed live.
- [ ] Complete shared permission/feedback patterns where a repeated workflow needs them. Field and Audit pagination are implemented; page/component inline styles have been removed. A generic table or toast is not a mandatory pattern by itself.
- [x] Add document upload/job progress, recoverable error states and retry/archive/restore actions.
- [ ] Replace remaining prototype-like or unsupported agent language.
- [ ] Run keyboard-only, screen-reader, focus-order, contrast, zoom/reflow and reduced-motion checks against WCAG 2.2 AA.
- [x] Check selected employee/reviewer/admin keyboard paths: modal and mobile-drawer focus loops, inert backgrounds, Escape/return focus, skip link, document preview/back/forward and synthetic exact-version request approval.
- [ ] Complete true 200% browser zoom on a supported browser. The in-app browser zoom shortcut did not change the stable viewport/pixel ratio; no true-zoom pass was established.
- [ ] Complete screen-reader speech/navigation and all-page text/non-text contrast. The corrected 64-element People text spot check passed; it does not close this gate.
- [ ] Visually verify every page at phone, tablet, laptop and wide desktop widths. Selected pages were checked at 390, 768 and 1440 CSS pixels; the complete matrix is still open.
- [ ] Test empty, loading, partial, offline/degraded, validation and server-error states.
- [x] Run selected real API-interruption checks: history, Documents, tasks and assignee failures; task/directory/history retry recovery; failed archive preserving the visible saved conversation; document counts marked unavailable.
- [x] Open saved conversations on mobile and keep the Archive action visible for a long title at 390/768/1440 CSS pixels. The complete state/viewport matrix remains open.
- [x] Download a retained source from a saved citation and verify its SHA-256 against a retained version in the disposable database.
- [x] Run a selected live visual pass on setup and Audit. Setup labels/layout were observed at 390/768/1440 CSS pixels without submitting the form. Audit filtering, details, checksum message and 25-to-27 cursor pagination were observed on synthetic data; no page-width overflow at 390/768/1440. Keyboard-only journeys and full accessibility remain open above.

### Milestone 08 · operations and controlled pilot — pilot-blocking

- [ ] External security review and remediation.
- [ ] Dependency/container vulnerability scanning on the exact release artifacts.
- [ ] Audit retention, external checkpointing/tamper detection and access-review procedure.
- [ ] Capacity, soak and failure-injection tests on target hardware.
- [ ] Monitoring, log retention, alert thresholds and incident runbook.
- [ ] Data retention, legal hold, deletion, privacy and acceptable-use policies approved by the company.
- [ ] Administrator/operator training and a support escalation path.
- [ ] Controlled pilot with non-critical data, named users, success metrics and rollback criteria.

## Known technical debt that still needs a decision

- [ ] Existing dependency/deprecation warnings: Starlette/TestClient behavior, missing future Chroma `get_config`, Pydantic v2 class configuration and naive UTC timestamps.
- [ ] The deterministic hash embedding is measured on the synthetic fixtures and remains an offline baseline, not an approved semantic retriever; replace or retain it only after the representative holdout and target-hardware comparison.
- [x] Chroma is treated as rebuildable derived data; dry-run/repair reconciliation and restore-time rebuild are implemented. Target-host restore proof remains open above.
- [ ] Audit hashing does not currently prove deletion or reordering resistance through an external checkpoint.
- [ ] The original archived demonstration database has no approved direct migration path. Import/migration must be designed and tested if its data is needed.
- [ ] Scanned PDFs/OCR, encrypted documents and advanced office formats need explicit support or clear rejection behavior.
- [ ] Antivirus/content-disarm integration requires a company-approved local scanning engine.
- [ ] SQLite remains for isolated development/tests only and must not be used as the company deployment database.

## Build-host checklist

- [ ] Use a controlled, patched build host with Docker, Compose v2, Python and Node.js.
- [ ] Review `deployment/artifacts.lock.json` and refresh pins only through an approved dependency update.
- [ ] Put the approved model records in `deployment/model`.
- [ ] Run the full backend suite and frontend clean install/lint/build.
- [ ] Run `deployment/scripts/build-release.ps1` without `-ApplicationOnly`.
- [ ] Confirm `release-manifest.json` says `complete: true`.
- [ ] Review `dependency-inventory.json` and all licence notices.
- [ ] Verify `SHA256SUMS` before and after transfer.
- [ ] Sign the release or record its hash in the company's release system.

## Target installation checklist

- [ ] Confirm the target is the release's supported platform (`linux/amd64`) or rebuild and validate for the actual architecture.
- [ ] Install Docker Engine, Compose v2 and PowerShell 7 from approved offline packages.
- [ ] Copy `.env.example` to `.env` and replace every placeholder.
- [ ] Use independent high-entropy values for JWT, database and one-time bootstrap secrets.
- [ ] Set `POSTGRES_PASSWORD_URLENCODED` correctly when the database password contains URL-reserved characters.
- [ ] Set `ORACLEX_HTTP_BIND`, `ORACLEX_HTTP_PORT` and exact `ALLOWED_ORIGINS` for the approved URL.
- [ ] Set the approved exact `OLLAMA_DEFAULT_MODEL` tag.
- [ ] Decide whether `MODEL_REQUIRED_FOR_READINESS` is required by company policy.
- [ ] Run `verify-release.ps1`.
- [ ] Run `install.ps1`; allow it to stop after creating `.env`, complete configuration and rerun it.
- [ ] Create the first company/administrator with the one-time bootstrap token.
- [ ] Disable bootstrap, restart and prove a second bootstrap attempt is rejected.
- [ ] Run `diagnostics.ps1` and retain readiness evidence.
- [ ] Run the disconnected network-isolation test and the full core-journey acceptance test.
- [ ] Take and restore the first verified backup before pilot data is admitted.

## Core functional acceptance

- [ ] Administrator, manager and employee sign-in; wrong/inactive/expired credentials fail correctly.
- [ ] Role/capability navigation and backend authorization agree.
- [ ] Same-company department and clearance boundaries hold for list, detail, search, assistant and download paths.
- [ ] Upload supported documents and reject empty, duplicate, oversized, unsupported, misleading, corrupt and encrypted inputs safely.
- [ ] Observe queued → processing → ready/failed document status and recover a failed job.
- [ ] Create a replacement version and verify old/new version behavior.
- [ ] Archive and restore content while searches are running.
- [ ] Ask supported and unsupported questions; inspect exact cited source locations and abstention.
- [x] Submit, review and complete a structured request with distinct decision and fulfillment states in automated local tests.
- [ ] Repeat the complete request journey with separate real user sessions on target PostgreSQL.
- [ ] Verify user, document, request and administrator actions appear in the audit log.

## Final pilot go/no-go gate

OracleX is ready for a controlled company pilot only when all of these are true:

- [ ] Milestones 01–08 show completed acceptance evidence.
- [ ] Every pilot-blocking checkbox in this document is complete or formally accepted by the accountable company owner with a documented compensating control.
- [ ] PostgreSQL, Docker, approved model, backup/restore, offline networking and capacity tests pass on the actual deployment class.
- [ ] The complete release checksum, model approval, licences, configuration record and operator runbooks are stored in the release record.
- [ ] Security, privacy, retention, accessibility and incident-response owners approve the pilot.
- [ ] A rollback decision, previous verified release and tested backup are available before launch.

Until then, OracleX remains a development/pilot candidate and must not be described as compliant, tamper-proof, fully air-gapped or production-ready.
