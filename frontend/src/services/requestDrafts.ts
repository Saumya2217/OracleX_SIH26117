import type { BusinessRequest, BusinessRequestDetail, BusinessRequestType, User } from "../types";

export type RequestForm = {
  request_type: BusinessRequestType;
  title: string;
  description: string;
  risk_level: BusinessRequest["risk_level"];
  assigned_reviewer_id: string | null;
  fields: Record<string, unknown>;
};
export type PendingRequest = { kind: "new"; form: RequestForm } | {
  kind: "record"; record: BusinessRequestDetail; form: RequestForm; actionNote: string; cancelNote: string;
};

export const requestDraftScope = (user: Pick<User, "company_id" | "id">) => JSON.stringify([user.company_id, user.id]);
export const newRequestForm = (request_type: BusinessRequestType = "CONTROLLED_CHANGE"): RequestForm => ({ request_type, title: "", description: "", risk_level: "MEDIUM", assigned_reviewer_id: null, fields: {} });
export const requestFormFromRecord = (record: BusinessRequest): RequestForm => ({ request_type: record.request_type, title: record.title, description: record.description, risk_level: record.risk_level, assigned_reviewer_id: record.assigned_reviewer_id ?? null, fields: record.current_payload ?? {} });
export const isNewRequestDirty = (form: RequestForm) => Boolean(form.title.trim() || form.description.trim() || form.request_type !== "CONTROLLED_CHANGE" || form.risk_level !== "MEDIUM" || form.assigned_reviewer_id
  || Object.values(form.fields).some((value) => typeof value === "string" ? Boolean(value.trim()) : value != null));

// Deliberately memory-only. Request text is never written to browser storage.
export function createRequestDraftStore() {
  const scopes = new Map<string, Map<string, PendingRequest>>();
  const listeners = new Set<() => void>();
  let revision = 0;
  const changed = () => { revision++; for (const listener of listeners) listener(); };
  const remove = (scope: string, key: string) => {
    if (!scopes.get(scope)?.delete(key)) return;
    if (!scopes.get(scope)?.size) scopes.delete(scope);
    changed();
  };
  return {
    subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; },
    getSnapshot: () => revision,
    list(scope: string) { return structuredClone(Array.from(scopes.get(scope)?.entries() ?? [])); },
    get(scope: string, key: string) { const value = scopes.get(scope)?.get(key); return value ? structuredClone(value) : undefined; },
    put(scope: string, key: string, value: PendingRequest) {
      if (JSON.stringify(scopes.get(scope)?.get(key)) === JSON.stringify(value)) return;
      const items = scopes.get(scope) ?? new Map<string, PendingRequest>();
      items.set(key, structuredClone(value)); scopes.set(scope, items); changed();
    },
    remove,
    removeIfUnchanged(scope: string, key: string, expected: PendingRequest | undefined) {
      if (JSON.stringify(scopes.get(scope)?.get(key)) === JSON.stringify(expected)) remove(scope, key);
    },
    clear(scope: string) { if (scopes.delete(scope)) changed(); },
  };
}

export const requestDrafts = createRequestDraftStore();
