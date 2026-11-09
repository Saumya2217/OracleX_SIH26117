import assert from "node:assert/strict";
import test from "node:test";
import { createRequestDraftStore, requestDraftScope, newRequestForm, isNewRequestDirty } from "../src/services/requestDrafts.ts";
import { notificationDate, notificationRequestId } from "../src/services/notifications.ts";

const scope = requestDraftScope({ company_id: "company", id: "employee" });
const draft = () => ({ kind: "new", form: { ...newRequestForm("PURCHASE_REQUEST"), title: "QA", assigned_reviewer_id: "reviewer", fields: { estimated_cost: 0 } } });

test("notification timestamps interpret the API's naive UTC and preserve explicit offsets", () => {
  const expected = "2026-10-20T10:00:00.000Z";
  for (const value of ["2026-10-20T10:00:00", "2026-10-20T10:00:00Z", "2026-10-20T15:30:00+05:30"]) {
    assert.equal(notificationDate(value).toISOString(), expected);
  }
});

test("pending text stays within its account and company and clears on sign-out", () => {
  const store = createRequestDraftStore();
  store.put(scope, "new", draft());
  assert.equal(store.list(requestDraftScope({ company_id: "company", id: "other" })).length, 0);
  assert.equal(store.list(requestDraftScope({ company_id: "other", id: "employee" })).length, 0);
  store.clear(scope);
  assert.equal(store.list(scope).length, 0);
});

test("buffer snapshots survive page lifetimes without sharing mutable form references", () => {
  const store = createRequestDraftStore();
  const original = draft(); store.put(scope, "new", original);
  original.form.title = "Mutated";
  const restored = store.get(scope, "new");
  assert.equal(restored.form.title, "QA");
  assert.equal(restored.form.assigned_reviewer_id, "reviewer");
  restored.form.fields.estimated_cost = 99;
  assert.equal(store.get(scope, "new").form.fields.estimated_cost, 0);
  store.list(scope)[0][1].form.title = "Changed list snapshot";
  assert.equal(store.get(scope, "new").form.title, "QA");
  const version = store.getSnapshot();
  store.put(scope, "new", store.get(scope, "new"));
  assert.equal(store.getSnapshot(), version);
});

test("a late successful request cannot discard newer edits made in another page lifetime", () => {
  const store = createRequestDraftStore();
  store.put(scope, "new", draft());
  const submitted = store.get(scope, "new");
  store.put(scope, "new", { ...draft(), form: { ...draft().form, title: "Newer edits" } });
  store.removeIfUnchanged(scope, "new", submitted);
  assert.equal(store.get(scope, "new").form.title, "Newer edits");
  store.removeIfUnchanged(scope, "new", store.get(scope, "new"));
  assert.equal(store.get(scope, "new"), undefined);
});

test("blank new forms stay clean while zero values and chosen request types are retained", () => {
  assert.equal(isNewRequestDirty(newRequestForm()), false);
  assert.equal(isNewRequestDirty({ ...newRequestForm(), title: "   " }), false);
  assert.equal(isNewRequestDirty({ ...newRequestForm(), fields: { estimated_cost: 0 } }), true);
  assert.equal(isNewRequestDirty(newRequestForm("ACCESS_REQUEST")), true);
  assert.equal(isNewRequestDirty({ ...newRequestForm(), assigned_reviewer_id: "reviewer" }), true);
});

test("notification navigation accepts a request ID and never an external supplied link", () => {
  const id = "93a6de68-1df2-4859-bdec-0584b8389965";
  assert.equal(notificationRequestId({ request_id: id, deep_link: "https://untrusted.example" }), id);
  for (const request_id of [null, "", "https://untrusted.example", "../admin", "javascript:alert(1)"]) {
    assert.equal(notificationRequestId({ request_id }), null);
  }
});
