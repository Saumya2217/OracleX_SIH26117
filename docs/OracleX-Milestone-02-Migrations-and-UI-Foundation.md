# OracleX milestone 02 — migrations and UI foundation

Completed 18 September 2026 · Source snapshot included separately

## Outcome

OracleX now uses a tested Alembic schema baseline and has its first professional interface foundation. Production startup no longer creates database tables implicitly. The active UI uses opaque surfaces, restrained business styling, responsive navigation and truthful operational wording. The original submitted ZIP remains unchanged; all implementation work is in the clean source snapshot.

Do not load confidential company data yet. Durable ingestion jobs, document versions, restore drills, evaluated retrieval, persistent conversations, complete evidence/source preview and target-environment validation remain required before a company pilot.

## Database migration foundation

- Added Alembic as a backend dependency with configuration bound to the application's validated database URL.
- Added an initial migration covering companies, departments, roles, users, workflows, requests, audit events, documents, chunks, feedback and tasks, including foreign keys and indexes represented by the current ORM models.
- Removed runtime `create_all`; application startup no longer mutates the schema implicitly.
- Backend containers run `alembic upgrade head` before Uvicorn starts.
- The Windows launcher applies migrations and stops if the migration fails.
- Local setup documentation now requires an explicit migration before starting the API.
- Added a migration test that upgrades a fresh database, verifies all expected tables and the current revision, checks ORM/migration drift, downgrades to base and reapplies the history.

This is a fresh-install baseline. It is not an approved migration path for the archived demonstration database or an unknown populated database.

## Professional UI foundation

- Replaced the generic dark dashboard shell with a calm light business interface using opaque white/grey surfaces, clear dividers, restrained blue actions and system fonts.
- Removed the Google Fonts runtime request. The application can render without contacting a font CDN.
- Added a responsive sidebar drawer and compact mobile header; verified at a 390 × 844 viewport.
- Rebuilt sign-in with associated labels, browser autocomplete hints, a show/hide password control, a clear error region and a direct authorized-access message.
- Navigation now uses the actual administrator flag and role permissions. High document clearance no longer unlocks administrator UI.
- Renamed user-facing destinations to Overview, Documents, Ask OracleX, My work, Requests, People, Teams, Audit log and Settings.
- Removed Messages from navigation because it is not a complete backend-supported product flow.
- Replaced hardcoded “6 people” and “4 units” overview metrics with actual permission-scoped task, document and request counts.
- Corrected rejected-request rationale so it no longer records “Approved by”.
- Replaced the inaccurate sovereignty/compliance settings page with measured model availability, provider, engine, active model and installed-model status. It explicitly states the checks it does not perform.
- Removed every backdrop blur and retained plain dim dialog scrims.
- Added responsive overview grids, visible focus treatment and reduced-motion behavior.

## Scope cleanup and quality

- Removed eight unreachable or misleading prototype screens across the two milestones, including Test Center, Dashboard, Workbench, old workflow/adaptation/vault pages, Org Studio and Messages.
- Cleared frontend lint warnings, including stale imports, unsafe effect patterns and impure message identifiers.
- Async page loaders now ignore results after their component unmounts.
- Logout clears cached company, task, request, document and assistant-prompt state.

## Verification

| Check | Result |
|---|---|
| Backend pytest suite | 30 passed, 4 skipped, 140 dependency/deprecation warnings |
| Alembic lifecycle test | Upgrade, drift check, downgrade and reapply passed on isolated SQLite |
| PostgreSQL integration | Not run; no explicitly disposable PostgreSQL service was available |
| Frontend TypeScript build | Passed |
| Frontend lint | Passed with zero warnings and zero errors |
| Frontend Vite production build | Passed; 1,864 modules, 323.15 kB JS / 88.60 kB gzip |
| Visual QA | Sign-in and authenticated overview checked at desktop size; sign-in, overview and navigation drawer checked at 390 × 844 |
| Docker Compose runtime | Not run because Docker is not installed on this host |
| Live Ollama evaluation | Not run; model-unavailable and explicit demo-simulator behavior are covered, but no live model quality claim is made |

Latest source archive: `OracleX-Milestone-02-Source.zip` · 106 files · 161,376 bytes · SHA-256 `f0ebed18411edde2aeb191715af6911d76a14d2d3ea432e3051fc578f2622593`.

Tests use isolated SQLite, Chroma and upload locations. Visual QA used a disposable migrated and seeded local database under the work directory. No archived project data or company environment was modified.

## Remaining priorities before pilot

1. Add document versions, immutable original metadata, archive/restore and retention policy behavior.
2. Move upload parsing/indexing to durable jobs with retry, idempotency, reconciliation and administrator-visible failures.
3. Replace the current retrieval baseline only after corpus-specific evaluation; implement exact page/section highlighting and permission-checked downloads.
4. Remove or redesign unsupported vision/data/report routes, reasoning traces and uncalibrated confidence fields.
5. Add persistent conversations and structured request previews with explicit reviewer reasons and concurrency handling.
6. Complete the Documents, Requests, People and Ask OracleX page redesigns using dense tables and evidence panels.
7. Run PostgreSQL, Docker, backup/restore, WCAG 2.2 AA, network isolation and capacity checks on the intended company hardware.

## Recommended next build slice

Implement versioned document ingestion as the next vertical slice: SQL version/job tables and migrations, upload-to-job transaction, background worker, retry/reconciliation, version-aware vector identifiers, archive/restore, status UI and end-to-end tests. This resolves the largest data-integrity risk before expanding assistant features.
