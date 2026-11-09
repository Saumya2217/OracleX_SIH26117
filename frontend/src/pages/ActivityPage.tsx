import React, { useCallback, useEffect, useRef, useState } from "react";
import { RefreshCw, Search, ShieldCheck } from "lucide-react";
import { AuditLogItem, User } from "../types";
import type { ApiSchema } from "../types/openapi.generated";
import { api } from "../services/api";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Notice } from "../components/ui/Notice";
import { PageHeader } from "../components/ui/PageHeader";
import { Pagination } from "../components/ui/Pagination";
import { StatusLabel } from "../components/ui/StatusLabel";

interface ActivityPageProps { currentUser: User; }
type IntegrityResult = ApiSchema<"AuditIntegrityResponse">;
const PAGE_SIZE = 25;

export const ActivityPage: React.FC<ActivityPageProps> = ({ currentUser }) => {
  const canView = currentUser.is_admin || Boolean(currentUser.role?.permissions?.includes("audit:view"));
  const [logs, setLogs] = useState<AuditLogItem[] | null>(null);
  const [actionFilter, setActionFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [integrity, setIntegrity] = useState<IntegrityResult | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [appliedFilters, setAppliedFilters] = useState({ action: "", status: "" });
  const pageRequest = useRef<AbortController | null>(null);
  const moreRequest = useRef<AbortController | null>(null);
  const pageGeneration = useRef(0);

  const load = useCallback(async (action: string, status: string) => {
    if (!canView) return;
    pageRequest.current?.abort();
    moreRequest.current?.abort();
    const controller = new AbortController();
    pageRequest.current = controller;
    pageGeneration.current += 1;
    setLoadingMore(false);
    setError(null);
    try {
      const items = await api.getAuditLogs(action, status, controller.signal, undefined, PAGE_SIZE);
      if (controller.signal.aborted) return;
      setLogs(items);
      setHasMore(items.length === PAGE_SIZE);
      setAppliedFilters({ action, status });
    }
    catch (cause: unknown) {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Audit records could not be loaded.");
    }
  }, [canView]);
  useEffect(() => {
    if (!canView) return;
    const controller = new AbortController();
    pageRequest.current = controller;
    void api.getAuditLogs("", "", controller.signal, undefined, PAGE_SIZE).then((items) => {
      if (!controller.signal.aborted) { setLogs(items); setHasMore(items.length === PAGE_SIZE); }
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Audit records could not be loaded.");
    });
    return () => { pageRequest.current?.abort(); moreRequest.current?.abort(); };
  }, [canView]);

  const loadMore = async () => {
    if (!logs?.length || !hasMore || loadingMore) return;
    const last = logs[logs.length - 1];
    const generation = pageGeneration.current;
    const controller = new AbortController();
    moreRequest.current = controller;
    setLoadingMore(true);
    setError(null);
    try {
      const items = await api.getAuditLogs(appliedFilters.action, appliedFilters.status, controller.signal, { timestamp: last.timestamp, id: last.id }, PAGE_SIZE);
      if (controller.signal.aborted || generation !== pageGeneration.current) return;
      setLogs((current) => [...(current || []), ...items]);
      setHasMore(items.length === PAGE_SIZE);
    } catch (cause: unknown) {
      if (!controller.signal.aborted && generation === pageGeneration.current) setError(cause instanceof Error ? cause.message : "More audit records could not be loaded.");
    } finally { if (generation === pageGeneration.current) setLoadingMore(false); }
  };

  const verify = async () => {
    setVerifying(true); setError(null);
    try { setIntegrity(await api.verifyAuditIntegrity()); }
    catch (cause: unknown) { setError(cause instanceof Error ? cause.message : "The checksum verification could not be completed."); }
    finally { setVerifying(false); }
  };

  if (!canView) return <div className="professional-page"><PageHeader eyebrow="Compliance" title="Audit log" description="Company event records and record checksum verification." /><Notice tone="error">Your role does not include audit:view permission.</Notice></div>;

  return <div className="professional-page professional-page-wide">
    <PageHeader eyebrow="Compliance" title="Audit log" description="Review company event records and verify each stored record checksum."
      actions={<><button type="button" className="btn-secondary" onClick={() => void load(appliedFilters.action, appliedFilters.status)}><RefreshCw size={14} /> Refresh</button><button type="button" className="btn-primary" disabled={verifying} onClick={() => void verify()}><ShieldCheck size={15} /> {verifying ? "Verifying…" : "Verify checksums"}</button></>} />
    {error && logs !== null && <Notice tone="error" onDismiss={() => setError(null)}>{error}</Notice>}
    {integrity && <Notice tone={integrity.status === "TAMPER_DETECTED" ? "error" : "success"} onDismiss={() => setIntegrity(null)}>{integrity.status === "NO_RECORDS" ? "No records were available to verify." : integrity.status === "CHECKSUMS_VALID" ? `${integrity.valid_signatures} of ${integrity.total_records_checked} record checksums match.` : `${integrity.tampered_records.length} record checksums do not match.`} {integrity.scope}</Notice>}

    <section className="register-panel">
      <form className="register-toolbar audit-filters" onSubmit={(event) => { event.preventDefault(); void load(actionFilter, statusFilter); }}>
        <label className="search-field"><Search size={15} /><span className="sr-only">Filter by action</span><input value={actionFilter} onChange={(event) => setActionFilter(event.target.value)} placeholder="Filter action name" /></label>
        <label><span className="sr-only">Filter by status</span><select className="toolbar-select" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">All statuses</option><option value="SUCCESS">Success</option><option value="FAILURE">Failure</option><option value="DENIED">Denied</option></select></label>
        <button className="btn-secondary" type="submit">Apply filters</button>
      </form>
      {logs === null && (error ? <ErrorState title="Audit records could not be loaded" description={error} onRetry={() => void load(actionFilter, statusFilter)} /> : <div className="loading-state"><span className="pulse-indicator" /> Loading audit records…</div>)}
      {logs !== null && logs.length === 0 && <EmptyState title="No audit records" description="No records matched the current filters." />}
      {logs !== null && logs.length > 0 && <div className="data-table-wrap"><table className="data-table audit-table"><thead><tr><th>Time</th><th>Action</th><th>Actor</th><th>Resource</th><th>Status</th><th>Details</th></tr></thead><tbody>{logs.map((item) => <tr key={item.id}><td><time dateTime={item.timestamp}>{new Date(item.timestamp).toLocaleString()}</time></td><td><strong>{item.action.replaceAll("_", " ")}</strong></td><td>{item.user_email || "System"}<small>{item.user_role || ""}</small></td><td>{item.resource_type}<small>{item.resource_id ? item.resource_id.slice(0, 12) : "No resource ID"}</small></td><td><StatusLabel value={item.status} /></td><td><details className="audit-details"><summary>View</summary><dl><div><dt>Record ID</dt><dd>{item.id}</dd></div>{item.ip_address && <div><dt>IP address</dt><dd>{item.ip_address}</dd></div>}{item.clearance_at_action && <div><dt>Clearance</dt><dd>{item.clearance_at_action}</dd></div>}{item.integrity_hash && <div><dt>SHA-256</dt><dd>{item.integrity_hash}</dd></div>}{item.details && Object.keys(item.details).length > 0 && <div><dt>Event data</dt><dd><pre>{JSON.stringify(item.details, null, 2)}</pre></dd></div>}</dl></details></td></tr>)}</tbody></table></div>}
      {logs !== null && logs.length > 0 && <Pagination shown={logs.length} hasMore={hasMore} loading={loadingMore} onLoadMore={() => void loadMore()} />}
    </section>
  </div>;
};
