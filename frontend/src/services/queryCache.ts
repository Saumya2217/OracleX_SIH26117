interface CacheEntry {
  value: unknown;
  expiresAt: number;
}

interface PendingQuery {
  controller: AbortController;
  signal?: AbortSignal;
  onAbort?: () => void;
  restartOnInvalidate: boolean;
  invalidated: boolean;
}

export class ScopedQueryCache {
  private scope: string | null = null;
  private epoch = 0;
  private entries = new Map<string, CacheEntry>();
  private pending = new Set<PendingQuery>();

  setScope(companyId: string, userId: string): void {
    const next = JSON.stringify([companyId, userId]);
    if (this.scope === next) return;
    this.clear();
    this.scope = next;
  }

  clear(): void {
    this.epoch += 1;
    for (const query of this.pending) query.controller.abort();
    this.entries.clear();
    this.scope = null;
  }

  invalidate(): void {
    this.epoch += 1;
    this.entries.clear();
    for (const query of this.pending) {
      if (query.restartOnInvalidate) {
        query.invalidated = true;
        query.controller.abort();
      }
    }
  }

  async load<T>(
    key: string,
    fetcher: (signal: AbortSignal) => Promise<T>,
    options: { signal?: AbortSignal; maxAgeMs?: number; force?: boolean; restartOnInvalidate?: boolean } = {},
  ): Promise<T> {
    const cacheKey = this.scope ? `${this.scope}:${key}` : null;
    const maxAgeMs = options.maxAgeMs ?? 0;
    if (options.signal?.aborted) throw new DOMException("Request cancelled", "AbortError");
    if (cacheKey && maxAgeMs > 0 && !options.force) {
      const cached = this.entries.get(cacheKey);
      if (cached && cached.expiresAt > Date.now()) return cached.value as T;
    }

    for (let attempt = 0; attempt < 3; attempt += 1) {
      const query: PendingQuery = {
        controller: new AbortController(),
        signal: options.signal,
        restartOnInvalidate: options.restartOnInvalidate ?? false,
        invalidated: false,
      };
      if (options.signal) {
        query.onAbort = () => query.controller.abort();
        options.signal.addEventListener("abort", query.onAbort, { once: true });
      }
      this.pending.add(query);
      const epoch = this.epoch;
      const scope = this.scope;
      let outcome: { ok: true; value: T } | { ok: false; error: unknown };
      try {
        outcome = { ok: true, value: await fetcher(query.controller.signal) };
      } catch (error) {
        outcome = { ok: false, error };
      } finally {
        if (query.signal && query.onAbort) query.signal.removeEventListener("abort", query.onAbort);
        this.pending.delete(query);
      }
      if (query.invalidated && this.scope === scope && !options.signal?.aborted) continue;
      if (query.controller.signal.aborted) throw new DOMException("Request cancelled", "AbortError");
      if (!outcome.ok) throw outcome.error;
      if (cacheKey && maxAgeMs > 0 && !query.controller.signal.aborted && this.epoch === epoch && this.scope === scope) {
        this.entries.set(cacheKey, { value: outcome.value, expiresAt: Date.now() + maxAgeMs });
      }
      return outcome.value;
    }
    throw new DOMException("Request invalidated repeatedly", "AbortError");
  }
}

export const queryCache = new ScopedQueryCache();
