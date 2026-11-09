# OracleX verification record

Prepared and updated 10 November 2026 · Original audit plus current implementation verification

## Current implementation verification

The source has now changed through Milestones 01–06 and nine focused Milestone 07 batches. The sections below titled “Source handling”, “Frontend checks”, “Backend test run” and “Isolated behavioral probes” preserve the original-archive audit evidence that motivated the roadmap; they are historical and must not be read as the current implementation state.

Current verified results:

| Check | Result |
|---|---|
| Complete backend suite, 10 November | 82 passed, 5 PostgreSQL-only tests skipped, 497 warnings |
| Earlier seventh-batch focused request regression | 6 passed, 100 warnings; includes extra assigned-reviewer denial and friendly currency-message assertions after the full run |
| Earlier focused index/config/deployment regression | 9 passed, 44 warnings; private single-server topology, production configuration, worker guard, safe 503 and client routing |
| Earlier focused accountable-request tests | 2 passed, 81 warnings |
| Current frontend state/field/error/capability tests | 18 passed: includes scoped draft buffers, immutable snapshots, late-write preservation, zero values, safe local notification links and UTC timestamps |
| Current generated OpenAPI drift check | Passed; 60 schemas. Shared frontend response names alias generated types; optional fields are handled explicitly. |
| Offline/readiness/configuration subset | 10 passed |
| Alembic lifecycle after Milestone 02 | Upgrade, drift check, downgrade and reapply passed on isolated SQLite |
| Frontend dependency install | `npm ci` passed; 28 packages; npm audit reported 0 known vulnerabilities |
| Frontend lint | Passed with 0 warnings/errors |
| TypeScript and Vite build | Passed; 1,883 modules; 362.79 kB JavaScript (104.12 kB gzip) and 54.22 kB CSS (10.45 kB gzip) |
| Ninth-batch request browser checks, 20 October | Access version 1 selected-reviewer submission, reassignment to Hetvi, rejection/read-back; controlled-change reviewer edit saved as version 2, exact-version approval and separate QA completion; Submitted/Assigned owner cancellation; reviewer lookup outage/retry and selected 390/768/1440 form widths. Synthetic SQLite only; no real access grant or process change. |
| Publication checks, 10 November | 18 frontend tests, lint/build and 60-schema drift passed. Full backend result above is a fresh run. Browser evidence remains dated 20 October. |
| Earlier live local UI review | On 12 October, synthetic employee/admin sign-in and protected-route redirect; request, conversation and document-version deep links; extractive answer/citation; selected 390, 768 and 1440 CSS-pixel layouts; no page-width overflow on checked views |
| Eighth-batch inbox browser checks | Arya: 25 then 30 own records, no other recipient's QA item; page-tail read removal with older page retained; refresh persisted read state; unsafe deep_link ignored. Krish: only his record, failed mark stayed unread during API outage, retry/read/empty Unread recovered. |
| Eighth-batch draft browser checks | New text and zero recovered after sidebar/Back; fields and unsent cancellation note recovered for a saved draft; second-view version 3 caused recovered version-2 fields to block writes. Sign-out Keep working/Escape retained text, explicit discard cleared it and Escape returned focus. Selected inbox/pending-header widths equaled 390/768/1440 viewports. |
| Native unload / durable unsaved recovery | Not verified: automated reload exposed no beforeunload dialog and lost memory-only text. Browser-native warning remains a manual gate; accepted reload/crash/session recovery is unsupported unless fields were saved as a backend draft. |
| Live request handoff, seventh batch | Synthetic Arya purchase draft at zero cost; dirty submission blocked; two-view conflict/reload; submitted version 3; Ashutosh claim/approval followed by separate QA completion; requester saw both records. Two cancellation fixtures retained reasons. Krish received a private-record 404 without content. API interruption/retry, fresh history reads and register reconciliation observed. Selected completed-record/final-header widths matched 390/768/1440 viewports. |
| Live administrator ingestion, 20 October | Synthetic upload and three versions; separate worker with inline ingestion disabled; deliberate missing-source failure restored then retried; previous version retained; detail/preview refreshed automatically. Shared-server version 3 was searchable through the already-running API. Chroma stop/restart gave an explicit error and recovered on retry. Empty-upload feedback/focus and Escape return observed. |
| Live Audit review, 13 October | Synthetic administrator sign-in, filter, details and checksum message observed. Twenty-five of 27 labeled synthetic QA events loaded first; “Load more” produced all 27 with no duplicate resource IDs. No page-width overflow at 390/768/1440 CSS pixels, including expanded details at 390. |
| Live setup review, 13 October | Fresh empty migrated SQLite fixture exposed the first-company form; labels and layout inspected at 390/768/1440 CSS pixels, with no page-width overflow at 390/768. No administrator account was created. |
| Current selected keyboard paths | Employee mobile navigation/skip link, request/upload/document modals; reviewer reason/approval; administrator dialogs. Focus loops, inert backgrounds, Escape/return and action-removal heading focus observed. Complete pilot journeys remain open. |
| Earlier synthetic request lifecycle, 13 October | Keyboard-created purchase draft retained a cleared quantity and zero cost; employee saved/submitted version 2 and separate reviewer approved that version. No real purchase occurred. |
| Document route regression | Extracted preview now loads and closing returns focus to the record opener. Browser back/forward reopens/closes detail after retaining the register instance. |
| Selected contrast | People direct-text/solid-background spot check: 1 failure among 64 elements before correction; the same check passed afterward. Full text/non-text contrast remains open. |
| True zoom and screen-reader pass | Unverified. The in-app browser zoom shortcut did not change stable viewport/pixel ratio; no true 200% zoom or screen-reader speech/navigation pass was established. |
| Live API-interruption checks | History/register/directory failures observed with the disposable API stopped. Task, assignee and mobile-history retries recovered after restart; failed archive kept the saved conversation visible. Document failed reads showed unavailable counts. This was an API outage, not a disconnected-host/air-gap test. |
| Live retained-source download | 1,575-byte synthetic handbook downloaded from the saved citation; SHA-256 matched a retained version in the disposable fixture. |
| Mobile saved-conversation controls | Selector and retry available below 720 CSS pixels. Saved record opened at 390 pixels; long-title Archive control stayed visible and page width equaled viewport width at 390/768/1440. |
| Milestone 06 schema repair | Earlier stamped SQLite fixture upgraded through the new conditional migration; two targeted migration tests passed |
| Versioned ingestion recovery | Replacement/supersession, misleading signature, invalid UTF-8, vector outage, expired lease, idempotent retry, archive/restore, reconciliation repair and historical-version authorization passed |
| M05 retrieval evaluation | Frozen 20-case synthetic set: lexical 20/20, vector-only 14/20 due to 0% abstention, hybrid 20/20; representative company holdout remains pending |
| M05 evidence/source contract | Exact version/chunk/location citations, explicit generation modes, offline extractive fallback, restricted/historical source denial and retained-file integrity rejection passed |
| M06 persistent conversations | Owner isolation, ordered history, bounded follow-up context, archived-state enforcement, saved failures and citation redaction after access revocation passed |
| M06 accountable requests | Typed validation, immutable versions, exact submitted-version decisions, self-review denial, stale writes, notification scope and once-only fulfillment passed locally |
| Linux/amd64 Python lock | 99 exact packages; local-only wheel resolution and SHA-256 verification passed |
| Offline deployment configuration | Compose YAML parsed; production tags pinned; `pull_policy: never`; internal runtime network; no runtime model pull |
| Operator tooling | 14 PowerShell scripts, including native startup, parsed on 20 October; revised Compose YAML and sole index-owner topology passed static checks. Native launcher/container execution remains open. Earlier Python release helpers compiled. |
| Live Docker/Compose and process-restart persistence | Not run because Docker is unavailable on the current host |
| Clean disconnected install / traffic capture | Pending target hardware and approved model artifact |

