# OracleX milestone 01 — security foundation

Completed 18 September 2026 · Implementation snapshot included separately

## Outcome

OracleX now has a safer production-default foundation. This milestone closes the verified anonymous-admin path, removes production demo identity and seed routes, protects first setup, isolates test storage, hardens upload storage, and applies explicit authorization to several exposed workflows. The original ZIP remains unchanged; implementation occurred in a clean source-only copy.

Do not load confidential company data yet. Database migrations, durable ingestion, evaluated retrieval, restore procedures and the professional UI are still incomplete.

## Implemented

### Authentication and setup

- Missing, malformed, expired and inactive-user tokens fail with `401`.
- L4 clearance no longer grants administrator authority.
- `/auth/demo-switch` and `/company/seed` are not registered unless `DEMO_MODE=true`.
- Normal startup no longer seeds or replaces company data.
- Company setup requires `BOOTSTRAP_ENABLED=true`, a constant-time checked setup token and an empty installation. Repeated setup returns `409`.
- Login normalizes email casing and surrounding whitespace.
- JWT secrets are required, must be at least 32 characters and reject the archived demo key.
- Wildcard CORS origins and contradictory demo settings fail configuration validation.
- Tokens expire after 60 minutes by default rather than 24 hours.

### Documents and retrieval

- Upload permission is checked through the role capability model.
- Classification must be L1–L4; audience is explicit and department IDs must belong to the current company.
- Supported uploads are currently PDF, TXT, Markdown, CSV and XLSX. Other extensions return `415`.
- Uploads stream into a generated company/document directory, never a user-controlled path, with a 25 MB default limit.
- Empty files and exact duplicate content are rejected. SHA-256 is stored for new uploads.
- SQL records become `INDEXED` only after vector indexing succeeds; common failures roll back and remove partial files/vectors.
- Deleted documents are tombstoned before cleanup, their stored file is removed, and vector deletion errors are no longer silently swallowed.
- List/detail/search omit non-indexed records. Vector candidates are rechecked against current SQL state and canonical authorization.
- A bounded, authorization-checked lexical pass now handles exact terms and identifiers alongside the existing vector index. This fixed the supplied failing travel-policy retrieval test.
- Unsupported scanned/empty extraction is rejected instead of appearing ready.

### Users, tasks, approvals and audit

- User department, role and supervisor references must belong to the same company; self-supervision is rejected.
- Email addresses are normalized, new passwords require at least 12 characters and clearance is bounded to L1–L4.
- The last active administrator cannot be demoted, deactivated or deleted.
- User create/update/status/delete operations now record audit events.
- Employees see only tasks assigned to or created by them unless their role grants task management.
- Assignment requires a task-assignment capability and an active same-company assignee.
- Approval statuses are an enum, rationale is required and requesters cannot review their own requests.
- Approval lists show a user's own requests unless the role grants review authority.
- Audit endpoints require the audit-view capability.
- The checksum endpoint no longer claims compliance or reports an empty log as verified; it states that deletion and reordering are outside its current scope.

### Frontend and deployment

- API requests use same-origin `/api`; Vite and nginx proxy to the backend.
- `204 No Content` is handled correctly and `401` clears the local session token.
- Login contains no prefilled demo credentials or quick-persona buttons.
- Initial setup is shown only when the backend reports that bootstrap is enabled and incomplete; the form sends the one-time setup token and the correct `company_name` contract.
- People creation requires an entered temporary password and separates role, document clearance and administrator permission.
- Upload UI separates classification from audience, sends the effective department/company scope and lists actual format/size constraints.
- Delete actions are shown only to the document owner or an administrator.
- The disconnected Test Center, which depended on the insecure demo identity API and presented scripted checks as proof, was removed.
- Root/backend/frontend ignore files, an environment template, nginx SPA/API configuration and safer Compose secret/service-network settings were added.
- README and the Windows launcher now describe the current product honestly and fail when required local setup is missing.

## Verification

| Check | Result |
|---|---|
| Backend pytest suite | 29 passed, 4 skipped, 140 warnings |
| PostgreSQL integration | Not run; no explicitly disposable PostgreSQL test service was available |
| Frontend TypeScript project build | Passed |
| Frontend Vite production build | Passed; 1,865 modules, 328.88 kB JS / 88.64 kB gzip |
| Frontend lint | 0 errors; legacy warnings remain and are tracked for cleanup/UI work |
| Docker Compose validation/runtime | Not run because Docker is not installed on this host |
| Live Ollama evaluation | Not run; simulator behavior was tested only when explicitly enabled |

The tests use isolated temporary SQLite, Chroma and upload locations. They do not touch the archived database or a company environment.

## Remaining risks before pilot

1. `AUTO_CREATE_SCHEMA` is transitional; Alembic migrations and an upgrade/rollback test are required.
2. Ingestion still runs synchronously and needs a durable job/outbox, retry, reconciliation and document versions.
3. The current hash-vector implementation remains unsuitable as the final semantic retriever. Model and embedding choices need corpus evaluation.
4. The agent orchestrator still contains unsupported vision/data/report paths and misleading trace/confidence wording; these should be quarantined/removed in the next scope-cleanup milestone.
5. Audit events are not yet an externally checkpointed append-only sequence.
6. Conversations are not persistent, source preview/download is incomplete, and the active UI still needs the planned professional redesign.
7. PostgreSQL, Compose, backup/restore, accessibility, network isolation and target-hardware performance are unverified.

## Next milestone

Implement a migration-backed document foundation: Alembic baseline, document versions, ingestion jobs/outbox, parser coverage states, index reconciliation, permission-filtered retrieval and exact source-location contracts. In parallel, remove unsupported agent routes and old disconnected pages after preserving any useful tests or behavior.
