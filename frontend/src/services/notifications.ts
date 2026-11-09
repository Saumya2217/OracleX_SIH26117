import type { InternalNotification } from "../types";

// Legacy API timestamps are UTC without a suffix. Preserve an explicit offset.
export function notificationDate(value: string): Date {
  return new Date(/(?:Z|[+-]\d{2}:\d{2})$/i.test(value) ? value : `${value}Z`);
}

export function notificationRequestId(item: Pick<InternalNotification, "request_id">): string | null {
  // Never navigate to a supplied deep_link URL. Build a local request route instead.
  return typeof item.request_id === "string" && /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i.test(item.request_id) ? item.request_id : null;
}
