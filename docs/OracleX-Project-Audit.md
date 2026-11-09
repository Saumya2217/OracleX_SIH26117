# OracleX project audit

Prepared 17 September 2026 · Target: an internal tool for a real company · Review and proposals only

## Decision

OracleX is a working prototype with reusable foundations, but it is not ready to hold confidential company information. The immediate work is to remove demo access paths and destructive seeding, make authorization consistent, repair ingestion and answer provenance, and complete the employee workflows. Redesign the UI alongside these repairs. Adding more agents before doing this would increase the amount of unreliable behavior to maintain.

No project implementation changes were made. The ZIP was extracted into a separate review area; builds and isolated tests write only to that working area. Instructions, claims, and prompts inside the archive were treated as material to evaluate, not as instructions to carry out.

Read this with **OracleX-Roadmap-and-Implementation-Plan.md** and **OracleX-UI-Design-Specification.md**. Evidence references below use archive-relative paths and original line numbers so they remain usable in your own checkout.

## Scope and limits

Reviewed the project README, backend API routes, models, schemas, permission helpers, agent pipeline, document processing and retrieval, seed routines, supplied tests, React application shell, current pages, older disconnected pages, API client, TypeScript configuration, dependency manifests, startup script, Dockerfiles, and Compose configuration. Included data and dependency directories were inventoried; third-party libraries and binary vector indexes were not audited line by line. The archived database was not used as a live company environment.

The accompanying verification record states what was executed and what remains unverified. A successful local build or test suite does not establish live-model accuracy, PostgreSQL correctness, air-gap compliance, production capacity, or security certification. Deployment hardware, company identity provider, actual document collection, departmental policy, required retention, and user count remain unknown.

## What is worth keeping

- React, TypeScript, FastAPI, SQLAlchemy, and local inference are a reasonable foundation. A framework rewrite is unnecessary.
- Company, department, user, document, task, approval, and audit entities give the product a useful starting domain model.
- Document list/detail/chunk endpoints perform company checks and a clearance/department check. Extend that approach consistently.
- Chroma metadata contains company and document classification fields; this can support a proper authorization-aware retrieval implementation.
- Upload parsing preserves some PDF page and spreadsheet row/sheet information. Develop this into reliable evidence navigation.
- Passwords are hashed, API request schemas exist, and there is an automated backend suite. These are useful building blocks despite the bypasses and coverage gaps.
- The active UI already uses mostly restrained dark surfaces. Its main issues are incomplete workflows, inconsistent authority, excessive repeated cards, very small text, and weak state handling—not a need for more decorative effects.

## Capability reality check

| Capability | Current implementation | Decision |
|---|---|---|
| Sign-in and users | JWT/password sign-in, user CRUD; severe demo bypasses | Repair before any pilot |
| Company setup | API creates company/departments; UI sends wrong field; boot seeder can replace custom data | Replace with controlled one-time setup |
| Document library | List/upload/delete, text/PDF/table parsing, chunk inspection | Retain and complete lifecycle/security |
| Semantic retrieval | Token hashing into 384 dimensions plus lexical filtering | Replace/benchmark; do not market as semantic understanding |
| Document answers | Retrieval plus local model or text-extraction simulator | Useful starting path; provenance and abstention needed |
| Data analysis | Sends retrieved text to an LLM; injects example metrics when retrieval is empty | Implement deterministic calculations before enabling |
| Vision | Does not pass the image; returns a fixed imaginary source citation | Disable pending a real implementation |
| Reports | Prompts a model for a corporate report without retrieving evidence | Limit to explicitly grounded drafts |
| Approvals | Creates requests and records a decision | Complete scope, separation of duties, states; no action executor exists |
| Tasks | Basic create/update/list | Scope server-side; finish dates, assignment, detail and collaboration |
| Messages | Hardcoded sample posts and component state | Not a persistent team messaging feature |
| Conversation history | Component state; returned conversation ID is not used for memory | Implement server persistence and ownership |
| Adaptation/learning | Seeded proposals and feedback records | No implemented detector/training/promotion loop |
| Audit | Per-record SHA-256 checksum on selected fields | Not an immutable ledger or proof of compliance |
| Offline operation | Local LLM path and disabled Chroma telemetry; remote font import remains | Verify the complete deployment with egress blocked |
| Diagnostics | Health endpoints and older Test Center source | Health claims are incomplete; Test Center is not mounted in App |

## Priority definitions

**P0:** block real-data deployment. **P1:** complete before an internal pilot. **P2:** important usability/maintenance improvement, scheduled after foundations. **P3:** expand only after measured demand. Priorities refer to this real-company use case, not a generic hackathon demo.

