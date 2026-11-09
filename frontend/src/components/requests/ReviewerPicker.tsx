import React, { useEffect, useId, useState } from "react";
import { api } from "../../services/api";
import type { RequestReviewer } from "../../types";

interface ReviewerPickerProps {
  requestId?: string;
  value: string | null;
  onChange: (value: string | null) => void;
  disabled?: boolean;
  allowUnassigned?: boolean;
  currentName?: string | null;
}

export function ReviewerPicker({ requestId, value, onChange, disabled, allowUnassigned = true, currentName }: ReviewerPickerProps) {
  const [reviewers, setReviewers] = useState<RequestReviewer[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const hintId = useId();
  useEffect(() => {
    const controller = new AbortController();
    void api.getRequestReviewers(requestId, controller.signal).then((items) => {
      if (!controller.signal.aborted) { setReviewers(items); setError(null); }
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Reviewers could not be loaded.");
    });
    return () => controller.abort();
  }, [requestId, revision]);
  const missing = Boolean(value && reviewers && !reviewers.some((item) => item.id === value));
  return <div className="reviewer-picker">
    <label>Reviewer<select disabled={disabled || reviewers === null || Boolean(error)} value={value ?? ""} aria-describedby={hintId} onChange={(event) => onChange(event.target.value || null)}>
      <option value="" disabled={!allowUnassigned}>{allowUnassigned ? "Unassigned review queue" : "Choose reviewer"}</option>
      {value && (!reviewers || missing) && <option value={value} disabled>{currentName || "Selected reviewer"}{missing ? " — no longer eligible" : ""}</option>}
      {reviewers?.map((item) => <option key={item.id} value={item.id}>{item.full_name}{item.job_title ? ` · ${item.job_title}` : ""}</option>)}
    </select></label>
    <p className="form-note" id={hintId}>{error ? "Reviewer choices are unavailable. Retry before choosing someone." : reviewers === null ? "Loading eligible reviewers…" : missing ? "Choose another reviewer or clear the selection before submitting." : reviewers.length === 0 ? "No eligible reviewers are available. An authorized reviewer is required before a decision can be recorded." : "Only active company reviewers are listed. Requesters cannot review their own work."}</p>
    {error && <div role="alert"><span>{error}</span><button type="button" className="text-button" disabled={disabled} onClick={() => { setReviewers(null); setError(null); setRevision((count) => count + 1); }}>Retry reviewers</button></div>}
    {allowUnassigned && value && <button type="button" className="text-button" disabled={disabled} onClick={() => onChange(null)}>Use unassigned review queue</button>}
  </div>;
}

export function ReviewerAssignment({ requestId, reviewerId, currentUserId, disabled, onAssign }: {
  requestId: string; reviewerId?: string | null; currentUserId: string; disabled: boolean; onAssign: (id: string) => void;
}) {
  const [choice, setChoice] = useState<string | null>(null);
  return <section className="decision-panel" aria-label="Reviewer assignment">
    <h3>{reviewerId ? "Change reviewer" : "Assign review"}</h3>
    <ReviewerPicker requestId={requestId} value={choice} onChange={setChoice} disabled={disabled} allowUnassigned={false} />
    <div className="request-actions">
      {!reviewerId && <button type="button" className="btn-secondary" disabled={disabled} onClick={() => onAssign(currentUserId)}>Assign to me</button>}
      <button type="button" className="btn-secondary" disabled={disabled || !choice || choice === reviewerId} onClick={() => { if (choice) onAssign(choice); }}>{reviewerId ? "Change reviewer" : "Assign reviewer"}</button>
    </div>
    <p className="form-note">Assignment changes who reviews this request. It does not change the submitted version or grant access to the requested resource.</p>
  </section>;
}
