# OracleX

OracleX is being rebuilt as a private company document workspace with evidence-backed assistance. This snapshot includes the security foundation, migration baseline, professional UI foundation, offline deployment tooling, versioned ingestion, evaluated evidence, persistent conversations and accountable typed requests. It is not ready for confidential production data yet.

Milestone 07 is in progress. Start with the [roadmap](docs/OracleX-Roadmap-and-Implementation-Plan.md), [unfinished-work and pre-launch checklist](docs/OracleX-Pre-Launch-Completion-and-Validation-Checklist.md), and [verification record](docs/OracleX-Verification-Record.md). The [documentation index](docs/README.md) links the implementation and design reports.

## Current milestone

Implemented:

- Authentication fails closed; protected APIs return `401` without a valid active-user token.
- Administrative authority comes from the admin capability, not clearance level.
- Demo identity switching, database seeding and automatic demo fixtures are absent unless `DEMO_MODE=true` is deliberately configured.
- First-company setup requires a one-time setup token and is disabled after one company exists.
- JWT and database secrets have no usable built-in defaults.
- Production CORS rejects wildcard origins.
- The frontend uses same-origin `/api`; Vite and nginx proxy it to the backend.
- Uploads use generated contained paths, bounded streaming, an allowlist, duplicate hashes, explicit audience and capability checks.
- Search candidates are rechecked against current SQL document state and authorization.
- Audit access, task ownership, approval decisions and user relationships use explicit server-side permission checks.
- Self-approval, arbitrary approval states and removal of the final active administrator are blocked.
- The model simulator is off by default and cannot silently replace unavailable inference.
- Alembic owns schema creation. The initial migration is tested for upgrade, metadata drift, rollback and clean reapplication.
- Container and Windows development startup apply migrations before starting the API.
- The active UI now uses an opaque, responsive business interface with a light visual system, accessible sign-in controls and no external font request, gradients, blur or glass effects.
- Navigation follows actual capabilities instead of treating document clearance as administrator authority.
- Fabricated overview counts and the misleading system/compliance dashboard were removed.
- Disconnected prototype pages and their obsolete demo surfaces were removed.
- Production container and direct frontend dependency versions are pinned. Python has a transitive hash lock and the release builder creates a verified Linux wheelhouse.
- Runtime Compose uses an internal Docker network, contains no package/model download step and exposes only the configured frontend address.
- A complete release imports a checksum-verified, licence-recorded local GGUF through an explicit operator command.
- Liveness and readiness are separate. Readiness reports database, migration, storage, index, model and worker state, and reports a missing model as degraded instead of simulating an answer.
- Release tooling builds compiled frontend and application images on a connected build host, exports all runtime images, records dependency sources/licences and writes a checksum manifest.
- Install, start, stop, model import, backup, restore, update, rollback, diagnostics and live outbound-denial scripts are included under `deployment/scripts`.
- Uploads create immutable document versions and durable ingestion jobs. A separate worker uses leases, bounded retries, stable vector IDs and verified index counts before atomically activating a new version.
- Failed replacement versions never displace the last ready version. Archive removes active vectors, restore rebuilds them, and reconciliation detects missing sources, checksum drift, missing vectors and stale-version vectors.
- The document register shows processing states, version history, safe errors, retry controls, archive/restore and an administrator-only permanent-delete action.
- API and ingestion worker connect to one private Chroma server. Production rejects embedded storage, and the standalone worker refuses to share an embedded directory. Search outages return an explicit 503.
- Assistant retrieval uses authorized current-version SQL records with lexical/vector rank fusion and an explicit relevance gate.
- Answers return evidence status, generation mode, immutable document/version/chunk identifiers, exact page/section/table locations and permission-checked retained-source downloads.
- Unsupported image analysis is rejected explicitly; ungrounded questions abstain; unavailable local inference falls back to a visibly labelled extractive answer.
- A 20-case synthetic permission-labelled development benchmark compares lexical, vector and hybrid modes. Hybrid passed the development gates; a representative approved company corpus remains required for pilot acceptance.
- Document versions record the embedding implementation and dimensions used to build their index entries.
- Assistant conversations, messages, runs and exact citation snapshots persist with owner/company boundaries, classification, archived state, safe failure records and source-access rechecks.
- Every assistant run records its prompt version, generation/retrieval mode, model identifier and exact source-version identifiers without exposing hidden reasoning or invented confidence.
- Controlled change, access and purchase requests use validated typed fields, immutable versions, exact submitted-version decisions and optimistic locking.
- Requester and reviewer actions are separated: approval never claims fulfillment, reviewer reasons are required, self-review is blocked and recipient notifications use request deep links.
- Ask OracleX and Requests now use persistent, responsive, opaque business interfaces with conversation history, evidence, draft editing, review controls and a readable timeline.
- Requests block submission while draft edits are unsaved, expose owner cancellation with a reason, and provide explicit conflict/reload and unavailable-record states. Review controls respect assignment; approval and recorded completion remain separate. Invalid typed request fields return safe field errors without creating or changing a saved version.
- Notifications has recipient-scoped All/Unread views, explicit mark-as-read, safe local request links, cursor pagination and retry states.
- New and editable drafts support an eligible company reviewer or the unassigned queue. Reviewer changes are saved in immutable versions. Reassignment is limited to the assigned reviewer or an authorized administrator, preserves the submitted version, and records timeline/recipient notifications. Submission rechecks reviewer eligibility.
- Unsaved request fields and notes stay in a company/user-scoped memory buffer across workspace/history navigation, with resume/discard controls and a sign-out confirmation. Save a backend draft for persistent fields: accepted reloads, crashes and process loss discard the memory buffer. Native reload/close warnings still require supported-browser acceptance testing.

