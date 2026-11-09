import React, { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { ArrowLeft, Check, CheckCircle2, Clock3, FilePlus2, Send, X } from "lucide-react";
import { BusinessRequest, BusinessRequestDetail, BusinessRequestType, User } from "../types";
import { api } from "../services/api";
import { ModalSurface } from "../components/ui/ModalSurface";
import { readTextField, readNumberField, updateRequestField } from "../services/requestFields";
import { hasPermission } from "../services/permissions";
import { requestActions, requestDraftChanged } from "../services/requestState";
import { ApiError } from "../services/apiErrors";
import { Notice } from "../components/ui/Notice";
import { ErrorState } from "../components/ui/ErrorState";
import { requestDrafts, requestDraftScope, isNewRequestDirty, newRequestForm as emptyForm, requestFormFromRecord, type RequestForm } from "../services/requestDrafts";
import { ReviewerPicker, ReviewerAssignment } from "../components/requests/ReviewerPicker";

interface RequestsPageProps {
  currentUser: User;
  initialRequestId?: string | null;
  onRequestChange?: (requestId?: string) => void;
  onRefreshData: () => void;
}

const TYPE_LABELS: Record<BusinessRequestType, string> = {
  CONTROLLED_CHANGE: "Controlled change",
  ACCESS_REQUEST: "Access request",
  PURCHASE_REQUEST: "Purchase request"
};

const statusClass = (status: string) => `request-status request-status-${status.toLowerCase()}`;
const readable = (value: string) => value.replaceAll("_", " ").toLowerCase().replace(/^./, (letter) => letter.toUpperCase());

const RequestFields: React.FC<{
  type: BusinessRequestType;
  fields: Record<string, unknown>;
  onChange: (fields: Record<string, unknown>) => void;
  disabled?: boolean;
}> = ({ type, fields, onChange, disabled }) => {
  const update = (name: string, value: string | number | null) => onChange(updateRequestField(fields, name, value));
  if (type === "CONTROLLED_CHANGE") {
    return <div className="request-field-grid">
      <label>Asset or process<input disabled={disabled} value={readTextField(fields, "affected_asset")} onChange={(e) => update("affected_asset", e.target.value)} /></label>
      <label>Proposed change<textarea disabled={disabled} value={readTextField(fields, "proposed_change")} onChange={(e) => update("proposed_change", e.target.value)} /></label>
      <label>Business reason<textarea disabled={disabled} value={readTextField(fields, "business_reason")} onChange={(e) => update("business_reason", e.target.value)} /></label>
      <label>Impact assessment<textarea disabled={disabled} value={readTextField(fields, "impact_assessment")} onChange={(e) => update("impact_assessment", e.target.value)} /></label>
      <label>Rollback plan<textarea disabled={disabled} value={readTextField(fields, "rollback_plan")} onChange={(e) => update("rollback_plan", e.target.value)} /></label>
    </div>;
  }
  if (type === "ACCESS_REQUEST") {
    return <div className="request-field-grid">
      <label>Resource<input disabled={disabled} value={readTextField(fields, "resource")} onChange={(e) => update("resource", e.target.value)} /></label>
      <label>Access level<select disabled={disabled} value={readTextField(fields, "access_level")} onChange={(e) => update("access_level", e.target.value || null)}><option value="">Select</option><option value="VIEW">View</option><option value="EDIT">Edit</option><option value="ADMIN">Admin</option></select></label>
      <label>Business reason<textarea disabled={disabled} value={readTextField(fields, "business_reason")} onChange={(e) => update("business_reason", e.target.value)} /></label>
      <label>End date (optional)<input type="date" disabled={disabled} value={readTextField(fields, "end_date")} onChange={(e) => update("end_date", e.target.value || null)} /></label>
    </div>;
  }
  return <div className="request-field-grid">
    <label>Item<input disabled={disabled} value={readTextField(fields, "item")} onChange={(e) => update("item", e.target.value)} /></label>
    <label>Quantity<input type="number" min="1" disabled={disabled} value={readNumberField(fields, "quantity")} onChange={(e) => update("quantity", e.target.value ? Number(e.target.value) : null)} /></label>
    <label>Estimated cost<input type="number" min="0" step="0.01" disabled={disabled} value={readNumberField(fields, "estimated_cost")} onChange={(e) => update("estimated_cost", e.target.value ? Number(e.target.value) : null)} /></label>
    <label>Currency<input disabled={disabled} maxLength={3} placeholder="USD" value={readTextField(fields, "currency")} onChange={(e) => update("currency", e.target.value ? e.target.value.toUpperCase() : null)} /></label>
    <label>Vendor (optional)<input disabled={disabled} value={readTextField(fields, "vendor")} onChange={(e) => update("vendor", e.target.value)} /></label>
    <label>Business reason<textarea disabled={disabled} value={readTextField(fields, "business_reason")} onChange={(e) => update("business_reason", e.target.value)} /></label>
  </div>;
};

export const ApprovalsPage: React.FC<RequestsPageProps> = ({ currentUser, initialRequestId, onRequestChange, onRefreshData }) => {
  const draftScope = requestDraftScope(currentUser);
  useSyncExternalStore(requestDrafts.subscribe, requestDrafts.getSnapshot);
  const pendingDrafts = requestDrafts.list(draftScope);
  const canReview = hasPermission(currentUser, "workflow:approve");
  const canCreate = hasPermission(currentUser, "workflow:trigger");
  const [view, setView] = useState<"mine" | "review">("mine");
  const [requests, setRequests] = useState<BusinessRequest[]>([]);
  const [selectedRecord, setSelected] = useState<BusinessRequestDetail | null>(null);
  const selected = selectedRecord?.id === initialRequestId ? selectedRecord : null;
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState<RequestForm>(() => requestDrafts.get(draftScope, "new")?.form ?? emptyForm());
  const [draftForm, setDraftForm] = useState<RequestForm>(emptyForm());
  const [actionNote, setActionNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [listRevision, setListRevision] = useState(0);
  const [recordRevision, setRecordRevision] = useState(0);
  const [recordFailure, setRecordFailure] = useState<{ id: string; message: string } | null>(null);
  const [writeConflict, setNeedsReload] = useState(false);
  const [cancelNote, setCancelNote] = useState("");
  const routeId = useRef(initialRequestId);
  const freshNavigation = useRef<string | null>(null);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => { routeId.current = initialRequestId; }, [initialRequestId]);
  const actions = selected ? requestActions(currentUser, selected) : null;
  const dirty = Boolean(selected && actions?.edit && requestDraftChanged(draftForm, selected));
  const needsReload = writeConflict || Boolean(selected && requests.some((item) => item.id === selected.id && item.lock_version > selected.lock_version));
  const detailError = recordFailure && recordFailure.id === initialRequestId ? recordFailure.message : null;
  const detailLoading = Boolean(initialRequestId && !selected && !detailError);
  useEffect(() => {
    if (busy) return;
    if (isNewRequestDirty(createForm)) requestDrafts.put(draftScope, "new", { kind: "new", form: createForm });
    else requestDrafts.remove(draftScope, "new");
  }, [createForm, draftScope, busy]);
  useEffect(() => {
    if (!selected || busy) return;
    if (dirty || actionNote.trim() || cancelNote.trim()) requestDrafts.put(draftScope, selected.id, { kind: "record", record: selected, form: draftForm, actionNote, cancelNote });
    else requestDrafts.remove(draftScope, selected.id);
  }, [selected, draftForm, dirty, actionNote, cancelNote, draftScope, busy]);
  useEffect(() => {
    if (showCreate || (!selected?.id && !detailError)) return;
    const frame = window.requestAnimationFrame(() => {
      const heading = document.querySelector<HTMLElement>(detailError ? '.request-detail [role="alert"]' : ".request-detail h2");
      if (heading) { heading.tabIndex = -1; heading.focus(); }
    });
    return () => window.cancelAnimationFrame(frame);
  }, [selected?.id, showCreate, detailError]);

  const loadList = () => {
    setLoading(true);
    setListError(null);
    setListRevision((revision) => revision + 1);
  };
  const mayDiscardChanges = () => !(dirty || actionNote.trim() || cancelNote.trim()) || window.confirm("Discard unsaved changes and reload the saved record?");
  const openRequest = (id: string) => {
    if (busy) return;
    if (id === initialRequestId && !mayDiscardChanges()) return;
    setError(null); setRecordFailure(null);
    if (id === initialRequestId) { requestDrafts.remove(draftScope, id); setSelected(null); setRecordRevision((revision) => revision + 1); }
    else onRequestChange?.(id);
  };
  const closeRequest = () => {
    if (busy) return;
    setSelected(null); setError(null); onRequestChange?.();
  };
  const reloadRequest = () => {
    if (!mayDiscardChanges()) return;
    if (initialRequestId) requestDrafts.remove(draftScope, initialRequestId);
    setSelected(null); setRecordFailure(null); setError(null);
    setRecordRevision((revision) => revision + 1);
  };

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    api.getRequests(view, undefined, controller.signal)
      .then((data) => { if (active) { setRequests(data); setListError(null); } })
      .catch((cause) => { if (active) setListError(cause instanceof Error ? cause.message : "Requests could not be loaded."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; controller.abort(); };
  }, [view, listRevision]);

  useEffect(() => {
    if (!initialRequestId) return;
    // Creation already returned this exact record. Later history/reload visits fetch fresh.
    if (freshNavigation.current === initialRequestId) { freshNavigation.current = null; return; }
    let active = true;
    const controller = new AbortController();
    api.getRequest(initialRequestId, controller.signal)
      .then((detail) => {
        if (!active) return;
        const pending = requestDrafts.get(draftScope, detail.id);
        const restored = pending?.kind === "record" ? pending : null;
        setSelected(restored?.record ?? detail);
        setRequests((items) => items.map((item) => item.id === detail.id ? detail : item));
        setDraftForm(restored?.form ?? requestFormFromRecord(detail));
        setActionNote(restored?.actionNote ?? "");
        setCancelNote(restored?.cancelNote ?? ""); setNeedsReload(Boolean(restored && restored.record.lock_version !== detail.lock_version)); setRecordFailure(null); setError(null);
      })
      .catch((cause) => { if (active) { setSelected(null); setRecordFailure({ id: initialRequestId, message: cause instanceof Error ? cause.message : "This request could not be opened." }); } });
    return () => { active = false; controller.abort(); };
  }, [initialRequestId, recordRevision, draftScope]);

  const pendingCount = useMemo(() => requests.filter((item) => ["SUBMITTED", "ASSIGNED"].includes(item.status)).length, [requests]);

  const refreshAfterAction = async (detail: BusinessRequestDetail) => {
    requestDrafts.remove(draftScope, detail.id);
    setSelected(detail);
    if (detail.id !== routeId.current) freshNavigation.current = detail.id;
    onRequestChange?.(detail.id);
    setDraftForm(requestFormFromRecord(detail));
    setActionNote("");
    // Saving draft fields does not submit a cancellation reason.
    setCancelNote(detail.status === "DRAFT" ? cancelNote : ""); setNeedsReload(false);
    loadList();
    onRefreshData();
  };

  const execute = async (operation: () => Promise<BusinessRequestDetail>) => {
    const requestedId = initialRequestId;
    const submittedBuffer = requestedId ? requestDrafts.get(draftScope, requestedId) : undefined;
    const priorFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setBusy(true);
    setError(null);
    try {
      const detail = await operation();
      if (mounted.current && routeId.current === requestedId) await refreshAfterAction(detail);
      else requestDrafts.removeIfUnchanged(draftScope, detail.id, submittedBuffer);
    }
    catch (cause: unknown) {
      if (mounted.current && routeId.current === requestedId) {
        setError(cause instanceof Error ? cause.message : "The request could not be updated. Please retry.");
        if (cause instanceof ApiError && cause.status === 409) setNeedsReload(true);
      }
    }
    finally {
      setBusy(false);
      window.requestAnimationFrame(() => {
        if (!mounted.current || routeId.current !== requestedId) return;
        if (priorFocus?.isConnected && !priorFocus.hasAttribute("disabled")) priorFocus.focus();
        else {
          const heading = document.querySelector<HTMLElement>(".request-detail h2");
          if (heading) { heading.tabIndex = -1; heading.focus(); }
        }
      });
    }
  };

  const createRequest = async () => {
    const submittedBuffer = requestDrafts.get(draftScope, "new");
    setBusy(true);
    setError(null);
    try {
      const detail = await api.createRequest({
        request_type: createForm.request_type,
        title: createForm.title,
        description: createForm.description,
        risk_level: createForm.risk_level,
        assigned_reviewer_id: createForm.assigned_reviewer_id,
        payload: createForm.fields
      });
      requestDrafts.removeIfUnchanged(draftScope, "new", submittedBuffer);
      if (!mounted.current) return;
      setShowCreate(false);
      setCreateForm(emptyForm());
      await refreshAfterAction(detail);
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : "The draft could not be created.");
    } finally {
      setBusy(false);
    }
  };

  const submittedSnapshot = selected?.versions.find((version) => version.id === selected.submitted_version_id);
  const feedback = error && <Notice tone="error" onDismiss={() => setError(null)}>{error}</Notice>;
  const discardPending = (key: string) => {
    if (key === initialRequestId) { reloadRequest(); return; }
    if (!window.confirm("Discard this unsaved request text? Saved records will be kept.")) return;
    requestDrafts.remove(draftScope, key);
    if (key === "new") setCreateForm(emptyForm());
  };

  return (
    <div className="requests-page">
      <header className="requests-header">
        <div>
          <div className="page-kicker">Governed work</div>
          <h1>Requests</h1>
          <p>Draft, review, decide, and fulfill controlled work with a complete version history.</p>
        </div>
        <div className="requests-header-actions"><button type="button" disabled={busy} aria-disabled={loading} aria-busy={loading} className="btn-secondary" onClick={() => { if (!loading) loadList(); }}>{loading ? "Refreshing…" : "Refresh requests"}</button>{canCreate && <button type="button" disabled={busy} className="btn-primary" onClick={() => { setError(null); setShowCreate(true); }}><FilePlus2 size={14} /> New request</button>}</div>
      </header>

      {!showCreate && feedback}
      {pendingDrafts.length > 0 && <section className="pending-drafts" aria-label="Unsaved request text"><h2>Unsaved request text</h2><p>Kept while you move around this workspace. Save or discard it before closing this browser session.</p>{pendingDrafts.map(([key, item]) => <div key={key}><button type="button" className="text-button" disabled={busy} onClick={() => key === "new" ? setShowCreate(true) : onRequestChange?.(key)}>{item.form.title || "New request draft"}</button><button type="button" className="text-button danger-text" disabled={busy} onClick={() => discardPending(key)}>Discard<span className="sr-only"> {item.form.title || "new request draft"}</span></button></div>)}</section>}

      <div className="request-tabs" role="group" aria-label="Request view">
        <button disabled={busy} aria-pressed={view === "mine"} className={view === "mine" ? "active" : ""} onClick={() => { if (view !== "mine") setLoading(true); setView("mine"); setSelected(null); setError(null); onRequestChange?.(); }}>My requests</button>
        {canReview && <button disabled={busy} aria-pressed={view === "review"} className={view === "review" ? "active" : ""} onClick={() => { if (view !== "review") setLoading(true); setView("review"); setSelected(null); setError(null); onRequestChange?.(); }}>Review queue {view === "review" && !loading && !listError && pendingCount > 0 && <span>{pendingCount}</span>}</button>}
      </div>

      <div className="request-layout">
        <section className={`request-register ${selected ? "has-selection" : ""}`}>
          {loading && <div className="empty-state">Loading requests…</div>}
          {!loading && listError && <div className="request-empty" role="alert"><strong>Requests could not be loaded</strong><span>{listError}</span><button type="button" className="btn-secondary" onClick={() => void loadList()}>Try again</button></div>}
          {!loading && !listError && requests.length === 0 && <div className="request-empty"><CheckCircle2 size={22} /><strong>No requests in this view</strong><span>Create a draft or wait for a submitted request.</span></div>}
          {!loading && !listError && requests.map((item) => (
            <button type="button" disabled={busy} key={item.id} className={`request-row ${selected?.id === item.id ? "active" : ""}`} onClick={() => openRequest(item.id)}>
              <div className="request-row-top"><span>{TYPE_LABELS[item.request_type]}</span><span className={statusClass(item.status)}>{readable(item.status)}</span></div>
              <strong>{item.title}</strong>
              <p>{item.description}</p>
              <div className="request-row-meta"><span>{item.requester_name || "Requester"}</span><span>Updated {new Date(item.updated_at).toLocaleDateString()}</span></div>
            </button>
          ))}
        </section>

        <section className="request-detail">
          {detailLoading && <div className="empty-state" role="status">Loading request…</div>}
          {detailError && <ErrorState title="Request unavailable" description={detailError} onRetry={reloadRequest} />}
          {!initialRequestId && !selected && <div className="request-detail-empty"><Clock3 size={24} /><strong>Select a request</strong><span>Open a record to review its current fields, submitted version, and timeline.</span></div>}
          {selected && <>
            <div className="request-detail-header">
              <div className="request-actions"><button disabled={busy} className="request-back" type="button" onClick={closeRequest}><ArrowLeft size={14} /> Back</button><button disabled={busy} className="btn-secondary" type="button" onClick={reloadRequest}>Reload record</button></div>
              <div className="request-detail-title"><div><span>{TYPE_LABELS[selected.request_type]} · {selected.risk_level} risk</span><h2>{selected.title}</h2></div><span className={statusClass(selected.status)}>{readable(selected.status)}</span></div>
              <p>{selected.description}</p>
            </div>

            {needsReload && <Notice tone="info">This record changed. Reload it and review the latest version before taking another action. Your current fields remain visible until you reload.</Notice>}

            <div className="request-facts">
              <div><span>Requester</span><strong>{selected.requester_name || "Unknown"}</strong></div>
              <div><span>Reviewer</span><strong>{selected.assigned_reviewer_name || "Unassigned"}</strong></div>
              <div><span>Current version</span><strong>v{selected.versions.at(-1)?.version_number || 1}</strong></div>
              <div><span>Record ID</span><strong>{selected.id.slice(0, 8)}</strong></div>
            </div>

            <div className="request-detail-body">
              <section>
                <div className="request-section-heading"><h3>{selected.status === "DRAFT" && selected.requester_id === currentUser.id ? "Edit draft" : "Request fields"}</h3>{submittedSnapshot && <span>Decision bound to v{submittedSnapshot.version_number}</span>}</div>
                {selected.status === "DRAFT" && selected.requester_id === currentUser.id && <div className="request-field-grid request-basics">
                  <label>Title<input disabled={busy || needsReload} value={draftForm.title} onChange={(e) => setDraftForm({ ...draftForm, title: e.target.value })} /></label>
                  <label>Risk<select disabled={busy || needsReload} value={draftForm.risk_level} onChange={(e) => setDraftForm({ ...draftForm, risk_level: e.target.value as BusinessRequest["risk_level"] })}><option>LOW</option><option>MEDIUM</option><option>HIGH</option><option>CRITICAL</option></select></label>
                  <label>Description<textarea disabled={busy || needsReload} value={draftForm.description} onChange={(e) => setDraftForm({ ...draftForm, description: e.target.value })} /></label>
                </div>}
                <RequestFields type={selected.request_type} fields={draftForm.fields} onChange={(fields) => setDraftForm({ ...draftForm, fields })} disabled={!actions?.edit || busy || needsReload} />
                {actions?.edit && <ReviewerPicker key={selected.id} requestId={selected.id} value={draftForm.assigned_reviewer_id} currentName={draftForm.assigned_reviewer_id === selected.assigned_reviewer_id ? selected.assigned_reviewer_name : undefined} onChange={(assigned_reviewer_id) => setDraftForm({ ...draftForm, assigned_reviewer_id })} disabled={busy || needsReload} />}

                {selected.status === "DRAFT" && selected.requester_id === currentUser.id && <div className="request-actions">
                  <button className="btn-secondary" disabled={busy || needsReload || !dirty || !draftForm.title.trim() || !draftForm.description.trim()} onClick={() => void execute(() => api.updateRequest(selected.id, { expected_lock_version: selected.lock_version, title: draftForm.title, description: draftForm.description, risk_level: draftForm.risk_level, assigned_reviewer_id: draftForm.assigned_reviewer_id, payload: draftForm.fields }))}>Save new version</button>
                  <button className="btn-primary" disabled={busy || needsReload || dirty} aria-describedby={dirty ? "request-unsaved" : undefined} onClick={() => { if (!dirty) void execute(() => api.submitRequest(selected.id, selected.lock_version)); }}><Send size={13} /> Submit exact version</button>
                </div>}
                {dirty && <p id="request-unsaved" role="status" className="form-note">Unsaved changes. Save a new version before submitting.</p>}

                {actions?.assign && <ReviewerAssignment key={`${selected.id}:${selected.lock_version}`} requestId={selected.id} reviewerId={selected.assigned_reviewer_id} currentUserId={currentUser.id} disabled={busy || needsReload} onAssign={(reviewerId) => void execute(() => api.assignRequest(selected.id, reviewerId, selected.lock_version))} />}

                {actions?.decide && <div className="decision-panel">
                  <label>Decision reason<textarea disabled={busy || needsReload} maxLength={4000} value={actionNote} onChange={(e) => setActionNote(e.target.value)} placeholder="Record the evidence and reason for this decision." /></label>
                  <div className="request-actions">
                    <button className="btn-secondary danger-text" disabled={busy || needsReload || actionNote.trim().length < 3} onClick={() => void execute(() => api.decideRequest(selected.id, "REJECTED", actionNote, selected.submitted_version_id!, selected.lock_version))}><X size={13} /> Reject</button>
                    <button className="btn-primary" disabled={busy || needsReload || actionNote.trim().length < 3} onClick={() => void execute(() => api.decideRequest(selected.id, "APPROVED", actionNote, selected.submitted_version_id!, selected.lock_version))}><Check size={13} /> Approve version</button>
                  </div>
                </div>}

                {selected.status === "APPROVED" && <Notice tone="info">Approved. Completion has not been recorded; approval does not carry out the requested action.</Notice>}
                {actions?.complete && <div className="decision-panel">
                  <label>Fulfillment record<textarea disabled={busy || needsReload} maxLength={4000} value={actionNote} onChange={(e) => setActionNote(e.target.value)} placeholder="Describe what was completed and include any reference number." /></label>
                  <div className="request-actions"><button className="btn-primary" disabled={busy || needsReload || actionNote.trim().length < 3} onClick={() => void execute(() => api.fulfillRequest(selected.id, actionNote, selected.lock_version))}>Mark completed</button></div>
                </div>}

                {actions?.cancel && <details className="decision-panel"><summary>Cancel this request</summary><label>Cancellation reason<textarea disabled={busy || needsReload} maxLength={2000} value={cancelNote} onChange={(event) => setCancelNote(event.target.value)} /></label><div className="request-actions"><button className="btn-secondary danger-text" disabled={busy || needsReload || cancelNote.trim().length < 3} onClick={() => void execute(() => api.cancelRequest(selected.id, cancelNote, selected.lock_version))}>Cancel request</button></div></details>}

                {selected.decision_reason && <div className="decision-record"><span>Decision reason</span><p>{selected.decision_reason}</p></div>}
                {selected.fulfillment_notes && <div className="decision-record"><span>Fulfillment record</span><p>{selected.fulfillment_notes}</p></div>}
              </section>

              <aside className="request-timeline">
                <h3>Timeline</h3>
                {selected.timeline.map((event) => <div className="timeline-event" key={event.id}><span /><div><strong>{readable(event.event_type)}</strong><p>{event.actor_name || "System"} · {new Date(event.created_at).toLocaleString()}</p>{event.reason && <blockquote>{event.reason}</blockquote>}</div></div>)}
                <div className="version-summary"><strong>{selected.versions.length} immutable version{selected.versions.length === 1 ? "" : "s"}</strong><span>Every draft save creates a separate snapshot.</span></div>
              </aside>
            </div>
          </>}
        </section>
      </div>

      {showCreate && <ModalSurface className="request-create-modal" labelledBy="create-request-title" onClose={() => setShowCreate(false)} dismissible={!busy}>
          <div className="modal-heading"><div><div className="page-kicker">New governed record</div><h2 id="create-request-title">Create request draft</h2></div><button type="button" disabled={busy} aria-label="Close create request" className="icon-button" onClick={() => setShowCreate(false)}><X size={16} /></button></div>
          {feedback}
          <div className="request-field-grid request-basics">
            <label>Request type<select disabled={busy} value={createForm.request_type} onChange={(e) => { if (Object.keys(createForm.fields).length && !window.confirm("Change request type and clear its fields? Title and description will be kept.")) return; setCreateForm({ ...createForm, request_type: e.target.value as BusinessRequestType, fields: {} }); }}>{Object.entries(TYPE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label>Risk<select disabled={busy} value={createForm.risk_level} onChange={(e) => setCreateForm({ ...createForm, risk_level: e.target.value as BusinessRequest["risk_level"] })}><option>LOW</option><option>MEDIUM</option><option>HIGH</option><option>CRITICAL</option></select></label>
            <label>Title<input disabled={busy} value={createForm.title} onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })} /></label>
            <label>Description<textarea disabled={busy} value={createForm.description} onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })} /></label>
          </div>
          <RequestFields type={createForm.request_type} fields={createForm.fields} onChange={(fields) => setCreateForm({ ...createForm, fields })} disabled={busy} />
          <ReviewerPicker value={createForm.assigned_reviewer_id} onChange={(assigned_reviewer_id) => setCreateForm({ ...createForm, assigned_reviewer_id })} disabled={busy} />
          <p className="form-note">This text stays available while you move around this workspace. Create a draft to save it as a company record.</p>
          <div className="modal-actions"><button disabled={busy} className="btn-secondary" onClick={() => setShowCreate(false)}>Close draft</button><button className="btn-primary" disabled={busy || !createForm.title.trim() || !createForm.description.trim()} onClick={() => void createRequest()}>Create draft</button></div>
      </ModalSurface>}
    </div>
  );
};
