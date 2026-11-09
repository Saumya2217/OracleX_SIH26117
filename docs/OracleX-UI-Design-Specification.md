# OracleX professional UI specification

Design proposal · No application changes · 17 September 2026

## Design intent

Make OracleX feel like a dependable internal business application. The interface should communicate the document, request, person or decision the employee is working on. AI is a capability inside that workflow.

Use opaque surfaces, a precise typographic hierarchy, practical tables, restrained icons and clear action placement. No glassmorphism, backdrop blur, gradient backgrounds, glowing borders, animated particles, floating orbs, robot mascots, rainbow status palettes or giant prompt-centric home screen. A plain dim overlay behind an opaque dialog is acceptable; it must not blur the page.

The current active design already has a restrained dark palette. Preserve that restraint, but replace the repeated card piles, tiny labels, hidden state errors, vague security claims and inconsistent page layouts. Offer a comfortable light theme and a deliberate dark theme with equal functional quality.

## Information architecture

Primary navigation, with visibility based on server capabilities:

| Destination | Employee | Reviewer/manager | Administrator |
|---|---|---|---|
| Overview | Personal work and recent authorized sources | Assigned reviews and team work | Actionable organization status and failures |
| Documents | Authorized library and saved items | Team library and document ownership | Library administration, indexing and retention |
| Ask OracleX | Evidence-backed questions and saved conversations | Same, within authorized scope | Same; no automatic universal content access merely for IT admin |
| Requests | Own drafts/submitted requests and outcomes | Assigned review queue and history | Policy-authorized oversight |
| My work | Assigned tasks | Team work if permitted | Scoped operational overview |
| Administration | Not shown | Only delegated settings | People, teams, roles, system status, audit |

Show only shipped destinations. If tasks are deferred, omit My work. Keep notifications inside the header or as a compact inbox; defer Messages as a top-level product until it is real. Place diagnostics/Test Center in a separate nonproduction environment. Group departments and roles under Administration rather than giving every management table a primary nav entry.

Use stable URLs: `/overview`, `/documents`, `/documents/:id/versions/:version`, `/ask/:conversationId`, `/requests/:id`, `/work`, `/admin/people`, `/admin/roles`, `/admin/system`, `/admin/audit`. Preserve filters in query parameters when useful; browser back must work predictably.

## Visual foundations

Proposed tokens, subject to measured contrast verification in all states:

| Token | Light | Dark | Usage |
|---|---|---|---|
| Canvas | `#F5F6F8` | `#15181C` | App background |
| Surface | `#FFFFFF` | `#1D2127` | Content, tables, dialogs |
| Subtle surface | `#F0F2F5` | `#252B33` | Sidebar, table header, selected neutral state |
| Primary text | `#20252D` | `#F0F2F5` | Headings, values, body |
| Secondary text | `#596474` | `#B4BECA` | Supporting labels |
| Structural border | `#DDE2E8` | `#3C4552` | Dividers; not sole affordance for controls |
| Interactive border | `#7A8697` | `#8491A3` | Inputs/control boundaries when needed |
| Primary action | `#234FA3` | `#9CBFFF` | One blue accent, restrained application |
| Primary button text | `#FFFFFF` | `#13203B` | Text on primary fill |
| Success text | `#24613D` | `#8BC9A1` | Named completed/ready state |
| Warning text | `#82580A` | `#E8C274` | Named pending/partial state |
| Error text | `#A33131` | `#F0A5A5` | Actual error/danger state |

Typography: use a system sans-serif stack or a locally hosted licensed font. No Google Fonts request in the deployed app. Body and controls 14–16px, secondary 12–13px, page title 24–28px, section title 16–18px. Use 400/500/600 weights; reserve stronger weight for a small number of primary headings. Use tabular numerals for dates/counts in tables and monospace only for technical identifiers in details.

Spacing: 4/8/12/16/24/32px scale. Desktop content padding 24–32px; sidebar 224–240px; header 56–64px; form content max-width about 640px. Tables may use available width. Radius 4–6px on controls, 6–8px on dialogs; avoid pill styling everywhere. Use thin dividers and alignment before adding cards. Shadows are optional and small, only when an elevated layer needs separation.

Primary controls approximately 36–40px high for pointer use, with adequate effective touch targets. Motion only for state transition, approximately 120–180ms, respecting reduced-motion preferences. Do not pulse a healthy indicator indefinitely.