The current implementation evidence and open exit gates are detailed in `OracleX-Milestone-07-Professional-UI-Progress.md`, the Milestone 05 retrieval records and the pre-launch checklist.

The seventh batch initially exposed a currency-payload 500, a nullable error-state build failure and a stale register row after a fresh history read. Each was corrected; final checks above passed. UI/browser evidence used disposable SQLite records and sequential role sign-ins, not target PostgreSQL or independent company sessions. The eighth batch completes selected inbox and workspace/history draft recovery checks. It adds three backend pagination/scope tests and six frontend buffer/link/time tests. The first native sign-out confirmation could not be reliably controlled by the automated browser; it was replaced by a shared in-app dialog and the replacement was checked. Native unload warnings, durable/session recovery and the full role/state matrix remain open in the pre-launch checklist.

## Source handling

- Reviewed archive: `OracleX-AI.zip`, 203,615,176 bytes, 24,566 ZIP entries.
- Archive SHA-256: `38dafbbe9eed4cc9462b74c1313b10dda67555e3f118383dcf0e1527083d77da`.
- The archive was extracted to a separate review directory. The supplied virtual environment, dependency directories and binary indexes were inventoried but were not treated as first-party source.
- After review/build activity, 96 selected first-party files from the application, tests, manifests and root configuration were byte-compared with the ZIP. No selected file was missing or changed.
- Builds, test databases, vector data, uploads, probes, logs and UI screenshots were written only under the separate `work` review area.

