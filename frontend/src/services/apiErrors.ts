export class ApiError extends Error {
  public readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

export function apiErrorMessage(body: unknown, status: number): string {
  const fallback = `Request failed (${status}). Please try again.`;
  if (!body || typeof body !== "object" || !("detail" in body)) return fallback;
  const detail = body.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (!Array.isArray(detail)) return fallback;
  const messages = detail.slice(0, 5).flatMap((item: unknown) => {
    if (!item || typeof item !== "object" || !("msg" in item) || typeof item.msg !== "string") return [];
    const location = "loc" in item && Array.isArray(item.loc)
      ? item.loc.filter((part: unknown) => typeof part === "string" && !["body", "query", "header", "path"].includes(part)).join(" ").replaceAll("_", " ")
      : "";
    return [location ? `${location}: ${item.msg}` : item.msg];
  });
  return messages.length ? messages.join("; ") : fallback;
}
