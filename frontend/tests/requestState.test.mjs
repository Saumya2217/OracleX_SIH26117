import assert from "node:assert/strict";
import test from "node:test";
import { requestActions, requestDraftChanged } from "../src/services/requestState.ts";
import { hasPermission } from "../src/services/permissions.ts";

const employee = { id: "owner", is_active: true, role: { permissions: ["workflow:trigger"] } };
const reviewer = { id: "reviewer", is_active: true, role: { permissions: ["workflow:approve"] } };
const record = { requester_id: "owner", status: "SUBMITTED", assigned_reviewer_id: null };

test("request controls respect ownership and the assigned reviewer", () => {
  assert.equal(requestActions(employee, record).decide, false);
  assert.equal(requestActions(reviewer, record).assign, true);
  assert.equal(requestActions(reviewer, { ...record, assigned_reviewer_id: "other" }).decide, false);
  assert.equal(requestActions(reviewer, { ...record, status: "ASSIGNED", assigned_reviewer_id: "other" }).assign, false);
  assert.equal(requestActions(reviewer, { ...record, status: "ASSIGNED", assigned_reviewer_id: "reviewer" }).assign, true);
  assert.equal(requestActions(reviewer, { ...record, assigned_reviewer_id: "reviewer" }).decide, true);
  const ownerWithReview = { ...reviewer, id: "owner" };
  assert.equal(requestActions(ownerWithReview, record).assign, false);
  assert.equal(requestActions(ownerWithReview, record).decide, false);
  assert.equal(requestActions({ ...reviewer, is_admin: true }, { ...record, assigned_reviewer_id: "other" }).decide, true);
});

test("approval, completion and cancellation remain distinct", () => {
  assert.equal(requestActions(reviewer, record).complete, false);
  assert.equal(requestActions(reviewer, { ...record, status: "APPROVED" }).complete, true);
  assert.equal(requestActions(employee, { ...record, status: "APPROVED" }).complete, false);
  assert.equal(requestActions(employee, record).cancel, true);
  assert.equal(requestActions(reviewer, record).cancel, false);
  for (const status of ["APPROVED", "REJECTED", "COMPLETED", "CANCELLED"]) {
    assert.equal(requestActions(employee, { ...record, status }).cancel, false);
    assert.equal(requestActions(reviewer, { ...record, status }).decide, false);
  }
});

test("dirty drafts preserve zero and compare cleared fields with normalized saved payloads", () => {
  const saved = { title: "QA", description: "Synthetic request", risk_level: "LOW", current_payload: { quantity: 1, estimated_cost: 0 } };
  const draft = { ...saved, fields: { estimated_cost: 0, quantity: 1, vendor: null } };
  assert.equal(requestDraftChanged(draft, saved), false);
  assert.equal(requestDraftChanged({ ...draft, fields: { quantity: 1, estimated_cost: null } }, saved), true);
  assert.equal(requestDraftChanged({ ...draft, fields: { ...draft.fields, quantity: 2 } }, saved), true);
  assert.equal(requestDraftChanged({ ...draft, title: "Changed" }, saved), true);
  assert.equal(requestDraftChanged({ ...draft, assigned_reviewer_id: "reviewer" }, saved), true);
  assert.equal(requestDraftChanged(draft, { ...saved, assigned_reviewer_id: "reviewer" }), true);
  assert.equal(requestDraftChanged({ ...draft, description: "Changed" }, saved), true);
  assert.equal(requestDraftChanged({ ...draft, risk_level: "HIGH" }, saved), true);
});

test("capabilities come from permissions or active administrator status, not clearance", () => {
  assert.equal(hasPermission({ ...employee, clearance_level: 4 }, "doc:upload"), false);
  assert.equal(hasPermission({ ...employee, is_admin: true }, "doc:upload"), true);
  assert.equal(hasPermission({ ...employee, is_admin: true, is_active: false }, "doc:upload"), false);
  assert.equal(hasPermission(null, "doc:upload"), false);
});
