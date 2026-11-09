# OracleX Milestone 03 · Offline deployment foundation

Implementation record · 18 September 2026

## Status

**Source implementation complete; target-host acceptance pending.**

OracleX now has a controlled offline release path, but Milestone 03 is not marked completed because the current Windows host has no Docker installation and the company has not supplied the deployment host profile or an approved redistributable model artifact. The clean disconnected-install and zero-outbound exit gates therefore remain open.

No later roadmap milestone was started.

Deliverable source archive: `OracleX-Milestone-03-Source.zip` · 130 source entries · 176,050 bytes · SHA-256 `fe827ac1472e1507efd0ccd7e4726bffe535bff60c699bc9d1d9ae0c7e14cfbf`.

## Implemented

### Deterministic dependencies and images

- Added a Linux/amd64 CPython 3.11 transitive lock containing 99 exact package versions and one verified SHA-256 wheel hash for each package.
- Verified that the complete locked wheelhouse can be resolved using only local files and `--require-hashes`.
- Pinned all direct npm dependencies to exact versions; `package-lock.json` remains the transitive integrity lock.
- Pinned PostgreSQL `15.15-alpine3.23`, Ollama `0.34.1`, Python `3.11.16-slim-bookworm` and nginx `1.29.6-alpine3.23`.
- Recorded the selected container manifest digests, source pages and licence families in `deployment/artifacts.lock.json`.
- Added a generated dependency inventory containing the resolved Python and npm versions, source locations and licence metadata.

### Offline runtime boundary

- Removed the `ollama-init` service and every runtime `ollama pull` command.
- Added `pull_policy: never` to every Compose service so a missing image stops with an error rather than contacting a registry.
- Placed PostgreSQL, Ollama, backend, frontend and model-import services on a Docker network with `internal: true`.
- Published only the configurable frontend port. PostgreSQL, Ollama and the API are not published to the host.
- Added read-only application containers, restricted writable tmpfs mounts and `no-new-privileges` where practical.
- Kept same-origin `/api` routing and made frontend address, port and exact CORS origins configurable for local or approved company-LAN use.

### Approved local model import

- Added an explicit local GGUF import service and operator command.
- The importer refuses to run without `model.gguf`, `model.sha256`, `MODEL-LICENSE.txt`, `model-source.json` and `Modelfile`.
- It verifies the model checksum before calling `ollama create` and rejects an implicit `latest` model tag.
- The release builder refuses to produce a complete release without the approved model records. `-ApplicationOnly` is available only for an intentionally incomplete engineering bundle and marks it incomplete.
- A reachable Ollama server without the configured model now reports `model_missing`; OracleX no longer selects an arbitrary installed model.

### Liveness, readiness and degraded operation

- `/health/live` reports the API process independently of dependencies.
- Internal `/health/ready` reports database connectivity, Alembic revision, upload/index storage, Chroma heartbeat, configured model and future worker state.
- Model absence returns an explicit degraded state when model availability is optional. Database, migration, storage or index failure returns `503`.
- `MODEL_REQUIRED_FOR_READINESS=true` allows company policy to require inference before the frontend starts.
- The simulator remains disabled in production and cannot turn a missing model into a live-inference claim.

### Offline packaging and operations

- The frontend production image uses only the compiled `dist` directory and pinned nginx. Node.js and npm are absent from the runtime image.
- The backend production image installs only from a local hash-verified wheelhouse while Docker build networking is disabled.
- The connected release builder pulls external images by recorded digest, builds application images with networking disabled, exports all runtime images, adds the approved model, generates a dependency inventory and hashes every release file.
- Added release verification, install, model import, start, stop, backup, restore, update, rollback, diagnostics and live outbound-denial scripts.
- Update and rollback preserve named data volumes. Rollback requires an explicit acknowledgement and matching backup.
- Removed unused Vite/React starter assets and replaced the starter frontend documentation.

## Validation performed

| Check | Result |
|---|---|
| Full backend suite | **38 passed, 4 PostgreSQL-only tests skipped** |
| Existing warnings | 140 dependency/deprecation warnings; no new failure |
| Offline/readiness/configuration subset | **10 passed** |
| Frontend clean install | `npm ci` installed 28 packages; audit reported 0 known vulnerabilities |
| Frontend lint | Passed with 0 warnings/errors |
| TypeScript and Vite build | Passed; 1,864 modules transformed |
| Production bundle | 323.15 kB JavaScript, 88.60 kB gzip; 10.89 kB CSS, 3.14 kB gzip |
| Linux wheel lock | 99 exact packages; local-only hash verification passed |
| Compose YAML | Parsed; five services on one internal network |
| Deployment scripts | All PowerShell files parsed; Python helper scripts compiled |
| Floating production tags / runtime model pull | Static scan found none |
| Live Docker/Compose | **Not run: Docker is unavailable on this host** |
| Approved model import and inference | **Not run: target hardware/model approval is required** |
| Clean disconnected installation | **Pending on a clean Linux/amd64 Docker host** |
| Browser/container/DNS traffic capture | **Pending target-host acceptance run** |

The skipped PostgreSQL tests require an explicitly disposable `POSTGRES_TEST_URL`. Existing warnings concern upstream TestClient/Chroma behavior, Pydantic v2 migration and naive UTC timestamps; they remain technical-debt work and do not change this milestone's test result.

## Required input to close the milestone

Provide the intended offline host's:

- operating system and CPU architecture;
- CPU model/core count;
- total RAM and RAM allocated to OracleX;
- GPU model and VRAM, or confirmation of CPU-only inference;
- free disk space available to application images, model, documents, indexes and backups; and
- acceptable response latency and expected simultaneous users.

The company must also approve one model source/licence for local redistribution. After that, the model can be selected, checksummed and added to the complete bundle.

## Target-host acceptance sequence

1. Build a complete release on a controlled connected Docker build host.
2. Transfer it through the company's approved media process and verify every checksum.
3. Install it on a clean Linux/amd64 Docker host while external networking is disabled.
4. Apply migrations, bootstrap the company and run sign-in, upload, search and ask.
5. Capture browser, backend, container and DNS traffic during those journeys.
6. Remove the configured model and confirm explicit degraded behavior with no simulator response.
7. Restart services and verify database, original-document, model and index persistence.
8. Corrupt a copied artifact and force a disposable migration failure; verify safe, actionable stops.
9. Exercise backup, update and rollback with non-production test data.

Milestone 03 can be marked completed only when this evidence passes and zero unintended outbound requests are observed.
