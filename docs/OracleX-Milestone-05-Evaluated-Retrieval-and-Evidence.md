# OracleX Milestone 05 · evaluated retrieval and evidence

Implemented in source · 18 September 2026

Source release version: **1.4.0**

## Outcome

OracleX now answers company questions through an explicit evidence contract. Retrieval starts from current indexed SQL chunks, applies the requesting user's company, department and clearance rules, combines lexical and local vector rank, and retains only candidates close to the strongest lexical match. Questions without relevant authorized evidence abstain.

Every supported response identifies the immutable document version and chunk, includes an exact page, section or table location where the parser can provide it, shows an excerpt, and offers a retained-source download that repeats authorization and SHA-256 integrity checks. The product also states whether text came from a configured local model, a labelled extractive fallback, an explicitly enabled demo simulator, or no generation at all.

This milestone is **source-complete and locally verified**. It is not fully accepted for a company pilot. The included evaluation uses 20 synthetic NovaWorks cases, not an approved representative company corpus or separate holdout. No approved semantic embedding or language model was available on this device, and generated-claim fidelity has not been measured on real company documents.

## Implemented behavior

### Retrieval and evaluation

- Added lexical, vector and hybrid retrieval modes over authorized current-version chunks.
- Hybrid retrieval uses reciprocal-rank ordering only among candidates that pass lexical relevance; it does not treat an unrelated vector neighbour as evidence.
- Added aliases and normalized tokens for the bounded development vocabulary plus a relative relevance floor that removes weak trailing sources.
- Added a frozen, permission-labelled 20-case development set with 14 answerable cases, three unsupported questions and three permission/cross-department cases.
- Added a reproducible offline evaluation command and machine-readable report comparing all three modes.
- Document versions record `embedding_model` and `embedding_dimensions` through an Alembic migration and expose them in the document record UI.

### Evidence contract

- Replaced `primary_agent`, answer `confidence` and `reasoning_trace` fields with `evidence_status`, `generation_mode`, `model_id`, `retrieval_mode` and exact citations.
- Citations include document ID, immutable version ID, chunk ID/index, filename/title, page/section/sheet/row location, excerpt and permission-checked source path.
- Prompt assembly includes only authorized current-version evidence and records cited version IDs in the audit event.
- Unsupported image requests return `UNSUPPORTED_INPUT`; unsupported company questions return `INSUFFICIENT_EVIDENCE`; restricted-topic guards return `ACCESS_DENIED`.
- When the local model is unavailable, supported queries return a visibly labelled extractive answer. Production does not silently enable the demo simulator.
- Removed the fixed vision agent, unsupported report agent, fabricated visual citation, invented data telemetry and ungrounded generic-answer fallback.

### Source authorization and integrity

- Added current and historical retained-source download rules. Administrators or the document uploader may inspect authorized history; ordinary readers may download only the active indexed version.
- Rechecks company ownership, department/clearance authorization, storage-root containment, file existence and content SHA-256 before serving a source.
- Records source reads in the audit log.
- Added regression coverage for restricted-source denial, historical-source denial and tampered retained-source rejection.

### Professional evidence UI

- Assistant answers show a restrained evidence-status badge, generation label, exact source/version location, excerpt and source download.
- Document version history shows the embedding implementation and dimensions used for that version.
- The UI uses opaque neutral surfaces, restrained blue actions and compact business typography. It has no glassmorphism, gradient, blur, glow, mascot or decorative AI treatment.
- A live local review at the available 762 px viewport verified a supported confidential-budget response and an unsupported dental-benefit abstention.

## Development evaluation result

The full result and every case are in `OracleX-Milestone-05-Retrieval-Evaluation.json`.

| Mode | Answerable recall@5 | Abstention accuracy | Access-control accuracy | Passed cases |
|---|---:|---:|---:|---:|
| Lexical | 100% | 100% | 100% | 20/20 |
| Deterministic vector only | 100% | 0% | 100% | 14/20 |
| Hybrid with lexical relevance gate | 100% | 100% | 100% | 20/20 |

The vector-only result demonstrates why nearest neighbours cannot be treated as evidence without a relevance/abstention gate. The perfect lexical and hybrid figures reflect a small synthetic fixture set and must not be generalized to company documents, model quality or factual correctness.

## Verification performed on this device

| Check | Result |
|---|---|
| Full backend suite | **53 passed, 4 skipped**; skipped checks require a disposable PostgreSQL service |
| Focused retrieval/agent/evidence suite | **10 passed** after the final relevance refinement |
| Migration lifecycle | Upgrade through the M05 revision, ORM drift check, downgrade and clean reapply passed on isolated SQLite |
| Retrieval evaluation | 20/20 hybrid cases passed the synthetic development gates |
| Offline fallback | Model-unavailable query returned a labelled extractive answer with exact citations |
| Source authorization/integrity | Current/historical access, restricted clearance and tampered-file behavior passed |
| Frontend lint | **0 warnings, 0 errors** |
| TypeScript/Vite build | Passed; 1,864 modules; 330.33 kB JavaScript (91.35 kB gzip) and 22.33 kB CSS (5.28 kB gzip) |
| Deployment static validation | All PowerShell scripts parsed; artifact JSON and Compose YAML parsed |
| Live UI review | Supported-evidence and insufficient-evidence states rendered correctly at 762 px against the seeded local backend |

The backend run reported 154 known dependency/deprecation warnings. They concern the Starlette TestClient transition, a future Chroma configuration requirement, Pydantic v2 class configuration and naive UTC timestamps; they remain tracked technical debt.

## Not completed or not provable on this device

- Approved representative company corpus, separate holdout and labelled conflicting, superseded, adversarial and prompt-injection cases.
- Comparison of legally approved semantic embedding candidates on representative CPU/GPU hardware.
- Live approved Ollama model quality, material-claim citation fidelity, latency, memory, concurrency and thermal measurements.
- Conflict detection and presentation when two current authorized sources disagree.
- Exact in-document highlighting or anchored preview. The UI currently shows the exact location label and excerpt and downloads the verified retained source.
- PostgreSQL/container authorization and concurrency checks; the four PostgreSQL tests remain skipped because no disposable service is available here.
- Clean disconnected installation, outbound-traffic capture, backup/restore and full index rebuild on the target deployment class.
- Formal keyboard, screen-reader, focus, contrast, zoom/reflow and browser-matrix accessibility acceptance.

Every unresolved item is retained in `OracleX-Pre-Launch-Completion-and-Validation-Checklist.md`.

## Acceptance status and next phase

Milestone 05 meets its local source gate: the synthetic benchmark is frozen and reproducible, unsupported questions abstain, inaccessible versions do not appear, exact immutable citations are returned, source downloads fail closed, and generation mode is explicit. Pilot acceptance stays open until the approved company corpus, holdout, model/embedding comparison, claim-fidelity review and target-host checks pass.

The next implementation phase is **Milestone 06 · persistent assistant and accountable requests**. It will persist owned/classified conversations and agent runs, store immutable citation records, replace generic approval payloads with typed versioned requests, separate decisions from fulfillment, and add concurrency-safe review behavior.

## Downloadable source

`OracleX-Milestone-05-Source.zip` contains 142 selected source/configuration files and excludes virtual environments, dependency folders, compiled frontend output, databases, uploads, vector data, wheelhouse files, model binaries and secrets.

SHA-256: `3ba4470603104539f096401a79f519ae7889419ada0b661419a98789497058dc`
