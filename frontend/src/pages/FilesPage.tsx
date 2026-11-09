import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Archive, Clock3, FileText, History, RefreshCw, RotateCcw, Search, ShieldCheck, Trash2, Upload, X } from "lucide-react";
import { api } from "../services/api";
import { DocumentDetail, DocumentItem, IngestionJobItem, User } from "../types";
import type { ApiSchema } from "../types/openapi.generated";
import { ErrorState } from "../components/ui/ErrorState";
import { ModalSurface } from "../components/ui/ModalSurface";
import { hasPermission } from "../services/permissions";

interface FilesPageProps {
  user: User | null;
  initialDocumentId?: string;
  initialVersionId?: string;
  onDocumentChange?: (documentId?: string, versionId?: string) => void;
}

const RUNNING = new Set(["QUEUED", "SCANNING", "PARSING", "INDEXING"]);
const RETRYABLE = new Set(["FAILED", "RETRYABLE"]);
const EMPTY_DOCUMENTS: DocumentItem[] = [];
const STATUS_LABELS: Record<string, string> = { INDEXED: "Ready", READY: "Ready", QUEUED: "Queued", SCANNING: "Scanning", PARSING: "Extracting", INDEXING: "Indexing", RETRYABLE: "Needs retry", FAILED: "Failed", ARCHIVED: "Archived", SUPERSEDED: "Superseded", SUCCEEDED: "Complete" };
const statusLabel = (value: string) => STATUS_LABELS[value] || value.replaceAll("_", " ");
const fileSize = (bytes: number) => bytes < 1024 ? `${bytes} B` : bytes < 1048576 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1048576).toFixed(1)} MB`;

export const FilesPage: React.FC<FilesPageProps> = ({ user, initialDocumentId, initialVersionId, onDocumentChange }) => {
  const [documents, setDocuments] = useState<DocumentItem[] | null>(null);
  const [activeTab, setActiveTab] = useState<"ALL" | "MY" | "ARCHIVED">("ALL");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ApiSchema<"VectorSearchResultItem">[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "error" | "success"; text: string } | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadClearance, setUploadClearance] = useState(1);
  const [uploadAudience, setUploadAudience] = useState<"company" | "department">(user?.department_id ? "department" : "company");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTags, setUploadTags] = useState("");
  const [uploading, setUploading] = useState(false);
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailRevision, setDetailRevision] = useState(0);
  const detailController = useRef<AbortController | null>(null);
  useEffect(() => () => detailController.current?.abort(), []);
  const [chunks, setChunks] = useState<ApiSchema<"DocumentChunkResponse">[]>([]);
  const [replacementFile, setReplacementFile] = useState<File | null>(null);
  const documentList = documents ?? EMPTY_DOCUMENTS;
  const loading = documents === null && !loadError;

  const loadDocuments = useCallback(async (_quiet = false) => {
    setLoadError(null);
    try { setDocuments(await api.getDocuments(true)); }
    catch (error: unknown) { setLoadError(error instanceof Error ? error.message : "Documents could not be loaded."); }
  }, []);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    api.getDocuments(true, controller.signal)
      .then((items) => { if (active) setDocuments(items); })
      .catch((error: unknown) => { if (active) setLoadError(error instanceof Error ? error.message : "Documents could not be loaded."); });
    return () => { active = false; controller.abort(); };
  }, []);
  useEffect(() => {
    if (!documentList.some((item) => RUNNING.has(item.status))) return;
    const timer = window.setInterval(() => void loadDocuments(true), 2500);
    return () => window.clearInterval(timer);
  }, [documentList, loadDocuments]);

  const filtered = useMemo(() => documentList.filter((item) => {
    if (activeTab === "ARCHIVED") return item.status === "ARCHIVED";
    if (item.status === "ARCHIVED") return false;
    return activeTab !== "MY" || item.uploaded_by_id === user?.id;
  }), [activeTab, documentList, user?.id]);
  const counts = useMemo(() => ({
    active: documentList.filter((item) => item.status !== "ARCHIVED").length,
    mine: documentList.filter((item) => item.status !== "ARCHIVED" && item.uploaded_by_id === user?.id).length,
    archived: documentList.filter((item) => item.status === "ARCHIVED").length,
  }), [documentList, user?.id]);
  const latestJob = detail?.jobs[0];
  const canManage = (item: DocumentItem) => Boolean(user?.is_admin || item.uploaded_by_id === user?.id);

  const handleSearch = async () => {
    if (!query.trim()) { setResults(null); return; }
    setSearching(true);
    setResults(null); setMessage(null);
    try { setResults(await api.searchKnowledge(query, 8)); }
    catch (error: unknown) { setMessage({ type: "error", text: error instanceof Error ? error.message : "Search failed." }); }
    finally { setSearching(false); }
  };

  const openDetail = async (item: DocumentItem) => {
    detailController.current?.abort();
    const controller = new AbortController();
    detailController.current = controller;
    setBusyId(item.id);
    try {
      const record = await api.getDocumentDetail(item.id, controller.signal);
      if (controller.signal.aborted) return;
      setMessage(null); setDetailError(null);
      setDetail(record); setReplacementFile(null); setChunks([]);
      onDocumentChange?.(record.document.id, record.document.current_version_id ?? undefined);
    } catch (error: unknown) {
      if (!controller.signal.aborted) setMessage({ type: "error", text: error instanceof Error ? error.message : "Document details could not be loaded." });
    } finally {
      if (detailController.current === controller) { detailController.current = null; setBusyId(null); }
    }
  };
  useEffect(() => {
    detailController.current?.abort();
    if (!initialDocumentId) return;
    const controller = new AbortController();
    let timer: number | undefined;
    const refresh = async () => {
      try {
        const record = await api.getDocumentDetail(initialDocumentId, controller.signal);
        const versionExists = !initialVersionId || record.versions.some((version) => version.id === initialVersionId);
        const loadedChunks = record.document.status === "INDEXED" ? await api.getDocumentChunks(initialDocumentId, controller.signal) : [];
        if (controller.signal.aborted) return;
        setDetail(record); setChunks(loadedChunks); setDetailError(null);
        if (!versionExists) setMessage({ type: "error", text: "The requested document version was not found." });
        // A replacement can be processing while the document itself remains INDEXED.
        if (record.jobs.some((job) => ["QUEUED", "PROCESSING", "RETRYABLE"].includes(job.state))) {
          timer = window.setTimeout(() => void refresh(), 2500);
        } else void loadDocuments(true);
      } catch (error: unknown) {
        if (!controller.signal.aborted) setDetailError(error instanceof Error ? error.message : "Document details could not be loaded.");
      }
    };
    void refresh();
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [initialDocumentId, initialVersionId, detailRevision, loadDocuments]);
  const refreshDetail = async () => {
    setResults(null);
    setDetailRevision((revision) => revision + 1);
    await loadDocuments(true);
  };

  const submitUpload = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!uploadFile || !uploadTitle.trim()) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", uploadFile); form.append("title", uploadTitle.trim());
      form.append("clearance_level", String(uploadClearance));
      form.append("is_company_wide", String(uploadAudience === "company"));
      if (uploadAudience === "department" && user?.department_id) form.append("department_id", user.department_id);
      form.append("tags", uploadTags);
      const result = await api.uploadDocument(form);
      setShowUpload(false); setUploadFile(null); setUploadTitle(""); setUploadTags("");
      setMessage({ type: "success", text: `“${result.document.title}” was accepted and is being processed.` });
      await loadDocuments(true); await openDetail(result.document);
    } catch (error: unknown) { setMessage({ type: "error", text: error instanceof Error ? error.message : "Upload failed." }); }
    finally { setUploading(false); }
  };

  const submitReplacement = async () => {
    if (!detail || !replacementFile) return;
    setBusyId(detail.document.id);
    try {
      await api.uploadDocumentVersion(detail.document.id, replacementFile); setReplacementFile(null);
      setMessage({ type: "success", text: "Replacement accepted. The current version remains searchable until the new version is ready." });
      await refreshDetail();
    } catch (error: unknown) { setMessage({ type: "error", text: error instanceof Error ? error.message : "Replacement upload failed." }); }
    finally { setBusyId(null); }
  };
  const retryJob = async (job: IngestionJobItem) => {
    setBusyId(job.document_id);
    try { await api.retryIngestionJob(job.id); setMessage({ type: "success", text: "The failed job was queued again." }); await refreshDetail(); }
    catch (error: unknown) { setMessage({ type: "error", text: error instanceof Error ? error.message : "The job could not be retried." }); }
    finally { setBusyId(null); }
  };
  const archiveDocument = async (item: DocumentItem) => {
    setBusyId(item.id);
    try { await api.archiveDocument(item.id); setMessage({ type: "success", text: `“${item.title}” was archived and removed from search.` }); setDetail(null); onDocumentChange?.(); await loadDocuments(true); }
    catch (error: unknown) { setMessage({ type: "error", text: error instanceof Error ? error.message : "The document could not be archived." }); }
    finally { setBusyId(null); }
  };
  const restoreDocument = async (item: DocumentItem) => {
    setBusyId(item.id);
    try { await api.restoreDocument(item.id); setMessage({ type: "success", text: `“${item.title}” is searchable again.` }); setDetail(null); onDocumentChange?.(); await loadDocuments(true); }
    catch (error: unknown) { setMessage({ type: "error", text: error instanceof Error ? error.message : "The document could not be restored." }); }
    finally { setBusyId(null); }
  };
  const purgeDocument = async (item: DocumentItem) => {
    if (!window.confirm(`Permanently delete “${item.title}”, including every version and original? This cannot be undone.`)) return;
    setBusyId(item.id);
    try { await api.deleteDocument(item.id); setMessage({ type: "success", text: `“${item.title}” was permanently deleted.` }); setDetail(null); onDocumentChange?.(); await loadDocuments(true); }
    catch (error: unknown) { setMessage({ type: "error", text: error instanceof Error ? error.message : "Permanent deletion failed." }); }
    finally { setBusyId(null); }
  };

  const detailOpen = Boolean(detail && initialDocumentId === detail.document.id);
  const feedback = message && <div className={`knowledge-message is-${message.type}`} role={message.type === "error" ? "alert" : "status"}><span>{message.text}</span><button aria-label="Dismiss" onClick={() => setMessage(null)}><X size={14} /></button></div>;
  const currentVersion = detail?.versions.find((version) => version.id === detail.document.current_version_id);

  return <div className="knowledge-page">
    <header className="knowledge-header"><div><div className="eyebrow">Company knowledge</div><h1>Documents</h1><p>Controlled source files, processing history, and searchable versions.</p></div>{hasPermission(user, "doc:upload") && <button className="btn-primary" onClick={() => { setMessage(null); setShowUpload(true); }}><Upload size={15} /> Upload document</button>}</header>
    {!showUpload && !detailOpen && feedback}{!detailOpen && detailError && <ErrorState title="Document details could not be loaded" description={detailError} onRetry={() => setDetailRevision((revision) => revision + 1)} />}
    <section className="knowledge-toolbar">
      <div className="knowledge-search"><Search size={16} /><input aria-label="Search document contents" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => event.key === "Enter" && void handleSearch()} placeholder="Search the contents of active documents" />{results && <button className="text-button" onClick={() => { setQuery(""); setResults(null); }}>Clear</button>}<button className="btn-secondary" onClick={() => void handleSearch()} disabled={searching}>{searching ? "Searching" : "Search"}</button></div>
      <nav className="document-tabs" aria-label="Document filters">{([["ALL", "Active", counts.active], ["MY", "My uploads", counts.mine], ["ARCHIVED", "Archived", counts.archived]] as const).map(([id, label, count]) => <button key={id} aria-pressed={activeTab === id} className={activeTab === id ? "active" : ""} onClick={() => setActiveTab(id)}>{label}<span>{documents === null ? "—" : count}</span></button>)}</nav>
    </section>
    {results && <section className="search-results-panel"><div className="section-heading"><div><h2>Search results</h2><p>{results.length} authorized passages</p></div></div>{results.length ? results.map((result, index) => <article key={`${result.document_id}-${result.chunk_index}-${index}`} className="search-result-row"><div className="result-rank">{String(index + 1).padStart(2, "0")}</div><div><strong>{result.title}</strong><p>{result.content}</p></div><span>{Math.round((result.similarity_score || 0) * 100)}% match</span></article>) : <div className="empty-state">No authorized passages matched this search.</div>}</section>}
    <section className="document-register">
      <div className="register-heading"><div><h2>{activeTab === "ARCHIVED" ? "Archive" : activeTab === "MY" ? "My documents" : "Active register"}</h2><p>{documents === null ? loadError ? "Record count unavailable." : "Loading records…" : `${filtered.length} records`}</p></div><button className="icon-button" aria-label="Refresh documents" onClick={() => void loadDocuments()}><RefreshCw size={15} /></button></div>
      <div className="document-table-wrap"><table className="document-table"><thead><tr><th>Document</th><th>Classification</th><th>Versions</th><th>Status</th><th>Updated</th><th aria-label="Actions" /></tr></thead><tbody>{!loading && filtered.map((item) => <tr key={item.id}><td><button className="document-name" onClick={() => void openDetail(item)}><span><FileText size={16} /></span><span><strong>{item.title}</strong><small>{item.filename} · {fileSize(item.file_size)}</small></span></button></td><td><span className="classification"><ShieldCheck size={13} /> L{item.clearance_level} · {item.is_company_wide ? "Company" : "Department"}</span></td><td><strong>{item.version_count || 1} total</strong><small>{item.chunk_count} sections</small></td><td><span className={`status-chip status-${item.status.toLowerCase()}`}>{RUNNING.has(item.status) && <Clock3 size={12} />}{statusLabel(item.status)}</span></td><td>{new Date(item.updated_at || item.created_at).toLocaleDateString()}<small>{new Date(item.updated_at || item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</small></td><td><button className="btn-secondary compact" disabled={busyId === item.id} onClick={() => void openDetail(item)}>Open</button></td></tr>)}</tbody></table>{loading && <div className="empty-state">Loading document register…</div>}{loadError && <ErrorState title="Documents could not be loaded" description={loadError} onRetry={() => void loadDocuments()} />}{documents !== null && filtered.length === 0 && <div className="empty-state">No documents in this view.</div>}</div>
    </section>

    {showUpload && <ModalSurface className="upload-panel" labelledBy="upload-title" onClose={() => setShowUpload(false)} dismissible={!uploading}><div className="modal-heading"><div><div className="eyebrow">New source</div><h2 id="upload-title">Upload document</h2></div><button type="button" disabled={uploading} aria-label="Close upload document" className="icon-button" onClick={() => setShowUpload(false)}><X size={16} /></button></div>{feedback}<form onSubmit={submitUpload} className="form-stack"><label>Document title<input className="input-control" value={uploadTitle} onChange={(event) => setUploadTitle(event.target.value)} placeholder="Employee handbook 2026" required /></label><label>Source file<input className="input-control" type="file" accept=".pdf,.txt,.md,.csv,.xlsx" onChange={(event) => setUploadFile(event.target.files?.[0] || null)} required /><small>PDF, TXT, Markdown, CSV, or XLSX · maximum 25 MB</small></label><div className="form-grid"><label>Classification<select className="input-control" value={uploadClearance} onChange={(event) => setUploadClearance(Number(event.target.value))}><option value={1} disabled={!user?.is_admin && (user?.clearance_level ?? 1) < 1}>L1 · Public</option><option value={2} disabled={!user?.is_admin && (user?.clearance_level ?? 1) < 2}>L2 · Internal</option><option value={3} disabled={!user?.is_admin && (user?.clearance_level ?? 1) < 3}>L3 · Confidential</option><option value={4} disabled={!user?.is_admin && (user?.clearance_level ?? 1) < 4}>L4 · Restricted</option></select></label><label>Audience<select className="input-control" value={uploadAudience} onChange={(event) => setUploadAudience(event.target.value as "company" | "department")}><option value="department" disabled={!user?.department_id}>My department</option><option value="company">Entire company</option></select></label></div><label>Tags<input className="input-control" value={uploadTags} onChange={(event) => setUploadTags(event.target.value)} placeholder="policy, people, 2026" /></label><div className="form-note"><ShieldCheck size={15} /><span>The file is quarantined, validated, extracted, and indexed locally. It becomes searchable only after every stage succeeds.</span></div><div className="modal-actions"><button type="button" disabled={uploading} className="btn-secondary" onClick={() => setShowUpload(false)}>Cancel</button><button className="btn-primary" disabled={uploading}>{uploading ? "Submitting…" : "Submit for processing"}</button></div></form></ModalSurface>}

    {detail && initialDocumentId === detail.document.id && <ModalSurface className="detail-panel" labelledBy="detail-title" onClose={() => { setDetail(null); onDocumentChange?.(); }} dismissible={busyId !== detail.document.id}><div className="modal-heading detail-title"><div><div className="eyebrow">Document record</div><h2 id="detail-title">{detail.document.title}</h2><p>{detail.document.filename} · {fileSize(detail.document.file_size)}</p></div><button className="icon-button" disabled={busyId === detail.document.id} aria-label="Close document details" onClick={() => { setDetail(null); onDocumentChange?.(); }}><X size={16} /></button></div>{feedback}{detailError && <ErrorState title="Document updates could not be loaded" description={detailError} onRetry={() => setDetailRevision((revision) => revision + 1)} />}<div className="detail-summary" role="status" aria-live="polite"><div><span>Status</span><strong className={`status-chip status-${detail.document.status.toLowerCase()}`}>{statusLabel(detail.document.status)}</strong></div><div><span>Current version</span><strong>{currentVersion ? `v${currentVersion.version_number}` : "Not ready"}</strong></div><div><span>Classification</span><strong>L{detail.document.clearance_level}</strong></div><div><span>Indexed sections</span><strong>{detail.document.chunk_count}</strong></div></div>{latestJob && RETRYABLE.has(latestJob.state) && <div className="job-error"><div><strong>{latestJob.error_code || "Processing failed"}</strong><p>{latestJob.safe_error_message || "Review the source file and retry."}</p></div>{canManage(detail.document) && <button className="btn-secondary" disabled={busyId === detail.document.id} onClick={() => void retryJob(latestJob)}>Retry job</button>}</div>}<div className="detail-body"><section className="detail-section"><div className="section-heading"><div><h3><History size={15} /> Version history</h3><p>Immutable source and processing records</p></div></div><div className="version-list">{detail.versions.map((version) => { const job = detail.jobs.find((item) => item.version_id === version.id); return <div className={`version-row ${initialVersionId === version.id ? "selected-version" : ""}`} key={version.id} aria-current={initialVersionId === version.id ? "true" : undefined}><div className="version-number">v{version.version_number}</div><div><strong>{version.original_filename}</strong><small>{new Date(version.created_at).toLocaleString()} · {fileSize(version.file_size)}</small><small>{version.embedding_model} · {version.embedding_dimensions} dimensions</small>{version.safe_error_message && <p>{version.safe_error_message}</p>}</div><div><span className={`status-chip status-${version.status.toLowerCase()}`}>{statusLabel(version.status)}</span>{job && <small>{job.attempt_count}/{job.max_attempts} attempts</small>}</div></div>; })}</div>{canManage(detail.document) && detail.document.status !== "ARCHIVED" && <div className="replacement-box"><div><strong>Upload a replacement</strong><p>The current version stays active until this file passes processing.</p></div><input aria-label="Replacement source file" type="file" accept=".pdf,.txt,.md,.csv,.xlsx" onChange={(event) => setReplacementFile(event.target.files?.[0] || null)} /><button className="btn-secondary" disabled={!replacementFile || busyId === detail.document.id} onClick={() => void submitReplacement()}>Upload version</button></div>}</section><section className="detail-section preview-section"><div className="section-heading"><div><h3>Extracted content</h3><p>{chunks.length ? `${chunks.length} searchable sections` : "Available when processing completes"}</p></div></div><div className="chunk-list">{chunks.length ? chunks.map((chunk, index) => <article key={chunk.id || index}><span>Section {index + 1}{chunk.page_number ? ` · Page ${chunk.page_number}` : ""}</span><p>{chunk.content}</p></article>) : <div className="empty-state">No active content preview.</div>}</div></section></div>{canManage(detail.document) && <footer className="detail-actions">{detail.document.status === "ARCHIVED" ? <button className="btn-secondary" disabled={busyId === detail.document.id} onClick={() => void restoreDocument(detail.document)}><RotateCcw size={14} /> Restore</button> : <button className="btn-secondary" disabled={busyId === detail.document.id} onClick={() => void archiveDocument(detail.document)}><Archive size={14} /> Archive</button>}{user?.is_admin && <button className="danger-button" disabled={busyId === detail.document.id} onClick={() => void purgeDocument(detail.document)}><Trash2 size={14} /> Permanently delete</button>}</footer>}</ModalSurface>}
  </div>;
};

