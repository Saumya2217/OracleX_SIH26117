import assert from "node:assert/strict";
import test from "node:test";
import { ScopedQueryCache } from "../src/services/queryCache.ts";

test("cached data cannot cross company or user scope", async () => {
  const cache = new ScopedQueryCache();
  let calls = 0;
  const fetcher = async () => ++calls;
  cache.setScope("company-a", "user-a");
  assert.equal(await cache.load("tasks", fetcher, { maxAgeMs: 30_000 }), 1);
  assert.equal(await cache.load("tasks", fetcher, { maxAgeMs: 30_000 }), 1);
  cache.setScope("company-a", "user-b");
  assert.equal(await cache.load("tasks", fetcher, { maxAgeMs: 30_000 }), 2);
  cache.setScope("company-b", "user-b");
  assert.equal(await cache.load("tasks", fetcher, { maxAgeMs: 30_000 }), 3);
});

test("a write invalidation refreshes an older read before it reaches the caller", async () => {
  const cache = new ScopedQueryCache();
  cache.setScope("company-a", "user-a");
  let resolveOld;
  let calls = 0;
  const old = cache.load("tasks", () => {
    calls += 1;
    return calls === 1 ? new Promise((resolve) => { resolveOld = resolve; }) : Promise.resolve("fresh");
  }, { maxAgeMs: 30_000, restartOnInvalidate: true });
  cache.invalidate();
  resolveOld("stale");
  assert.equal(await old, "fresh");
  assert.equal(calls, 2);
  assert.equal(await cache.load("tasks", async () => "wrong", { maxAgeMs: 30_000 }), "fresh");
});

test("invalidation aborts and retries a pending read that honors cancellation", async () => {
  const cache = new ScopedQueryCache();
  cache.setScope("company-a", "user-a");
  let calls = 0;
  const read = cache.load("people", (signal) => {
    calls += 1;
    if (calls === 2) return Promise.resolve("updated");
    return new Promise((_, reject) => signal.addEventListener(
      "abort", () => reject(new DOMException("Cancelled", "AbortError")), { once: true },
    ));
  }, { restartOnInvalidate: true });
  cache.invalidate();
  assert.equal(await read, "updated");
  assert.equal(calls, 2);
});

test("logout and page cancellation abort outstanding reads", async () => {
  const cache = new ScopedQueryCache();
  cache.setScope("company-a", "user-a");
  const waitForAbort = (signal) => new Promise((_, reject) => {
    signal.addEventListener("abort", () => reject(new DOMException("Cancelled", "AbortError")), { once: true });
  });
  const logoutRead = cache.load("tasks", waitForAbort, { maxAgeMs: 30_000 });
  cache.clear();
  await assert.rejects(logoutRead, { name: "AbortError" });

  cache.setScope("company-a", "user-a");
  const page = new AbortController();
  const pageRead = cache.load("roles", waitForAbort, { signal: page.signal, maxAgeMs: 30_000 });
  page.abort();
  await assert.rejects(pageRead, { name: "AbortError" });
  assert.equal(await cache.load("roles", async () => "current", { maxAgeMs: 30_000 }), "current");
});