## Frontend checks

| Check | Result | Interpretation |
|---|---|---|
| TypeScript project build, `tsc -b` | Passed | The archived frontend source type-checks under its bundled dependency set. |
| Vite production build | Passed | 1,865 modules; generated JavaScript 327.75 kB (88.50 kB gzip), CSS 4.12 kB (1.31 kB gzip). |
| Oxc lint | 0 errors, 91 warnings | The build is not a clean quality signal; warnings include maintainability issues and were reviewed separately. |
| Current UI render | Completed with synthetic API fixtures | This verifies rendering only, not a live backend or real company data. |
| Proposed UI concept | Navigation, filtering, document detail, source interaction and local approval preview exercised | No console/page errors in the scripted run. No horizontal overflow at 1024, 768, 390 or 320 px in the tested concept states. |

Visual inspection confirmed that the current unchanged UI is unusable at 390 px because the fixed sidebar consumes most of the viewport and dashboard content remains desktop-sized. The proposed concept reflows the navigation and content at that width. This is visual evidence for the responsive recommendation, not a formal accessibility certification.

## Backend test run

The original requirement ranges were installed into a new isolated audit environment. Because the requirements use lower bounds rather than a lockfile, this validates one fresh resolution on Python 3.12; it does not reproduce the bundled Python 3.14 environment or the Docker Python 3.11 image exactly.

Environment overrides directed SQLite, Chroma and uploads to isolated test paths and pointed the model URL at an unused local port. The supplied pytest suite produced:

- 19 collected tests.
- 14 passed.
- 1 failed.
- 4 skipped.
- 143 warnings.
- Approximately 18.3 seconds.

The failure was `test_document_upload_query_and_delete`: a travel per-diem query retrieved a handbook leave excerpt rather than the expected value. The four skipped tests require a PostgreSQL test service; one was not provisioned. The run did not validate PostgreSQL behavior or live Ollama inference.

## Isolated behavioral probes

Purpose-built probes used fresh SQLite, Chroma and upload locations under the review area. They did not modify the supplied database. The probes reproduced these behaviors:

| Probe | Observed result |
|---|---|
| `/auth/me` without a token | `200`; returned an administrator |
| Unknown `/auth/demo-switch/...` alias | `200`; issued a user token |
| Current frontend registration payload | `422` |
| Employee modifies another user's task | `200` |
| Vision request with a supplied image | Image was not forwarded; fixed `VIS-IMG-01` citation returned |
| Employee reads a restricted approval draft | Draft content visible |
| Manager self-approves with status `BANANA` and no reason | `200`; arbitrary state stored |
| Employee reads company audit details | `200` |
| Change unhashed audit IP/email fields | Verification still reported `VERIFIED` |
| Delete all audit rows | Empty log reported `VERIFIED`/`COMPLIANT` |
| Upload filename `../probe-only.txt` | Escaped the isolated upload directory |
| One 3,000-character paragraph | Produced an empty chunk and one 3,000-character chunk |
| 200-row CSV | Only rows through 150 were indexed |
| Simulation disabled with model unavailable | Canned fallback still returned |
| Rename the company, then run seed | Existing company was deleted and replaced with NovaWorks |

The supplied database was queried read-only and contains six `INDEXED` document rows titled “Company Travel Policy 2026” with the same filename.

## Not established by this review

This work does not establish production security, legal/regulatory compliance, accessibility conformance, air-gap isolation, live-model quality, PostgreSQL correctness, backup recovery, container portability, throughput, GPU compatibility or performance under real company load. Those require the target deployment, policies, hardware and representative authorized documents.

The synthetic M05 development figures are current fixture results. The proposed pilot gates remain unproven on an approved representative company corpus, holdout and model.