Still planned before a company pilot:

- Company-corpus evaluation of approved semantic embeddings, generated-claim citation fidelity and exact in-document source highlighting.
- Complete accessibility, responsive error/state coverage and staff acceptance of the professional pages and path-based routes.
- Target-host model selection, disconnected installation, browser traffic capture, PostgreSQL/container, accessibility and capacity verification.

## Offline release workflow

OracleX uses a connected build host and a disconnected runtime host. The runtime host does not run `pip`, `npm`, `apt`, `apk` or `ollama pull`.

1. Record the target host CPU, RAM, GPU, free storage and acceptable response latency.
2. Obtain legal/security approval for one GGUF model. Put the model, checksum, licence, source record and `Modelfile` in `deployment/model` as described there.
3. On a connected Windows build host with Docker, Python and Node.js, run:

   ```powershell
   .\deployment\scripts\build-release.ps1
   ```

4. Transfer the generated `deployment/release/OracleX-1.5.0` directory through the company's approved media process.
5. On the disconnected host, verify and install:

   ```powershell
   .\deployment\scripts\verify-release.ps1
   .\deployment\scripts\install.ps1
   ```

The first install creates `.env` and stops if configuration is absent. Replace all placeholders, choose an exact browser origin and rerun it. `ORACLEX_HTTP_BIND=127.0.0.1` keeps access local; use an approved LAN interface only when company users must connect from other devices. Normal runtime startup is `start.ps1`; it never downloads a package or model.

The release builder requires an approved model by default. `-ApplicationOnly` produces an intentionally incomplete engineering bundle and marks it incomplete in `release-manifest.json`; it cannot satisfy the disconnected-install exit gate.

Detailed build, verification, update and recovery steps are in [deployment/README.md](deployment/README.md).

## Local setup

Requirements for source development: Python 3.11 or 3.12, Node.js 20.19+ or 22.12+, and a local PostgreSQL/Ollama installation if those services are being exercised. Local verification used Python 3.12; the offline container build targets Python 3.11.

1. Copy `.env.example` to `.env` at the project root.
2. Generate independent random values for `SECRET_KEY`, `BOOTSTRAP_TOKEN` and `POSTGRES_PASSWORD`.
3. For native development, replace container addresses with local ones: set `CHROMA_HOST=127.0.0.1`, `CHROMA_PORT=8001`, a local `DATABASE_URL`, and local writable `UPLOAD_DIR`/`CHROMA_PERSIST_DIR`. Set `BOOTSTRAP_ENABLED=true` only for initial company setup. Disable it afterward.
4. Install backend dependencies in a new virtual environment:

   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.in
   .\.venv\Scripts\chroma.exe run --host 127.0.0.1 --port 8001 --path ./data/chromadb
   ```

   Keep Chroma running. In separate backend terminals, migrate/start the API and then start the ingestion worker:

   ```powershell
   .\.venv\Scripts\python.exe -m alembic upgrade head
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   # Separate terminal:
   .\.venv\Scripts\python.exe -m app.workers.ingestion
   ```

5. In another terminal, run the frontend:

   ```powershell
   cd frontend
   npm ci
   npm run dev
   ```

The Vite development server proxies `/api` to `http://127.0.0.1:8000`. The container nginx configuration proxies `/api` to the backend service.

`requirements.in` is the connected cross-platform development input. Production uses the checked-in Linux/amd64 `requirements.lock`, whose exact wheel hashes are verified when the release builder creates the wheelhouse.

Do not enable `DEMO_MODE` or `SIMULATED_AI_FALLBACK` in a company deployment. Do not use the archived database, seeded users or bundled dependency directories.

## First setup

When the database has no company and `BOOTSTRAP_ENABLED=true`, the sign-in page offers company setup. Enter the configured one-time setup token. The setup endpoint rejects missing/wrong tokens and returns `409` after the company exists.

After setup:

1. Set `BOOTSTRAP_ENABLED=false`.
2. Restart the backend.
3. Store the setup token outside the runtime environment or rotate/remove it according to company policy.

## Tests

From `backend`:

```powershell
python -m pytest -q
```

The default suite uses isolated SQLite, Chroma and upload locations. PostgreSQL integration tests are skipped unless `POSTGRES_TEST_URL` points to an explicitly disposable database.

From `frontend`:

```powershell
npm ci
npm run test:state
npm run lint
npm run build
```

Check generated API types from `backend` with `python scripts/generate_frontend_types.py --check`.

The [verification record](docs/OracleX-Verification-Record.md) separates fresh automated checks from earlier synthetic browser checks and unrun target-host gates. This is development verification, not a production security or compliance certification.

## Production configuration notes

- Keep PostgreSQL, Chroma and Ollama on a private service network. Chroma has no published port; do not expose its unauthenticated API to company clients or the internet.
- Terminate HTTPS at the approved company ingress and configure exact `ALLOWED_ORIGINS`.
- Use a secret manager or protected deployment environment rather than committing `.env`.
- Apply migrations with `python -m alembic upgrade head` before every application rollout. Back up a populated database before upgrading it.
- Back up SQL records and original documents. The Chroma index is rebuildable and should not be the only copy of knowledge.
- A document answer is decision support. Users must be able to open the exact cited source; high-impact decisions require qualified review.
- The internal `/health/live` endpoint reports only the API process. Internal `/health/ready` reports each dependency and can return `degraded` with HTTP 200 when the optional local model is absent, leaving safe administrative functions available. The operator diagnostics command captures readiness without publishing it through nginx.
- Set `MODEL_REQUIRED_FOR_READINESS=true` only when company policy requires model availability before the frontend starts.

