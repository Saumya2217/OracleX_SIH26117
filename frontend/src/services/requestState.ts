import type { BusinessRequest, User } from "../types";
import { hasPermission } from "./permissions.ts";

export function requestActions(user: User, record: BusinessRequest) {
  const owner = record.requester_id === user.id;
  const reviewer = hasPermission(user, "workflow:approve");
  const awaitingDecision = ["SUBMITTED", "ASSIGNED"].includes(record.status);
  return {
    edit: owner && record.status === "DRAFT",
    assign: reviewer && !owner && awaitingDecision && (!record.assigned_reviewer_id || record.assigned_reviewer_id === user.id || Boolean(user.is_admin)),
    decide: reviewer && !owner && awaitingDecision && (!record.assigned_reviewer_id || record.assigned_reviewer_id === user.id || Boolean(user.is_admin)),
    complete: reviewer && record.status === "APPROVED",
    cancel: owner && ["DRAFT", "SUBMITTED", "ASSIGNED"].includes(record.status),
  };
}

type Draft = { title: string; description: string; risk_level: BusinessRequest["risk_level"]; assigned_reviewer_id?: string | null; fields: Record<string, unknown> };

const comparableFields = (fields: Record<string, unknown>) => JSON.stringify(
  Object.fromEntries(Object.entries(fields).filter(([, value]) => value != null).sort(([left], [right]) => left.localeCompare(right))),
);

export function requestDraftChanged(draft: Draft, record: BusinessRequest): boolean {
  return draft.title !== record.title || draft.description !== record.description || draft.risk_level !== record.risk_level
    || (draft.assigned_reviewer_id ?? null) !== (record.assigned_reviewer_id ?? null)
    || comparableFields(draft.fields) !== comparableFields(record.current_payload ?? {});
}