## Page specifications

### 1. Sign-in and first setup

- Small company wordmark and a direct “Sign in to [company]” heading.
- SSO button if configured; otherwise labeled email/password, show-password control, actionable validation, and the company's chosen recovery route.
- No prefilled credentials, demo chips, inflated privacy badges or public “Register company” after setup.
- First-time bootstrap is an administrator-only setup flow: organization → identity/owner → departments/access → deployment validation. Show actual validation results.
- On expired session, return to the requested page after sign-in where safe. On logout, clear cached documents/messages and prevent old in-flight responses from repopulating them.

### 2. Overview

One clear heading: “Overview.” Follow it with a short personal context line, then the things requiring action.

- “Needs attention”: assigned requests, failed owned uploads, overdue tasks. Each row opens the specific record.
- “Recent documents”: title, owner/team, updated date, version/status. Sort by a defined timestamp.
- “My work”: a short list if the tasks feature is in scope.
- A modest “Ask a question” action or navigation link. Do not duplicate a huge assistant box on every page.
- Counts must come from permission-scoped queries. No hardcoded team counts, unsupported compliance scores or vanity charts.
- Admins see operational failures and setup gaps; an empty healthy workspace is a calm empty state, not fabricated activity.

### 3. Documents

Header: **Documents** + a single **Upload document** action when permitted.

Toolbar: labeled search, team/audience filter, document type/status filter, sort. Use one dense table rather than a card for every document.

Columns: title/file type, owner/team, access classification, current version, processing/review status, updated date, row action menu. Filename can be supporting text beneath the title. Do not display “chunks” as the main document metadata.

Detail: source preview on the left; metadata, versions and linked requests in a side panel. A cited page opens with the relevant passage highlighted. Display permission-checked download only when supported. Separate “Archive” from permanent removal.

Upload flow:

1. Choose supported file; display size/type and any limits.
2. Title and owner; infer safe defaults without hiding the fields.
3. Classification and audience as separate labeled choices, e.g. “Internal” and “Operations team.”
4. Show the effective audience before submission.
5. Display progress through upload/scan/parse/index, with retry or a clear action when needed.

States: loading skeleton; no documents yet; no search matches; forbidden; indexing; partially extracted; failed with retry; ready; superseded; archived. “No matches” must never conceal an unavailable search service.

### 4. Ask OracleX

Use a work area organized around the question and evidence, with optional recent conversations. A wide desktop layout can have conversation content and a 320–380px evidence panel; on smaller screens the evidence panel becomes a clearly labeled separate view.

- Composer supports multiline questions, selected authorized sources and an explicit submit action. Attachments appear only when supported end to end.
- Show source scope and verified model availability in understated text.
- Responses use readable paragraphs/lists, with inline source references opening exact document versions/locations.
- Evidence panel shows source title, page/section, short excerpt, version and modified date.
- Display “No supporting company source found” when appropriate; distinguish general explanation, extractive fallback and generated company answer.
- Provide stop, retry, copy and feedback only when the behavior is implemented. Retain the draft after failure.
- Put execution metadata under “Run details”; do not present a scripted agent trace as private reasoning or factual proof.
- An action suggestion becomes a structured request preview. A message in chat never directly authorizes an operation.

### 5. Requests and approvals

Prefer the navigation word **Requests** because every employee may submit and track one. Reviewers have **Assigned to me**, **Submitted by me** and **History** tabs according to permission.

List columns: request title/type, requester/team, submitted date, status, assigned reviewer and due date if policy uses one. Show priority/risk with text, not color alone.

Detail layout:

- Header with request ID, title and current state.
- Summary of requested change, expected impact, requester and relevant source documents.
- Before/after fields or an exact structured payload, including amounts/units where applicable.
- Timeline of submission, review and fulfillment; distinguish “Approved” from “Completed.”
- Decision section with reviewer-entered reason and clearly labeled approve/reject actions, only when the server grants authority.
- If another reviewer has already acted, refresh to the authoritative decision and explain the conflict.
- If self-review is prohibited, state who is assigned rather than presenting a nonfunctional action.

### 6. My work

