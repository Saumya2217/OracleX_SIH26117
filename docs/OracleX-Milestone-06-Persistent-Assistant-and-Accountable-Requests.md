# OracleX Milestone 06 · persistent assistant and accountable requests

Completed 19 September 2026  
Source release version: **1.5.0**

## Outcome

Milestone 06 is implemented in source. OracleX now stores private assistant conversations, messages, run outcomes and immutable citation snapshots. Controlled work uses typed, versioned requests with explicit submission, assignment, decision and fulfillment states. The Ask OracleX and Requests pages were rebuilt as opaque professional workspaces with no glassmorphism, blur, gradients or decorative AI imagery.

This milestone does not make OracleX production-ready. PostgreSQL concurrency, Docker restart persistence, approved-model behavior, company retention policy and the remaining Milestone 07/08 acceptance work still require the target environment.

## Persistent assistant

- Added company- and owner-scoped conversations with classification, archive state and an explicit retention-policy date field.
- Added ordered user/assistant messages. Each exchange reserves its sequence numbers while the conversation row is locked, preventing concurrent replies from colliding on PostgreSQL.
- Added durable agent runs with started/completed/failed state, evidence outcome, generation mode, model identifier, prompt version, retrieval mode, review requirement, linked request and exact source-version identifiers.
- Added immutable citation snapshots containing the exact document, version, chunk, source location, excerpt and retained-source path shown when the answer was created.
- Persisted safe failure records without storing raw exception details in the user-visible transcript.
- Rechecked current document access whenever a saved conversation is opened. If any cited source is no longer authorized, the saved answer and its citations are redacted.
- Added bounded follow-up context using only the last two user questions. Referential prompts such as “summarize that again” retrieve against the prior topic without injecting a previous assistant answer that may have become unauthorized.
- Retained the Milestone 05 evidence contract: no hidden reasoning trace and no invented confidence percentage.

## Accountable requests

- Replaced product use of the generic approval API with three typed definitions: controlled change, access request and purchase request.
- Added validated states: `DRAFT`, `SUBMITTED`, `ASSIGNED`, `APPROVED`, `REJECTED`, `CANCELLED` and `COMPLETED`.
- Every draft save creates an immutable request-version snapshot. Submission binds the workflow to one exact version.
- Decisions require the submitted version identifier, a reviewer-entered reason and the current optimistic lock version.
- Requesters cannot review their own requests. Assigned requests cannot be decided by another reviewer except an authorized administrator.
- SQL conditional updates reject stale browser actions and ensure only one decision or fulfillment can win.
- Approval records a decision only. A separate once-only fulfillment action records completion notes and the responsible user.
- Added a human-readable event timeline and recipient-scoped internal notifications with deep links.
- Assistant prompts that describe controlled action create an editable typed draft. They do not claim approval or execution.
- Removed the legacy generic approval list/resolve routes from product use. The old table remains only for safe migration/history compatibility.

## Professional UI delivered in this milestone

### Ask OracleX

- Persistent recent-conversation rail and new-conversation action.
- Reloaded transcripts with saved failures, evidence status, generation/retrieval metadata and exact citations.
- Real copy, retry, archive and linked-request controls only where the behavior exists.
- Explicit empty, loading, failed, access-revoked and evidence states.
- Responsive two-pane layout using solid surfaces and restrained business styling.

### Requests

- My requests and permission-aware review queue.
- Typed creation forms and editable drafts.
- Save-as-new-version and exact-version submit controls.
- Assignment, approve/reject with mandatory reason, and separate completion record.
- Clear status, requester, reviewer, version and record identity fields.
- Readable timeline and immutable-version count.
- Responsive list/detail behavior and deep-link opening by request ID.

## Database and API changes

Alembic revision `b7d2c4e91f60` adds:

- `conversations`
- `conversation_messages`
- `agent_runs`
- `agent_run_citations`
- `business_requests`
- `business_request_versions`
- `business_request_events`
- `internal_notifications`

New APIs are under `/api/conversations` and `/api/requests`. The assistant query API accepts an owned conversation ID and returns `requires_review` plus an optional typed `request_id`.

## Verification performed on this device

| Check | Result |
|---|---|
| Complete backend suite | **58 passed, 5 skipped** |
| New conversation tests | Ownership, ordered persistence, contextual follow-up, archive, citation redaction and saved failure passed |
| New request tests | Typed validation, immutable versions, exact-version binding, stale updates, self-review denial, notification scope, decision/fulfillment separation and duplicate prevention passed |
| Alembic lifecycle | Upgrade, metadata check, downgrade and reapply passed on isolated SQLite |
| Frontend lint | Passed with no warnings or errors |
| TypeScript/Vite build | Passed; 1,864 modules; 342.91 kB JavaScript (94.35 kB gzip), 35.93 kB CSS (7.53 kB gzip) |
| Live local UI | Employee sign-in, supported answer, exact citation, refresh persistence, empty requests, typed draft creation and timeline rendered at the available 762 px viewport |
| Source version | API, Compose tags, artifact lock and release builder updated to 1.5.0 |

The five skipped tests require a reachable disposable PostgreSQL service. Four cover the existing PostgreSQL integration checks; the fifth races two request decisions and asserts that exactly one conditional update wins.

## Not completed or not proven here

- No Docker executable was available, so container startup and host restart persistence were not rerun.
- No PostgreSQL server was available, so the new simultaneous-decision test exists but was skipped.
- No approved local Ollama model was installed. Live UI verification used the explicitly enabled development simulation; this is not model-quality evidence.
- No company retention duration has been approved. The schema has `retention_until`, but the company must set policy, scheduled enforcement, legal-hold rules and deletion evidence in Milestone 08.
- The live viewport was 762 px wide. Formal 390/768/1440 px visual regression, 200% zoom, keyboard-only and screen-reader acceptance remain in Milestone 07.
- The local refresh check proved database-backed reload. Full process/host restart proof remains part of target-host recovery acceptance.
- Stable path-based routes and browser back/forward behavior remain a Milestone 07 task. Request notification deep links currently use safe query parameters.

## Next phase

Milestone 07 is next. It will finish the professional My work, People, Teams, Audit and Overview workflows, add stable routing and shared UI primitives, remove remaining prototype wording and inline styling, and complete responsive and accessibility acceptance across employee, reviewer and administrator journeys.
