import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Pencil, Plus, RefreshCw, Search, Trash2 } from "lucide-react";
import { api } from "../services/api";
import { User } from "../types";
import type { ApiSchema } from "../types/openapi.generated";
import { Dialog } from "../components/ui/Dialog";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Notice } from "../components/ui/Notice";
import { PageHeader } from "../components/ui/PageHeader";

interface DepartmentsPageProps { currentUser: User; }
type Department = ApiSchema<"DepartmentResponse">;

export const DepartmentsPage: React.FC<DepartmentsPageProps> = ({ currentUser }) => {
  const [departments, setDepartments] = useState<Department[] | null>(null);
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<Department | "new" | null>(null);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try { const items = await api.getDepartments(); setError(null); setDepartments(items); }
    catch (cause: unknown) { setError(cause instanceof Error ? cause.message : "Teams could not be loaded."); }
  }, []);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    api.getDepartments(controller.signal).then((items) => { if (active) setDepartments(items); }).catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : "Teams could not be loaded."); });
    return () => { active = false; controller.abort(); };
  }, []);

  const filtered = useMemo(() => (departments || []).filter((department) => {
    const needle = query.trim().toLowerCase();
    return !needle || [department.name, department.code, department.description].some((value) => value?.toLowerCase().includes(needle));
  }), [departments, query]);
  const openNew = () => { setName(""); setCode(""); setDescription(""); setEditing("new"); };
  const openEdit = (department: Department) => { setName(department.name); setCode(department.code); setDescription(department.description || ""); setEditing(department); };
  const save = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError(null); setSuccess(null);
    try {
      const payload = { name: name.trim(), code: code.trim().toUpperCase(), description: description.trim() };
      if (editing === "new") { await api.createDepartment(payload); setSuccess("Team created."); }
      else if (editing) { await api.updateDepartment(editing.id, payload); setSuccess("Team updated."); }
      setEditing(null); await load();
    } catch (cause: unknown) { setError(cause instanceof Error ? cause.message : "The team could not be saved."); }
    finally { setBusy(false); }
  };
  const remove = async (department: Department) => {
    if (!window.confirm(`Delete ${department.name}? This succeeds only when no company records still reference the team.`)) return;
    setBusy(true); setError(null); setSuccess(null);
    try { await api.deleteDepartment(department.id); setSuccess("Team deleted."); await load(); }
    catch (cause: unknown) { setError(cause instanceof Error ? cause.message : "The team could not be deleted."); }
    finally { setBusy(false); }
  };

  return <div className="professional-page">
    <PageHeader eyebrow="Organization" title="Teams" description="Maintain the company units used for people, documents, and task boundaries."
      actions={<><button type="button" className="btn-secondary" onClick={() => { api.invalidateCache(); void load(); }}><RefreshCw size={14} /> Refresh</button>{currentUser.is_admin && <button type="button" className="btn-primary" onClick={openNew}><Plus size={15} /> New team</button>}</>} />
    {error && departments !== null && <Notice tone="error" onDismiss={() => setError(null)}>{error}</Notice>}
    {success && <Notice tone="success" onDismiss={() => setSuccess(null)}>{success}</Notice>}
    <section className="register-panel">
      <div className="register-toolbar"><label className="search-field"><Search size={15} /><span className="sr-only">Search teams</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search team name, code, or purpose" /></label><span className="record-count">{departments?.length ?? 0} teams</span></div>
      {departments === null && (error ? <ErrorState title="Teams could not be loaded" description={error} onRetry={() => void load()} /> : <div className="loading-state"><span className="pulse-indicator" /> Loading teams…</div>)}
      {departments !== null && filtered.length === 0 && <EmptyState title={query ? "No matching teams" : "No teams configured"} description={query ? "Try a different search." : "Administrators can add the first company team."} />}
      {departments !== null && filtered.length > 0 && <div className="data-table-wrap"><table className="data-table teams-table"><thead><tr><th>Team</th><th>Code</th><th>Purpose</th>{currentUser.is_admin && <th><span className="sr-only">Actions</span></th>}</tr></thead><tbody>{filtered.map((department) => <tr key={department.id}><td><strong>{department.name}</strong></td><td><span className="code-label">{department.code}</span></td><td>{department.description || "No description"}</td>{currentUser.is_admin && <td><div className="row-actions"><button className="icon-button" type="button" onClick={() => openEdit(department)} aria-label={`Edit ${department.name}`}><Pencil size={14} /></button><button className="icon-button danger-icon" type="button" disabled={busy} onClick={() => void remove(department)} aria-label={`Delete ${department.name}`}><Trash2 size={14} /></button></div></td>}</tr>)}</tbody></table></div>}
    </section>
    {editing && <Dialog title={editing === "new" ? "Create team" : "Edit team"} description="Use a short, stable code because other company records may reference it." onClose={() => setEditing(null)} footer={<><button type="button" className="btn-secondary" onClick={() => setEditing(null)}>Cancel</button><button type="submit" form="team-form" className="btn-primary" disabled={busy || !name.trim() || !code.trim()}>{busy ? "Saving…" : "Save team"}</button></>}>
      {error && <Notice tone="error">{error}</Notice>}
      <form id="team-form" className="form-stack" onSubmit={save}><label>Team name<input className="input-control" value={name} onChange={(event) => setName(event.target.value)} required /></label><label>Team code<input className="input-control code-input" value={code} onChange={(event) => setCode(event.target.value.toUpperCase())} required maxLength={20} /></label><label>Purpose<textarea className="input-control" rows={4} value={description} onChange={(event) => setDescription(event.target.value)} /></label></form>
    </Dialog>}
  </div>;
};