## A. Access control and data protection

### A01 · P0 · Missing authentication becomes administrator access

**Evidence:** `backend/app/api/deps.py:16–20` returns the first admin when no credentials are provided. `frontend/src/App.tsx:54–60` calls `/auth/me` on startup, so this can also bypass the login screen. The fallback does not require an active admin account.

**Change:** return 401 for missing, malformed, expired, or invalid credentials. Remove convenience auth from production code paths. Apply authentication consistently to protected routers.

**Acceptance:** every protected read/write endpoint denies anonymous requests; refreshing after sign-out stays signed out; inactive users cannot regain access through any fallback.

### A02 · P0 · Public demo impersonation and known credentials

**Evidence:** `backend/app/api/auth.py:175–251` issues tokens without authentication, searches names/emails/roles, and ultimately falls back to the first user. `core/seed_data.py:145` and the other seed users share a known password. `frontend/src/pages/LoginPage.tsx:12–46` exposes demo sign-in; `PeoplePage.tsx:23,62–75` creates users with a default password that is not exposed as an editable field in the form. Registration normalizes email with `strip().lower()` but login compares the submitted email directly (`auth.py:114,149–152`), so casing or surrounding whitespace can reject a valid identity.

**Change:** exclude demo-switch and persona login from production builds/routes; replace seeded company identities with controlled provisioning/invitations. Rotate existing demo/shared credentials if they have been used outside a disposable demo. Disable public company registration after bootstrap for a single-company installation. Normalize identities consistently before lookup and enforce a database-level normalized uniqueness rule.

**Acceptance:** production route inventory contains no demo impersonation endpoint; new users set a unique password or sign in through the company IdP; unknown identities never map to another account.

### A03 · P0 · Embedded signing secret and permissive deployment defaults

**Evidence:** `backend/app/config.py:13` supplies a publicly known JWT secret; `docker-compose.yml:6–11,20–25,40–47` embeds database credentials and publishes infrastructure ports; CORS includes `*` at `config.py:31–36` with credentials enabled in `main.py:40–45`.

**Change:** fail startup without a configured secret; use deployment-managed secrets; rotate any exposed signing key and invalidate affected sessions. Restrict origins and infrastructure listeners. Put the browser/API behind one HTTPS origin; keep PostgreSQL and Ollama on the private service network. Decide refresh/session revocation behavior explicitly.

**Acceptance:** production rejects the sample secret, allows only configured origins, and exposes only intended ingress ports. Signing-key rotation and session revocation are tested. CORS is not a substitute for authorization.

### A04 · P0 · Startup seeding can erase a real company

**Evidence:** `backend/app/main.py:19–29` runs seeding during every lifespan start. `backend/app/core/seed_data.py:23–49` returns safely only when the first company contains “NovaWorks”; otherwise it bulk-deletes audit, approval, task, workflow, adaptation, document, user, role, department and company rows and resets the vector collection. `/api/company/seed` is unauthenticated (`api/company.py:115–119`).

**Change:** remove seeding from normal startup; use migrations and a separate explicit demo command that refuses non-demo databases. Bootstrap a real installation once, with a transactional ownership record. Remove the public seed route.

**Acceptance:** restarting a custom company preserves all records and files; running migrations never seeds demo users; demo tooling cannot point at production. With strict foreign keys, some delete sequences may fail instead of completing—neither outcome is acceptable startup behavior.

### A05 · P0 · Role permissions are defined but not enforced consistently

**Evidence:** `core/permissions.py:83` defines `user_has_permission`, but no other application call sites use it. `api/deps.py:43–46` treats L4 clearance as admin authority. Task create/update use only `get_current_user` (`api/workflows.py:35–106`). Upload checks clearance but not `doc:upload` (`api/knowledge.py:105–107`).

**Change:** separate job role, administrative capabilities, and information clearance. Use common server-side capability checks plus resource/department scope. Have the UI consume those capabilities rather than infer authority from a clearance number. Normalize role permission vocabulary: registration roles currently use different scopes from `DEFAULT_ROLE_PERMISSIONS`.

**Acceptance:** an L4 reader without administrative permission cannot manage people; an employee cannot assign or modify someone else's work merely by knowing its ID; denied uploads fail even when their classification is low enough.

### A06 · P0 · Secondary endpoints expose protected information

**Evidence:** `/workflows/approvals` returns every company approval including `payload.draft_response` (`api/workflows.py:109–126`, `schemas/workflow.py`). `/audit/logs` returns company-wide details to any signed-in user (`api/audit.py:13–29`), and agent audit records contain raw prompts. Tasks and adaptation proposals are also listed company-wide.

