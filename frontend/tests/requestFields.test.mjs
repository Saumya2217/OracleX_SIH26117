import assert from "node:assert/strict";
import test from "node:test";
import { readTextField, readNumberField, updateRequestField } from "../src/services/requestFields.ts";

test("request fields render only supported scalar values and preserve zero cost", () => {
  const payload = { resource: { nested: "not input text" }, quantity: "12", estimated_cost: 0, vendor: "Supplier" };
  assert.equal(readTextField(payload, "resource"), "");
  assert.equal(readTextField(payload, "vendor"), "Supplier");
  assert.equal(readNumberField(payload, "quantity"), "");
  assert.equal(readNumberField(payload, "estimated_cost"), 0);
  assert.equal(readNumberField({ quantity: Infinity }, "quantity"), "");
});

test("editing or clearing one field preserves all other payload data", () => {
  const payload = { item: "Printer", quantity: 2, metadata: { reference: "retained" } };
  const edited = updateRequestField(payload, "quantity", null);
  assert.equal(edited.quantity, null);
  assert.deepEqual(edited.metadata, payload.metadata);
  assert.equal(edited.item, "Printer");
  assert.equal(payload.quantity, 2);
});
