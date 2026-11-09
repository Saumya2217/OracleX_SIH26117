# OracleX offline deployment

## Deployment contract

The release is built on an internet-connected, controlled build host and installed on a Linux/amd64 Docker host with networking disabled or denied by policy. The production host needs Docker Engine with Compose v2 and PowerShell 7. It does not need Python, Node.js or package registries.

Only the frontend port is published. PostgreSQL, Ollama, Chroma, the API and the durable ingestion worker share the `private` Docker network, which has `internal: true`. Normal runtime has no internet-facing Docker network and no download command.

The `chroma` service is the sole owner of the existing `backend_chroma` volume. It reuses the pinned backend application image and its locked Chroma dependency. API and worker use `CHROMA_HOST=chroma`; they no longer mount that volume. Do not run embedded Chroma clients against the server's directory. The unauthenticated Chroma port must stay private. Server mode follows [Chroma's client/server guidance](https://docs.trychroma.com/production/chroma-server/client-server-mode).

For an existing development/pilot stack, back up SQL and originals, stop API/worker before switching modes, retain the volume and start Chroma as its only owner. Run reconciliation and a replacement/search smoke check before restarting normal use. Never start a second owner of the same directory. The revised Compose service, container restart, volume migration and backup/restore flow still require target-host Docker verification.

## Model approval inputs

Model selection cannot be made safely without the deployment host profile. Record:

- CPU architecture and core count.
- RAM available to OracleX under expected concurrency.
- GPU model, VRAM and approved container/runtime support, or explicitly record CPU-only.
- Free storage for release images, model, database, originals, indexes and backups.
- Required first-token and complete-answer latency.
- Model licence, redistribution permission and security/legal approval owner.

Populate `model/model-source.json` from the example and add `MODEL-LICENSE.txt`, `model.gguf` and `model.sha256`. The release builder verifies the checksum before it builds a complete bundle. The runtime importer verifies it again.

## Build a complete release

Run `scripts/build-release.ps1` from the repository on the connected build host. It:

1. Uses `npm ci` and produces the compiled frontend.
2. downloads Linux/amd64 Python wheels from the hash-locked dependency set;
3. pulls base/runtime images by recorded digest;
4. builds the application images with Docker networking disabled;
5. exports every runtime image to one archive;
6. inventories Python and npm dependency sources/licences;
7. copies the approved model and operator scripts; and
8. hashes every file in `SHA256SUMS` and verifies the result.

Docker is absent from the current development machine, so the checked-in implementation can be statically tested here but the full image export and disconnected-host proof must run on the designated build/test hosts.

## Install and operate

From a transferred complete release:

```powershell
.\deployment\scripts\verify-release.ps1
.\deployment\scripts\install.ps1
.\deployment\scripts\diagnostics.ps1
.\deployment\scripts\test-network-isolation.ps1
```

`install.ps1` loads the saved images, starts PostgreSQL and Ollama, imports the approved local model, applies migrations and starts OracleX. It never invokes a registry or package manager.

Daily commands:

```powershell
.\deployment\scripts\start.ps1
.\deployment\scripts\stop.ps1
.\deployment\scripts\backup.ps1
```

Backups briefly stop the frontend, API and ingestion worker so the PostgreSQL dump and uploaded originals form one recovery point, then restart the stack. The Chroma index is derived data: restore runs the reconciliation command to rebuild missing active-version entries from the SQL chunks and retained originals. Store backups on approved encrypted media outside the application host.

Document ingestion is asynchronous. The API commits a document version, job and outbox record together, while the `worker` service validates, parses, indexes and verifies the new version. `/health/ready` requires a recent worker heartbeat. Operators can run a dry check or safe index repair inside the backend image:

```powershell
docker compose exec -T backend python -m app.workers.reconcile
docker compose exec -T backend python -m app.workers.reconcile --repair
```

Updates require a verified complete release and create a pre-update backup:

```powershell
.\deployment\scripts\update.ps1 -NewReleaseDirectory D:\Releases\OracleX-1.5.0
```

Rollback requires the previous release and its matching pre-update backup:

```powershell
.\deployment\scripts\rollback.ps1 `
  -PreviousReleaseDirectory D:\Releases\OracleX-1.2.0 `
  -BackupDirectory D:\Backups\pre-update-YYYYMMDD-HHMMSSZ `
  -Confirmation ROLLBACK-ORACLEX
```

The scripts never use `docker compose down --volumes`; named data volumes survive stop, update and image replacement.

## Required target-host evidence

Before marking this milestone complete, retain:

- The complete release manifest, checksum verification output and approved model record.
- A clean disconnected install transcript.
- Browser developer-tools network export for sign-in, upload, search and ask.
- Container/DNS capture showing no unintended outbound request.
- Readiness output with the model present and with it deliberately absent.
- Restart/persistence results for database, originals, model and index.
- A deliberately failed checksum and migration test showing an actionable safe stop.
- Backup, update and rollback transcripts using non-production test data.