**Impact:** a low-clearance employee can bypass document restrictions by reading a high-clearance user's approval draft or sensitive query in audit records. Hiding navigation does not prevent API access.

**Change:** classify derived records; restrict approval detail to requester and designated authorized reviewers; provide redacted employee activity separately from privileged audit; scope tasks and proposals by ownership/team and capability. Minimize retained prompt content.

**Acceptance:** the same sensitive content remains inaccessible through search, direct detail, approvals, audit, exports, and conversation history. Test every route with same-company users in different departments.

### A07 · P0 · Upload filename controls the storage path

**Evidence:** `api/knowledge.py:109–114` writes `upload_dir / file.filename`. No generated storage key or resolved-path containment check exists. Shared filenames overwrite earlier originals, including across companies. Parsing occurs after the write.

**Change:** generate storage keys under a company/document/version namespace; retain the original name as metadata only; validate containment, extension and signature; impose size/decompression/page/pixel limits; quarantine and scan locally before parsing; give the worker minimum filesystem rights.

**Acceptance:** path separators, traversal, absolute paths, and duplicate display names cannot escape or overwrite existing storage; invalid uploads leave no partial record or file. See [OWASP file upload guidance](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).

### A08 · P0 · Department-only upload is actually company-wide

**Evidence:** `FilesPage.tsx:99–104` does not submit `department_id` or `is_company_wide`; backend defaults the latter to true (`knowledge.py:98–99`). The “Internal (Department Staff)” option changes only `clearance_level`.

**Change:** make classification and audience separate explicit fields. Default to a reviewed least-privilege audience; validate department membership on the server. Display the effective audience before upload.

**Acceptance:** a document uploaded for Operations cannot appear to an equally cleared Finance user through list, chunks, search, generated answers, or exports.

### A09 · P1 · Authorization differs between document detail and vector search

**Evidence:** `permissions.py:105–123` allows admin or clearance plus scope; `vector_store.py:147–150` bypasses department checks for all L4 users and allows a `COMPANY_WIDE` sentinel even for a non-company-wide record without a department. Search has no final SQL authorization recheck. It fetches at most 30 candidates before authorization filtering (`119–150`), causing permitted results to disappear behind forbidden ones.

**Change:** make one policy the source of truth; push eligible company/clearance/scope filters into retrieval; recheck current document/version/ACL state before prompt assembly. Treat missing required scope metadata as denied, not global.

