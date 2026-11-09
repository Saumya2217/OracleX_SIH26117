import assert from "node:assert/strict";
import test from "node:test";
import { apiErrorMessage, ApiError } from "../src/services/apiErrors.ts";

test("validation errors show field names without echoed input", () => {
  const message = apiErrorMessage({ detail: [
    { loc: ["body", "password"], msg: "String should have at least 12 characters", input: "private-input" },
    { loc: ["body", "payload", "end_date"], msg: "Input should be a valid date" },
  ] }, 422);
  assert.equal(message, "password: String should have at least 12 characters; payload end date: Input should be a valid date");
  assert.equal(message.includes("private-input"), false);
});

test("malformed error bodies produce a useful fallback and preserve HTTP status", () => {
  assert.equal(apiErrorMessage({ detail: [{ input: "untrusted" }] }, 503), "Request failed (503). Please try again.");
  assert.equal(apiErrorMessage(null, 502), "Request failed (502). Please try again.");
  const error = new ApiError(403, apiErrorMessage({ detail: "Access denied." }, 403));
  assert.equal(error.status, 403);
  assert.equal(error.message, "Access denied.");
});
