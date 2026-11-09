import React, { useEffect, useState } from "react";
import { KeyRound, RefreshCw } from "lucide-react";
import { api } from "../services/api";
import type { ApiSchema } from "../types/openapi.generated";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Notice } from "../components/ui/Notice";
import { PageHeader } from "../components/ui/PageHeader";

type RoleRecord = ApiSchema<"RoleResponse">;

export const RolesPage: React.FC = () => {
  const [roles, setRoles] = useState<RoleRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = async () => { setError(null); try { const items = await api.getRoles(); setRoles(items); } catch (cause: unknown) { setError(cause instanceof Error ? cause.message : "Roles could not be loaded."); } };
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    api.getRoles(controller.signal).then((items) => { if (active) setRoles(items); }).catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : "Roles could not be loaded."); });
    return () => { active = false; controller.abort(); };
  }, []);
  return <div className="professional-page">
    <PageHeader eyebrow="Access control" title="Roles" description="Review the permission scopes and default document clearance attached to company roles." actions={<button type="button" className="btn-secondary" onClick={() => { api.invalidateCache(); void load(); }}><RefreshCw size={14} /> Refresh</button>} />
    <section className="register-panel">
      {roles === null && (error ? <ErrorState title="Roles could not be loaded" description={error} onRetry={() => void load()} /> : <div className="loading-state"><span className="pulse-indicator" /> Loading roles…</div>)}
      {roles !== null && error && <Notice tone="error" onDismiss={() => setError(null)}>{error}</Notice>}
      {roles !== null && roles.length === 0 && <EmptyState title="No roles configured" description="Role templates will appear here when configured." />}
      {roles !== null && roles.length > 0 && <div className="role-register">{roles.map((role) => <article key={role.id}><header><span><KeyRound size={15} /></span><div><h2>{role.name}</h2><p>{role.code} · Default clearance L{role.clearance_level ?? 1}</p></div></header>{role.description && <p className="role-description">{role.description}</p>}<div className="permission-list">{role.permissions?.length ? role.permissions.map((permission) => <span key={permission}>{permission}</span>) : <em>No permission scopes</em>}</div></article>)}</div>}
    </section>
    <p className="page-footnote">Role definitions are read only in this release. Administrators can assign configured roles from the People page.</p>
  </div>;
};