Default to a sortable table/list with title, owner, due date, priority and status. Use a board view only if the team's workflow benefits. Task detail holds notes, linked sources/requests and change history. An employee's “My work” response must be scoped server-side, not merely filtered after fetching everyone else's tasks.

### 7. People, teams and access

Use a searchable people table: name, team, job title, role, status. Clearance and administrative permissions belong in access detail, not an ambiguous “Role Access” dropdown.

- Invite user or provision through IdP; do not assign a shared password silently.
- Edit profile and edit access are visibly different operations.
- Show effective permissions and scope; explain policy denials without exposing restricted content.
- Confirm high-impact access changes with precise before/after information and an audit reason where required.
- Protect final admin access and reporting hierarchy constraints. Deactivation should preserve past attribution.

### 8. Audit and system status

Audit is a privileged searchable table with date, actor, action, resource and outcome. Expand technical details only on demand. Show full date/time with timezone, not just a clock time.

System status reports measured database/worker/model/index readiness, last successful ingest, failed jobs and storage limits. Distinguish local inference availability from network isolation. Display “Integrity check completed” with scope and last checkpoint; do not label the company “COMPLIANT” because rows match a checksum.

## Reusable component inventory

Build these once, then compose pages:

- AppShell, SidebarNav, PageHeader, Breadcrumbs and AccountMenu.
- Button with primary/secondary/danger/text variants; IconButton with an accessible name.
- TextField, PasswordField, TextArea, Select, Checkbox and FieldError with associated labels.
- DataTable with sorting, row actions, pagination and a clear no-results state.
- StatusLabel and ClassificationLabel with text plus restrained color; no decorative status animation.
- Dialog/Drawer with focus trap, Escape behavior and focus restoration; plain scrim, opaque surface.
- SourcePreview, CitationLink, VersionHistory and UploadProgress.
- RequestTimeline, ChangeSummary and DecisionForm.
- LoadingState, EmptyState, ErrorState, PermissionState and toast/inline result feedback.

Generate API types and organize feature code around documents, conversations, requests, administration and shared UI. A router and server-state cache are useful implementation tools; select maintained versions and test their behavior rather than introducing a large frontend framework migration.

## Responsive and accessibility behavior

At desktop widths, preserve a stable sidebar and optional evidence/details panel. Around tablet widths, collapse navigation deliberately and move details below/behind an accessible view switch. On phones, use a compact header and menu; primary actions remain visible and tables adapt or scroll inside an explicitly labeled region. Do not shrink all text to fit desktop columns.

Required checks: keyboard-only operation; logical headings and focus order; visible focus; programmatic labels; status announcements; modal focus containment/restoration; Escape to close where appropriate; reduced motion; 200% zoom; 320–390px reflow where applicable; touch targets; screen-reader names; long titles; high contrast in both themes. Target WCAG 2.2 AA. Normal text needs at least 4.5:1 contrast and large text at least 3:1; do not use color alone to indicate status. See [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/).

## Copy changes

| Current style | Proposed wording |
|---|---|
| Sovereign embedded intelligence engine | Local model available / Model unavailable |
| Hallucination-free / ground-truth reasoning | Answer based on the sources shown |
| 95% confidence | Evidence: supported / partial / unavailable, only when evaluated |
| Cryptographic ledger proving compliance | Audit integrity check, with its actual scope |
| Multi-agent orchestration session | Ask OracleX |
| Clearance L2 as a job role | Role: employee · Document clearance: internal |
| Execution suspended | Request submitted for review |
| Approved | Approved; awaiting completion, when that is the real state |
| No data | Specific empty state, or “Could not load documents” on failure |

## Design acceptance checklist

- No blur, gradients, glass panels, glows, AI mascot or decorative particle effects.
- One visual language across all current pages; no older cyan/purple page family mixed in.
- One primary action per page section; table rows and details convey structure before cards do.
- Every visible control works or clearly indicates a real unavailable state.
- Evidence and audience are understandable without reading technical internals.
- No hardcoded people counts, artificial messages, mock confidence, fictional source citations or unconditional privacy/compliance badges in real workspaces.
- All core journeys have loading, empty, denied, error, success and relevant partial states.
- Design is reviewed with representative staff performing tasks, then iterated based on observed difficulty.

The accompanying interactive concept uses illustrative sample records to show the proposed visual direction. It does not connect to your project, modify files or submit actual decisions.
