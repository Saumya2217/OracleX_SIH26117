import React, { useMemo, useState } from "react";
import { ArrowRight, CheckSquare, FileText, Search, ShieldCheck } from "lucide-react";
import { BusinessRequest, Company, DocumentItem, TaskItem, User } from "../types";
import { EmptyState } from "../components/ui/EmptyState";
import { Notice } from "../components/ui/Notice";
import { PageHeader } from "../components/ui/PageHeader";
import { StatusLabel } from "../components/ui/StatusLabel";

interface OverviewPageProps {
  currentUser: User;
  company: Company | null;
  tasks: TaskItem[];
  requests: BusinessRequest[];
  documents: DocumentItem[];
  dataErrors: Partial<Record<"company" | "tasks" | "requests" | "documents", string>>;
  dataLoaded: boolean;
  onRefresh: () => void;
  onNavigate: (tab: string, initialPrompt?: string, entityId?: string) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ currentUser, company, tasks, requests, documents, dataErrors, dataLoaded, onRefresh, onNavigate }) => {
  const [question, setQuestion] = useState("");
  const activeTasks = useMemo(() => tasks.filter((task) => task.status !== "COMPLETED"), [tasks]);
  const pendingRequests = useMemo(() => requests.filter((request) => ["SUBMITTED", "ASSIGNED"].includes(request.status)), [requests]);
  const recentDocuments = useMemo(() => [...documents].sort((a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime()).slice(0, 4), [documents]);
  const firstName = currentUser.full_name.split(" ")[0];
  const submitQuestion = (event: React.FormEvent) => { event.preventDefault(); if (question.trim()) onNavigate("assistant", question.trim()); };

  return <div className="professional-page">
    <PageHeader eyebrow={company?.name || "Company workspace"} title={`Good day, ${firstName}`} description="Your current authorized work, requests, and company records." />
    {!dataLoaded && <div className="loading-state"><span className="pulse-indicator" /> Loading workspace summary…</div>}
    {Object.keys(dataErrors).length > 0 && <Notice tone="error">Some workspace data could not be loaded: {Object.values(dataErrors).join(" ")} <button type="button" className="notice-retry" onClick={onRefresh}>Retry</button></Notice>}

    <section className="overview-metrics" aria-label="Workspace summary">
      <button type="button" onClick={() => onNavigate("work")}><span><CheckSquare size={16} /> Active tasks</span><strong>{dataLoaded && !dataErrors.tasks ? activeTasks.length : "—"}</strong><small>Open work visible to you</small></button>
      <button type="button" onClick={() => onNavigate("requests")}><span><ShieldCheck size={16} /> Pending requests</span><strong>{dataLoaded && !dataErrors.requests ? pendingRequests.length : "—"}</strong><small>Submitted or assigned records</small></button>
      <button type="button" onClick={() => onNavigate("files")}><span><FileText size={16} /> Documents</span><strong>{dataLoaded && !dataErrors.documents ? documents.length : "—"}</strong><small>Records you can access</small></button>
    </section>

    <section className="question-panel" aria-labelledby="ask-records-title">
      <div><h2 id="ask-records-title">Search company knowledge</h2><p>Answers are saved with the source records used.</p></div>
      <form onSubmit={submitQuestion}><label><Search size={16} /><span className="sr-only">Question</span><input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a question about authorized company records" /></label><button type="submit" className="btn-primary" disabled={!question.trim()}>Ask <ArrowRight size={14} /></button></form>
    </section>

    {pendingRequests.length > 0 && <section className="overview-section">
      <div className="section-title-row"><div><h2>Requests needing attention</h2><p>Submitted or assigned records in your current view.</p></div><button type="button" className="text-link" onClick={() => onNavigate("requests")}>Open requests <ArrowRight size={13} /></button></div>
      <div className="compact-register">{pendingRequests.slice(0, 3).map((request) => <button type="button" key={request.id} onClick={() => onNavigate("requests", undefined, request.id)}><span><strong>{request.title}</strong><small>{request.request_type.replaceAll("_", " ")} · {request.requester_name || "Requester"}</small></span><StatusLabel value={request.status} /></button>)}</div>
    </section>}

    <div className="overview-columns professional-overview-columns">
      <section className="overview-section">
        <div className="section-title-row"><div><h2>Active work</h2><p>Most recent tasks in your authorized queue.</p></div><button type="button" className="text-link" onClick={() => onNavigate("work")}>View all <ArrowRight size={13} /></button></div>
        {!dataLoaded || dataErrors.tasks ? <div className="loading-state">Work summary unavailable.</div> : activeTasks.length === 0 ? <EmptyState title="No active tasks" description="Open tasks will appear here." /> : <div className="compact-register">{activeTasks.slice(0, 5).map((task) => <button type="button" key={task.id} onClick={() => onNavigate("work")}><span><strong>{task.title}</strong><small>{task.project_name} · {task.assigned_to_name || "Assigned to you"}</small></span><StatusLabel value={task.status} /></button>)}</div>}
      </section>
      <section className="overview-section">
        <div className="section-title-row"><div><h2>Recently updated documents</h2><p>Source records currently visible to you.</p></div><button type="button" className="text-link" onClick={() => onNavigate("files")}>View all <ArrowRight size={13} /></button></div>
        {!dataLoaded || dataErrors.documents ? <div className="loading-state">Document summary unavailable.</div> : recentDocuments.length === 0 ? <EmptyState title="No documents" description="Authorized documents will appear here." /> : <div className="compact-register">{recentDocuments.map((document) => <button type="button" key={document.id} onClick={() => onNavigate("files", undefined, document.id)}><span><strong>{document.title}</strong><small>{document.filename} · L{document.clearance_level}</small></span><StatusLabel value={document.status} /></button>)}</div>}
      </section>
    </div>
  </div>;
};
