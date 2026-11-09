import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Pencil, Plus, RefreshCw, Search, UserRoundCheck, UserRoundX } from "lucide-react";
import { api } from "../services/api";
import { User } from "../types";
import { Dialog } from "../components/ui/Dialog";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Notice } from "../components/ui/Notice";
import { PageHeader } from "../components/ui/PageHeader";
import { StatusLabel } from "../components/ui/StatusLabel";

interface PeoplePageProps { currentUser: User; }
interface Department { id: string; name: string; code: string; }
interface Role { id: string; name: string; code: string; }
type PersonForm = { fullName: string; email: string; password: string; jobTitle: string; employeeCode: string; departmentId: string; roleId: string; clearanceLevel: number; isAdmin: boolean; };
const emptyForm = (): PersonForm => ({ fullName: "", email: "", password: "", jobTitle: "", employeeCode: "", departmentId: "", roleId: "", clearanceLevel: 2, isAdmin: false });

export const PeoplePage: React.FC<PeoplePageProps> = ({ currentUser }) => {
  const [users, setUsers] = useState<User[] | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ACTIVE" | "ALL" | "INACTIVE">("ACTIVE");
  const [editing, setEditing] = useState<User | "new" | null>(null);
  const [form, setForm] = useState<PersonForm>(emptyForm());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [people, departmentList, roleList] = await Promise.all([api.getUsers(), api.getDepartments(), api.getRoles()]);
      setError(null); setUsers(people); setDepartments(departmentList); setRoles(roleList);
    } catch (cause: unknown) { setError(cause instanceof Error ? cause.message : "The people directory could not be loaded."); }
  }, []);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    Promise.all([api.getUsers(controller.signal), api.getDepartments(controller.signal), api.getRoles(controller.signal)]).then(([people, departmentList, roleList]) => { if (active) { setUsers(people); setDepartments(departmentList); setRoles(roleList); } }).catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : "The people directory could not be loaded."); });
    return () => { active = false; controller.abort(); };
  }, []);

  const filtered = useMemo(() => (users || []).filter((person) => {
    const active = person.is_active !== false;
    if (statusFilter === "ACTIVE" && !active) return false;
    if (statusFilter === "INACTIVE" && active) return false;
    const needle = query.trim().toLowerCase();
    return !needle || [person.full_name, person.email, person.job_title, person.employee_code, person.department?.name, person.role?.name].some((value) => value?.toLowerCase().includes(needle));
  }), [query, statusFilter, users]);

  const openNew = () => {
    setForm(emptyForm());
    setEditing("new");
  };
  const openEdit = (person: User) => {
    setForm({ fullName: person.full_name, email: person.email, password: "", jobTitle: person.job_title || "", employeeCode: person.employee_code || "", departmentId: person.department_id || "", roleId: person.role_id || "", clearanceLevel: person.clearance_level || 1, isAdmin: person.is_admin === true });
    setEditing(person);
  };
  const save = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError(null); setSuccess(null);
    try {
      if (editing === "new") {
        await api.createUser({ full_name: form.fullName.trim(), email: form.email.trim(), password: form.password, job_title: form.jobTitle.trim() || undefined, employee_code: form.employeeCode.trim() || undefined, department_id: form.departmentId || undefined, role_id: form.roleId || undefined, clearance_level: form.clearanceLevel, is_admin: form.isAdmin });
        setSuccess("Person added to the company directory.");
      } else if (editing) {
        await api.updateUser(editing.id, { full_name: form.fullName.trim(), job_title: form.jobTitle.trim() || null, employee_code: form.employeeCode.trim() || null, department_id: form.departmentId || null, role_id: form.roleId || null, clearance_level: form.clearanceLevel, is_admin: form.isAdmin });
        setSuccess("Profile updated.");
      }
      setEditing(null); await load();
    } catch (cause: unknown) { setError(cause instanceof Error ? cause.message : "The profile could not be saved."); }
    finally { setBusy(false); }
  };
  const toggleStatus = async (person: User) => {
    const action = person.is_active === false ? "reactivate" : "deactivate";
    if (!window.confirm(`${action === "reactivate" ? "Reactivate" : "Deactivate"} ${person.full_name}?`)) return;
    setBusy(true); setError(null); setSuccess(null);
    try { await api.toggleUserStatus(person.id); setSuccess(`${person.full_name} was ${action}d.`); await load(); }
    catch (cause: unknown) { setError(cause instanceof Error ? cause.message : "The account status could not be changed."); }
    finally { setBusy(false); }
  };

  return <div className="professional-page">
    <PageHeader eyebrow="Organization" title="People" description="Company contact, role, department, and account status records."
      actions={<><button type="button" className="btn-secondary" onClick={() => { api.invalidateCache(); void load(); }}><RefreshCw size={14} /> Refresh</button>{currentUser.is_admin && <button type="button" className="btn-primary" onClick={openNew}><Plus size={15} /> Add person</button>}</>} />
    {error && users !== null && <Notice tone="error" onDismiss={() => setError(null)}>{error}</Notice>}
    {success && <Notice tone="success" onDismiss={() => setSuccess(null)}>{success}</Notice>}

    <section className="register-panel">
      <div className="register-toolbar">
        <label className="search-field"><Search size={15} /><span className="sr-only">Search people</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search name, email, role, or team" /></label>
        <div className="segmented-control" aria-label="Account status filter">{(["ACTIVE", "ALL", "INACTIVE"] as const).map((value) => <button type="button" key={value} aria-pressed={statusFilter === value} className={statusFilter === value ? "active" : ""} onClick={() => setStatusFilter(value)}>{value === "INACTIVE" ? "Inactive" : value === "ACTIVE" ? "Active" : "All"}</button>)}</div>
      </div>
      {users === null && (error ? <ErrorState title="People could not be loaded" description={error} onRetry={() => void load()} /> : <div className="loading-state"><span className="pulse-indicator" /> Loading people…</div>)}
      {users !== null && filtered.length === 0 && <EmptyState title={query ? "No matching people" : "No people in this view"} description={query ? "Try a different search." : "Company accounts will appear here."} />}
      {users !== null && filtered.length > 0 && <div className="data-table-wrap"><table className="data-table people-table">
        <thead><tr><th>Person</th><th>Team</th><th>Role</th><th>Clearance</th><th>Status</th>{currentUser.is_admin && <th><span className="sr-only">Actions</span></th>}</tr></thead>
        <tbody>{filtered.map((person) => <tr key={person.id}>
          <td><div className="person-cell"><span className="person-initials" aria-hidden="true">{person.full_name.split(" ").filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase()}</span><span><strong>{person.full_name}{person.id === currentUser.id ? " (you)" : ""}</strong><small>{person.job_title || "No job title"} · {person.email}</small></span></div></td>
          <td>{person.department?.name || "Not assigned"}</td><td>{person.is_admin ? "Administrator" : person.role?.name || "Not assigned"}</td><td>L{person.clearance_level}</td>
          <td><StatusLabel value={person.is_active === false ? "INACTIVE" : "ACTIVE"} /></td>
          {currentUser.is_admin && <td><div className="row-actions"><button type="button" className="icon-button" onClick={() => openEdit(person)} aria-label={`Edit ${person.full_name}`}><Pencil size={14} /></button><button type="button" className="icon-button" disabled={busy || person.id === currentUser.id} onClick={() => void toggleStatus(person)} aria-label={`${person.is_active === false ? "Reactivate" : "Deactivate"} ${person.full_name}`}>{person.is_active === false ? <UserRoundCheck size={14} /> : <UserRoundX size={14} />}</button></div></td>}
        </tr>)}</tbody>
      </table></div>}
    </section>

    {editing && <Dialog title={editing === "new" ? "Add person" : "Edit profile"} description={editing === "new" ? "Create an account with an explicit role and document clearance." : `Update ${editing.full_name}'s company profile.`} onClose={() => setEditing(null)} footer={<><button type="button" className="btn-secondary" onClick={() => setEditing(null)}>Cancel</button><button type="submit" form="person-form" className="btn-primary" disabled={busy}>{busy ? "Saving…" : "Save"}</button></>}>
      {error && <Notice tone="error">{error}</Notice>}
      <form id="person-form" className="form-stack" onSubmit={save}>
        <div className="form-grid"><label>Full name<input className="input-control" value={form.fullName} onChange={(event) => setForm({ ...form, fullName: event.target.value })} required /></label><label>Employee code<input className="input-control" value={form.employeeCode} onChange={(event) => setForm({ ...form, employeeCode: event.target.value })} /></label></div>
        {editing === "new" && <><label>Email<input type="email" className="input-control" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required autoComplete="off" /></label><label>Temporary password<input type="password" className="input-control" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} minLength={12} required autoComplete="new-password" /><small>Use at least 12 characters and share it through your approved company channel.</small></label></>}
        <label>Job title<input className="input-control" value={form.jobTitle} onChange={(event) => setForm({ ...form, jobTitle: event.target.value })} /></label>
        <div className="form-grid"><label>Team<select className="input-control" value={form.departmentId} onChange={(event) => setForm({ ...form, departmentId: event.target.value })}><option value="">Not assigned</option>{departments.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label><label>Role<select className="input-control" value={form.roleId} onChange={(event) => setForm({ ...form, roleId: event.target.value })}><option value="">Not assigned</option>{roles.map((role) => <option key={role.id} value={role.id}>{role.name}</option>)}</select></label></div>
        <div className="form-grid"><label>Document clearance<select className="input-control" value={form.clearanceLevel} onChange={(event) => setForm({ ...form, clearanceLevel: Number(event.target.value) })}><option value={1}>L1 · Public</option><option value={2}>L2 · Internal</option><option value={3}>L3 · Confidential</option><option value={4}>L4 · Restricted</option></select></label><label className="checkbox-field"><input type="checkbox" checked={form.isAdmin} onChange={(event) => setForm({ ...form, isAdmin: event.target.checked })} /> Company administrator</label></div>
      </form>
    </Dialog>}
  </div>;
};