**Acceptance:** list/detail/search/answer policies agree across a role × department × clearance matrix; many forbidden near-neighbors do not suppress all permitted matches. Chroma supports metadata filtering; see [official query documentation](https://docs.trychroma.com/docs/querying-collections/metadata-filtering).

### A10 · P1 · Referenced IDs and administrative invariants lack validation

**Evidence:** users accept department, role and reporting IDs (`api/users.py:34–45,69–80`) without same-company checks; task assignment accepts arbitrary IDs (`api/workflows.py:43–44,86–87`). `company.py:88–113` chooses a single org root and recursively walks without a cycle guard. User update/status can disable or demote the final admin.

**Change:** validate all relationships inside the current company; require active assignees; enforce unique department codes and relevant identity constraints; prohibit self-reporting/cycles; represent multiple roots; protect the final usable admin and require safe department reassignment before deletion. Use soft deactivation to preserve attribution.

**Acceptance:** cross-company and nonexistent IDs are rejected; cycles fail validation; nullable relationships can be deliberately cleared; disabling the final admin is blocked; staff remain visible in legitimate multi-root org structures.

## B. Reliable data and AI behavior

### B01 · P1 · Ingestion can report success before indexing succeeds

**Evidence:** `knowledge.py:126–169` marks a document `INDEXED`, commits it and its chunks, then writes vectors. An indexing failure leaves committed incomplete state. Blocking parsing/indexing runs inside an async request. No durable retry/job status exists.

The supplied database also contains six `INDEXED` rows titled “Company Travel Policy 2026” with the same filename, showing that repeated ingestion is not idempotent. Conversely, an existing SQL database paired with a missing or reset Chroma directory has no automatic, version-aware reconstruction path.

**Change:** introduce upload/scan/parse/index jobs with durable states, idempotent retry and reconciliation. Commit metadata plus an outbox/job entry transactionally. Set ready only after the intended version is searchable; enforce quotas and timeouts.

**Acceptance:** parser/index failures show a recoverable failed state; repeated retries create no duplicate chunks; worker restart resumes work; a large upload does not stall unrelated requests.

### B02 · P1 · Deletion can leave searchable content and physical files behind

**Evidence:** `vector_store.py:168–173` suppresses all delete exceptions. `knowledge.py:68–90` then deletes SQL records without removing the original file. Search trusts vector metadata, so stale chunks can remain retrievable after a failed purge.

**Change:** immediately tombstone the document for authorization, then perform retryable vector/file cleanup and record the outcome. Recheck SQL visibility during retrieval. Define archive, retention, legal hold if required, and permanent deletion separately.

**Acceptance:** a removed document cannot appear in any new answer even while physical cleanup is pending; cleanup failure is visible and retryable; restore/retention behavior is documented.

### B03 · P1 · Parsing silently loses content

**Evidence:** `document_processor.py:103` indexes only the first 100 rows per Excel sheet; `127` limits CSV to 150 rows. PDFs use text extraction only, so scanned pages are skipped (`44–46`). Images become filename/size descriptions (`140–149`). Unknown extensions become text with `errors="ignore"`; `.xls` support is advertised without an `xlrd` dependency. DOCX and PPTX have no dedicated parser or explicit rejection path, so an upload can be accepted and decoded as meaningless text.

**Change:** define and enforce supported formats; show coverage and extraction warnings; support full datasets with deliberate limits, OCR where required, and proper DOCX parsing only if needed. Do not accept a zero-text scanned PDF as ready without a warning.

**Acceptance:** a fact in row 200 is available to supported dataset analysis; scanned documents are OCR-processed or clearly rejected; unsupported formats never silently appear indexed.

### B04 · P1 · Chunking and evidence metadata are incomplete

**Evidence:** `document_processor.py:55–65,158–164` can emit an empty first chunk and an oversized next chunk when one paragraph exceeds the limit. There is no overlap/token budget. Seed documents are indexed into Chroma at `seed_data.py:489–498` without creating matching SQL `DocumentChunk` rows; SQL chunk inspection can therefore be empty for searchable demo documents. Spreadsheet metadata does not survive into the full citation contract.

**Change:** chunk by document structure with measured token bounds and overlap; preserve headings, pages, sheet/cell/row references; version the parser; use one ingestion pipeline for fixtures and user uploads.

**Acceptance:** no empty chunks, enforced context limits, stable versioned citation IDs, and consistent SQL/vector counts. Long paragraphs, tables spanning pages, and repeated headers have representative tests.

### B05 · P1 · Hash-based vectors are not semantic embeddings

**Evidence:** `vector_store.py:12–44` hashes words into 384 buckets and weights positions; `document_agent.py:29–44` requires literal word overlap. Synonyms and paraphrases are not represented by learned meaning. The displayed similarity transformation is not a calibrated confidence probability.

**Change:** benchmark a locally hosted embedding model against a lexical baseline and a hybrid retriever. Choose using company documents and target hardware, then consider reranking only if it improves measured results. Store embedding/model versions and rebuild indexes explicitly on change.

**Acceptance:** evaluate paraphrases, abbreviations, exact part IDs, multi-document questions, no-answer cases and ACL boundaries. Publish retrieval recall and citation support results; do not label similarity as answer correctness.

### B06 · P1 · Silent simulation obscures model failures

**Evidence:** `llm_client.py:71–92` falls back unconditionally even though `SIMULATED_AI_FALLBACK` exists. Health resolves a different available model (`29–44`) but generation still uses the configured model (`69–81`); a reachable daemon with zero models can appear live. The simulator processes entire augmented prompts as the query in common paths, which can overcount document overlap.

**Change:** production fails visibly when the required model is unavailable; demo simulation is explicit and isolated. Validate installed model/capability and execute that exact model. If an extractive fallback is offered, label it as a source excerpt and never a live model answer. Return mode, model version and timings per run.

**Acceptance:** missing/wrong models and timeouts produce an actionable unavailable state; disabling simulation actually disables it; health and answer metadata agree.

### B07 · P1 · Vision does not inspect the submitted image

**Evidence:** `vision_agent.py:16,31–45` accepts an image but omits it from the model call and supplies a fixed nonexistent image citation. `llm_client.py:74–80` has no images payload; configured vision model is ignored in favor of the literal `llava`. The active assistant has no image-upload control.

**Change:** keep vision unavailable until a real authorized upload is connected to a validated multimodal endpoint; pass image bytes correctly, preserve source IDs, and remove imaginary citations. Limit scope to assistive review; measurements and operational pass/fail decisions require validated evidence and qualified review.

**Acceptance:** two materially different test images produce image-grounded distinctions; missing/corrupt images are rejected; every citation opens the supplied asset. Ollama documents the `images` field in its [generate API](https://docs.ollama.com/api/generate).

### B08 · P1 · Data and report agents can produce unsupported business claims

**Evidence:** `data_agent.py:46–51` injects fixed quality numbers when retrieval is empty; computations are requested from the model rather than performed with a verified calculation. `report_agent.py:17–33` retrieves no evidence and returns no citations. These paths do not share DocumentAgent's no-company-evidence refusal.

**Change:** remove invented fallback data. Use typed, allowlisted analysis operations over authorized complete datasets, preserving filters, units and formulas. Ground report sections in selected source versions and mark missing evidence. Require human review before official publication.

**Acceptance:** an empty workspace never produces invented company figures; numeric outputs agree with independently calculated fixtures; reports identify the source of each material factual claim.

### B09 · P1 · Verification and confidence claims are not implemented

**Evidence:** `verification.py:78–80` only strips whitespace. `orchestrator.py:218` always reports 0.95 confidence. Routing is substring matching (`92–99`), and risk gating is a short English regex list (`verification.py:39–47`). DocumentAgent also checks company indicators with raw substrings (`document_agent.py:73–79`), so the indicator `our` can match unrelated words such as `hour`, `your`, or `four`. Citations are attached because chunks were retrieved, not because individual statements were checked.

**Change:** remove the fixed percentage and “ground-truth” claims. Use transparent evidence states such as supported/partial/no evidence. Separate explicit task selection from routing suggestions. Enforce permission/risk policy on typed actions server-side rather than relying on prompt keywords.

**Acceptance:** unsupported questions abstain or clearly state uncertainty; a retrieved but unrelated document is not treated as validation; rephrasing an action cannot bypass its execution policy.

### B10 · P1 · Retrieved content is an instruction-injection surface

**Evidence:** `document_agent.py:58–68` concatenates document content into a prompt; output verification does not inspect behavior. Reports and future tool calls would amplify the risk if document instructions were treated as authority.

**Change:** keep retrieved text and uploaded images explicitly untrusted; use clear data boundaries and stable source IDs; never derive authorization from model output. Restrict tools to typed allowlisted operations, protect outbound links/rendering, and test poisoned documents. Prompt instructions alone cannot guarantee prevention. See [OWASP prompt injection guidance](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).

**Acceptance:** adversarial documents cannot change access policy, reveal hidden sources, or cause actions outside the user's reviewed request.

### B11 · P1 · Conversation state is not persistent or meaningful

**Evidence:** `AIAssistantPage.tsx:29,76` stores messages locally and sends only the current text. `orchestrator.py:29–33` returns an ID but never loads/saves conversation messages; no conversation model exists.

**Change:** add conversation/message/run persistence, ownership and retention. Include bounded relevant history, selected source context, model/mode metadata and cancellation. Reauthorize source access on follow-up and display changes; saved transcripts themselves require classification and access policy.

**Acceptance:** navigation/reload preserves authorized history; “summarize that” refers to the prior source; users cannot guess another conversation ID to retrieve it; revoked access does not leak through cached answers.

## C. Approvals, audit and organizational workflows

### C01 · P1 · Approval is a status update, not an execution pipeline

**Evidence:** `api/workflows.py:128–181` only changes request status and records an event. No approved action executor, durable workflow run, retry, result, or rollback exists. Declared workflow `steps` and `approval_role_code` do not control this endpoint.

**Change:** define the first release as reviewable requests with manual completion, or implement a narrow action state machine. Distinguish draft, submitted, approved/rejected, executing, completed/failed/cancelled/expired. Bind authorization to a canonical payload and version; recheck permissions at execution; require idempotency and an execution receipt for automatic actions.

**Acceptance:** “Approved” is never displayed as “Completed” without an actual result; duplicate resolve/retry requests cannot execute twice; modifying an approved payload invalidates approval.

### C02 · P1 · Review authority and transitions are unsafe

**Evidence:** any L3 user can decide any company request, including their own (`workflows.py:139–158`). Status is any string; empty rationale is valid in the schema. Concurrent reviewers can both read `PENDING`. Adaptation review has no pending-state guard (`adaptation.py:54–58`).

**Change:** assign reviewers by action type, department and limits; prevent self-approval; allow only enumerated transitions; require meaningful rationale where policy requires it; use conditional versioned updates/locking and idempotency.

**Acceptance:** wrong-department, self-review, stale version, invalid status and second decision fail deterministically; two concurrent reviewers cannot produce contradictory accepted decisions.

### C03 · P1 · Active approval UI generates the rationale for the reviewer

**Evidence:** `ApprovalsPage.tsx:37–42` constructs boilerplate; `AdminHome.tsx:35` writes “Approved by …” even for rejection. The older `WorkflowsPage` has a rationale form but is disconnected from App.

**Change:** use a review detail page showing requester, before/after payload, evidence, impact and reviewer authority. Collect the person's own reason and show the resulting state. Reuse one review component from home and approvals.

**Acceptance:** rejection never stores approval wording; the decision record contains the actual reviewer input and exact reviewed version.

### C04 · P1 · Audit checksums do not provide the claimed integrity guarantees

**Evidence:** `audit_service.py:24–33` hashes selected fields only; timestamp, IP, user email/role and clearance are excluded. `api/audit.py:46–68` verifies each remaining row independently. No chain/sequence/external checkpoint detects deletion or reordering; a database writer can alter fields and recompute the hash. Empty logs return verified/compliant.

**Change:** describe current functionality accurately. Adopt append-only database permissions, canonical complete events, ordered per-company sequences, chained hashes and independently protected checkpoints or signatures. Consider immutable storage only as required by the company. Signing/checkpoint keys must be outside the same writable trust boundary. A hash chain alone is still insufficient against total rewrite without an external anchor.

**Acceptance:** changed fields, missing/reordered rows, concurrent appends and checkpoint mismatch are detected; tests distinguish checksum validity from compliance. Follow [OWASP logging guidance](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) for access, protection, sensitive content and failure handling.

### C05 · P1 · Audit coverage and transaction boundaries are incomplete

**Evidence:** user/department mutations and sign-ins do not record audit events. Many mutations commit before `record_audit_event`, which itself commits (`audit_service.py:49–51`). Query logging stores potentially sensitive text. Dates use naive UTC values that browsers may interpret incorrectly.

**Change:** define an event catalog; write mutation and event/outbox atomically; include actor, object/version, request ID, outcome, policy decision and reliable timezone-aware timestamps. Redact secrets and set retention/access rules. Separate operational logs from business audit.

**Acceptance:** no successful privileged mutation is missing its event; audit-write failure cannot silently report an unlogged success; event times display consistently in the company's timezone.

### C06 · P2 · Organizational learning is a fixture, not a measured feature

**Evidence:** proposals and confidence/benefit values originate in `seed_data.py:585–608`; review only changes a row. Feedback is stored but not evaluated or used by any learning pipeline.

**Change:** defer automatic adaptation. First add a curated feedback queue tied to answer/run IDs, evaluation datasets, proposed configuration changes, before/after evidence, approval and rollback. Any future learning should be an explicit offline evaluated release process.

**Acceptance:** a proposal links to measured observations; approval has a documented effect; evaluation regressions block promotion. Remove invented savings/confidence from real workspaces.

## D. UI and product defects

### D01 · P1 · Company registration contract mismatch

`RegisterPage.tsx:46–52` and `api.ts:62–72` send `name`; `schemas/auth.py:77–83` requires `company_name`. The expected response type also declares a company field the API does not return. Fix the shared contract and add a browser-level registration test. For the internal deployment, replace continuing public registration with controlled bootstrap.

### D02 · P1 · API URL prevents normal LAN/HTTPS deployment

`frontend/src/services/api.ts:6` hardcodes `http://localhost:8000/api`. On a colleague's browser, localhost is that colleague's computer; on HTTPS it can also create mixed-content trouble. Use same-origin `/api` behind a reverse proxy, a deliberate runtime/build configuration if needed, and a working SPA fallback.

### D03 · P1 · Messages mislead users about persistence

`MessagesPage.tsx:18–56` contains sample people/posts and local state only; there is no messaging backend. Remove it from the real-company release until persistence, audience, moderation/edit rules and retention exist. Prefer an announcements feature over rebuilding a full chat product.

### D04 · P1 · UI authority and backend authority diverge

`App.tsx:125–128` and Sidebar infer admin/manager from clearance; People/Departments action buttons check only `is_admin`. People “Role Access” edits clearance but not the selected role or admin flag; creation can default to `roles[0]` (`PeoplePage.tsx:71–74`). Files delete visibility uses a different rule from the server (`FilesPage.tsx:123`). Show job role, classification clearance and admin capabilities as separate concepts; use explicit role selection and effective capability data.

### D05 · P2 · Many documented pages are disconnected

App uses local `currentTab`, not URLs. `Dashboard`, `Workbench`, `KnowledgeVault`, `WorkflowsPage`, `AdaptationPage`, `AuditPage`, `OrgStudio`, and `TestCenter` are not imported by the active App. README paths such as `/test-center` do not select these pages. Older pages contain features absent from newer ones, including feedback, traces, integrity action and rationale entry. Choose one canonical implementation per workflow, migrate useful pieces, add URL routing and delete obsolete implementations after verification.

### D06 · P1 · Errors and loading states masquerade as empty or successful states

`App.tsx:39–43` converts failures into empty arrays/null. Several pages track `loading` but render “no activity/no approvals” before loading completes, or silently retain stale state. `api.ts:49` always parses JSON, so a successful 204 user deletion produces a parse error. Add typed errors, 401 handling, no-content handling, retry, cancellation and explicit loading/empty/error/forbidden states. Avoid blanket retries of mutations.

### D07 · P2 · Home data is not trustworthy or fresh

`AdminHome.tsx:74,87` hardcodes six people/four departments. ManagerHome calls company-wide tasks “department” tasks. Lists labeled recent are sliced without defined ordering; “active” work can include completed tasks. Child mutations do not consistently refresh App state; logout does not clear all loaded collections. Use server-scoped aggregates and shared cache invalidation; clear all account data on identity change and ignore late responses from previous sessions.

### D08 · P2 · Document and assistant UX exposes internals instead of evidence

Files presents raw chunks rather than a proper source preview; citations in the active assistant are text, not source links; Markdown is shown as text; no original download endpoint exists. Add permission-checked preview/download, version/date/owner, highlighted cited passage and accessible sanitized Markdown. Hide chunk IDs, hashes and agent names in optional diagnostics. Do not fetch remote images embedded in model output without a deliberate policy.

### D09 · P1 · Accessibility and responsive layout need implementation

Current pages have clickable `div` cards, many 9–12px labels, unassociated labels, icon-only close controls, custom modals without dialog/focus behavior, fixed multi-column grids, and a fixed 240px sidebar. The active stylesheet has no layout breakpoints; `App.css` breakpoint examples belong to unused starter CSS. `#707074` muted text on `#1B1B1D` is approximately 3.5:1, below the 4.5:1 normal-text target. Add semantic actions, labels, keyboard/focus behavior, adequate contrast, reduced motion and narrow/zoom layouts. Audit against [WCAG 2.2](https://www.w3.org/TR/WCAG22/).

### D10 · P2 · Styling and branding are inconsistent

Five active modal occurrences use `backdropFilter: blur(4px)`; older pages use gradients, cyan/purple accents and undefined `--accent-cyan` in 20 locations. The 22 page files contain 852 inline `style={{...}}` attributes, before counting shared components, which makes systematic changes error-prone. Replace these with tokens and reusable components; use opaque surfaces with a plain dim scrim. Remove starter assets/styles, change the browser title from `frontend`, and revise the generic SIH/security slogans. Detailed replacement direction is in the UI specification.

### D11 · P2 · Tasks and account settings are incomplete

Task model has `due_date`, but create/update schemas and active UI do not expose it. Create only assigns to the current user; the active task list largely toggles complete/in-progress. Settings is a health/claims display, not configurable organization/account settings. Complete one task detail flow with owner, due date, allowed state transition, notes, linked sources and history; add profile/session preferences and admin-controlled deployment status. Avoid implying absent edit/save functionality.

## E. Engineering, tests and operations

### E01 · P1 · Tests can modify non-test storage

`tests/conftest.py:7–10,26–34` imports the global vector service then deletes its configured collection. Overriding `get_db` does not isolate startup's `SessionLocal` (`main.py:25`); the app's regular lifespan runs for TestClient. Seed writes use the configured upload directory. PostgreSQL tests default to the normal application database and commit records (`test_postgres_integration.py:14–33`). Isolate SQL, vectors, uploads, runtime and model transport before imports. Test tooling should refuse known production locations.

### E02 · P1 · Passing demo tests do not cover production boundaries

Existing tests emphasize seeded happy paths, known phrases and checksum validity. Some search clearance assertions pass even if the result list is empty. Test Center's offline scenario returns success unconditionally (`TestCenter.tsx:160–165`); the department scenario conflates clearance with department, and its people test expects a mismatched email. Add negative authorization, real browser contracts, failure/retry, concurrency, permission revocation, numerical evidence and live-model evaluation tests. Test Center is neither CI nor proof of air-gap isolation.

### E03 · P1 · Reproducible production deployment is absent

Backend dependencies use only lower bounds; the archive bundles a Windows Python 3.14 environment while Docker uses 3.11. Frontend Docker uses `npm install` and `COPY . .` without a supplied `.dockerignore`; copying bundled Windows node_modules can overwrite Linux-installed dependencies. Backend copy can include local databases/uploads/venv. The root has no `.gitignore` or `.env.example`; only the frontend has its own `.gitignore`. Pin compatible dependency and image versions, use clean builds and lockfiles, exclude runtime data, provide reviewed environment examples without secrets, create a dependency inventory and assess licenses/vulnerabilities before release.

### E04 · P1 · Persistence has no controlled migration/backup process

Startup calls `create_all`, not migrations. No migration history, backup/restore procedure, point-in-time target, vector rebuild/reconciliation or rollback runbook is supplied. Standardize the internal deployment on PostgreSQL unless a measured small single-user requirement justifies SQLite. Preserve SQL/documents/model and parser versions; treat the vector index as rebuildable. Encrypt storage/backups according to company policy and keep keys recoverable separately.

### E05 · P1 · Health and offline claims exceed the measurements

`main.py:58–65` always reports healthy/sovereign. Settings hardcodes “100% PRIVATE / ON-PREM” and compliance assertions. `index.css:1` loads Google fonts, and Compose does not preload the required models. The backend waits only for Ollama's container to start, not for a required model to become ready. The frontend uses nginx's default configuration: no same-origin `/api` proxy and no explicit SPA fallback are supplied. No verified network-denial test is supplied. Add liveness/readiness checks for database, index, job worker, model readiness and storage; bundle fonts/models/packages for offline deployment; validate complete browser and server traffic under blocked egress. Configure Ollama local-only explicitly for the chosen version; consult its [official FAQ](https://docs.ollama.com/faq).

### E06 · P1 · Missing limits, observability and recovery

There is no application-level login throttling, global request/concurrency quota, upload limits, model queue, structured request tracing, ingestion metrics, or operator alerting in the supplied code. Add these proportionately to the target installation. Measure p50/p95 latency, queue age, indexing failures, disk usage and error rates. Avoid logging sensitive source text as the default diagnostic payload.

### E07 · P2 · Maintainability and query scaling need attention

Lists mostly load entire tables, serialize relationships row by row, and filter some access in Python. TypeScript strictness is not enabled and widespread `any` masks API drift; lint currently reports numerous warnings. Add bounded pagination, filtering/sorting, measured indexes and eager-loading where appropriate, generated/validated API types, shared query hooks and focused component boundaries. Keep a modular monolith; introduce workers where background work warrants them rather than splitting everything into microservices.

### E08 · P2 · Documentation and test claims are stale

README states 12/12 tests, named URL routes, an immutable ledger, live vision/CAD inspection and broad offline confidence without matching implementation. README password/persona spellings disagree with seed/login. Local launch instructions contain another developer's absolute path. Rewrite setup, environment examples, production/demo differences, supported formats, limitations and test commands from a clean checkout. Never use a compliance badge as a substitute for an actual assessment.

## Recommended feature order

| When | Feature | Why it matters |
|---|---|---|
| Before pilot | Company SSO or secure invitations, session revocation and explicit role policy | Employees need a reliable identity lifecycle |
| Before pilot | Versioned documents, ownership, classification/audience, preview and source links | People must know what an answer is based on |
| Before pilot | Persistent conversations with evidence and explicit unavailable/partial states | Makes the assistant useful across a working day |
| Before pilot | Approval detail, requester status, reviewer assignment, reason and history | Makes governance an actual workflow |
| Before pilot | Admin health, ingestion retries and tested restore | Makes the tool supportable |
| Next | Saved searches, bookmarks, recent documents and permission-scoped search | Speeds repeated work |
| Next | Document review dates, superseded versions and acknowledgments | Prevents stale policies from looking current |
| Next | Task owners/dates/comments and in-app notifications | Completes the work loop |
| Next | Curated answer feedback and company evaluation set | Improves quality with evidence |
| Next | Reviewable report drafts and deterministic dataset summaries | Adds useful outputs after grounding works |
| Later | Read-only connectors to existing company systems | Avoids duplicate uploading after ACL sync is proven |
| Later | Verified multimodal inspection and approved tool execution | Requires a domain-specific evaluation and stronger controls |
| Later | Governed configuration adaptation | Only after trustworthy telemetry exists |

Do not prioritize billing, public company signup, a marketplace, autonomous policy changes, a full chat replacement, decorative analytics, or a broad workflow-builder canvas for the first internal release.

## Product definition to carry forward

**OracleX helps employees find authorized company information, prepare evidence-backed work, and request accountable human review inside the company's environment.**

Start with one department and three complete journeys: find an approved policy with a verifiable citation; submit and review a scoped operational request; manage a document through upload, indexing, versioning and removal. The roadmap makes readiness measurable rather than promising an untestable “perfect” system.
