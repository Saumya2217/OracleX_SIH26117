# OracleX Milestone 04 · versioned document ingestion

Implemented in source · 18 September 2026

Source release version: **1.3.0**

## Outcome

OracleX now has a recoverable document lifecycle instead of a synchronous upload that could appear ready after partial work. Each upload creates a stable document record, an immutable version, a durable ingestion job and a transactional outbox event. A separate local worker validates, parses, indexes and verifies the version before making it current.

This milestone is **source-complete and locally verified**. It is not fully accepted for a company pilot because Docker is unavailable on this device and the four PostgreSQL integration tests remain skipped. Real container interruption, PostgreSQL concurrent claims, production-volume faults and clean-host recovery must still pass on the target deployment class.

## Implemented behavior

### Durable data and migration

- Added `document_versions`, `ingestion_jobs`, `outbox_events` and `service_heartbeats` through Alembic.
- Migrates existing document/chunk rows into version 1 and preserves the active-document compatibility fields.
- Added unique version numbers, content hashes, version/chunk keys and vector IDs.
- Migration upgrade, ORM drift check, downgrade and clean reapply pass on isolated SQLite.

### Upload and worker lifecycle

- Uploads stream to generated quarantine paths, enforce a 25 MB default limit and allowed extensions, and calculate SHA-256 while writing.
- The worker validates storage containment, size, checksum and PDF/XLSX/text signatures before parsing.
- PDF pages and tabular rows have configurable bounds. Invalid UTF-8 is rejected instead of silently dropping bytes.
- Jobs use leases, heartbeats, attempt limits, safe error codes/messages and exponential retry availability.
- Chunk/vector identifiers are stable per immutable version. Reprocessing first removes that version's prior partial chunks.
- A new version becomes current only after its SQL chunks and vector count are verified. A failed replacement leaves the previous ready version active.
- The production Compose stack includes a separate worker service, and readiness can require a recent worker heartbeat.

### Retrieval and authorization

- Direct search, the document agent and the data agent recheck the candidate document in SQL and require the candidate version to equal `current_version_id`.
- Lexical retrieval reads only current-version SQL chunks.
- Historical chunk inspection is limited to administrators or the document uploader; authorized readers can inspect the current version.
- The data agent no longer invents fallback telemetry when no authorized dataset is available.

### Recovery and retention

- Archive removes current vectors immediately and retains originals, SQL chunks and history.
- Restore rebuilds and verifies the current version index.
- Reconciliation reports missing originals, checksum drift, active index-count mismatch, stale non-current vectors and expired leases. Safe repair rebuilds or removes vectors and fails closed when the authoritative source is missing or changed.
- A command-line reconciliation entry point supports operator dry runs and repair. Restore invokes repair after the database and originals are restored.
- Backup now quiesces the frontend, API and worker so the database dump and originals form one recovery point.
- Permanent deletion is administrator-only and removes vectors, all contained version sources, generated document storage and SQL records.

### Professional document UI

- Replaced the card prototype with a compact document register showing classification, version, status, section count and update time.
- Added Active, My uploads and Archived views, authorized semantic search and live polling while jobs are running.
- Added a document record with processing status, immutable version history, extraction preview, safe failure reason, retry, replacement upload, archive, restore and permanent deletion.
- Uses opaque white/neutral surfaces, restrained blue actions, compact business typography and no gradients, glass, blur, glow, mascot or decorative AI treatment.
- The frontend uses real API states rather than fabricated processing progress.

## Verification performed on this device

| Check | Result |
|---|---|
| Full backend suite | **45 passed, 4 skipped**; skipped tests require disposable PostgreSQL |
| Dedicated versioned-ingestion tests | **7 passed** |
| Migration lifecycle | Upgrade, drift check, downgrade and reapply passed on SQLite |
| Frontend lint | **0 warnings, 0 errors** |
| TypeScript/Vite build | Passed; 1,864 modules; 328.87 kB JS and 20.82 kB CSS before gzip |
| Compose and operator scripts | YAML includes the worker; all PowerShell scripts parse cleanly |
| Live UI review | Sign-in, document register and version detail rendered against a seeded local backend at 762 px |

The dedicated failure/recovery coverage includes:

- replacement and supersession with old vectors removed;
- archive, restore and reconciliation rebuild;
- expired worker lease and idempotent retry without duplicate chunks;
- misleading PDF signature and invalid UTF-8 rejection;
- simulated vector-index outage with no false-ready state;
- document/version/job/outbox creation in the upload transaction; and
- current versus historical version authorization for a non-owner employee.

## Not completed or not provable on this device

- Docker image build, worker container execution and real container-kill recovery.
- PostgreSQL migration/locking behavior and multiple workers claiming jobs concurrently.
- A clean disconnected restore with real named volumes and a rebuilt Chroma index.
- Disk-full, filesystem read-only, permission-denied and host-crash fault injection.
- Simultaneous upload/archive/search load at representative company concurrency.
- Company-approved antivirus/content-disarm integration. The current `SCANNING` stage means containment, hash, size and file-signature validation; it does not claim malware detection.
- OCR for scanned PDFs and support for encrypted documents. Encrypted PDFs are intentionally rejected.
- Formal keyboard, screen-reader, focus-trap, contrast, zoom/reflow and browser-matrix accessibility acceptance.

Every unresolved item above is also tracked in `OracleX-Pre-Launch-Completion-and-Validation-Checklist.md` so it cannot be mistaken for completed work.

## Acceptance status and next phase

Milestone 04 meets its local source gate: no tested false-ready state, retry does not duplicate data, archived/superseded versions leave active retrieval, and failures are visible and recoverable. Full acceptance stays open until the target-host PostgreSQL, container restart, filesystem fault and recovery checks pass.

The next implementation phase is **Milestone 05 · evaluated retrieval and evidence**. It will build a permission-labelled evaluation corpus, compare local retrieval options, add exact immutable source locations, strengthen abstention and remove unsupported assistant behavior. A representative non-confidential company document/question set and the target host profile will materially improve that work.

## Downloadable source

`OracleX-Milestone-04-Source.zip` contains 136 selected source/configuration files and excludes virtual environments, dependency folders, compiled frontend output, databases, uploads, vector data, wheelhouse files, model binaries and secrets.

SHA-256: `7cd8586ff22733f5d389202f7885916fe6e82585503a71b9c992a87af8a78ac7`
