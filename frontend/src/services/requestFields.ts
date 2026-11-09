export type RequestFields = Record<string, unknown>;

export function readTextField(fields: RequestFields, name: string): string {
  return typeof fields[name] === "string" ? fields[name] : "";
}

export function readNumberField(fields: RequestFields, name: string): number | "" {
  const value = fields[name];
  return typeof value === "number" && Number.isFinite(value) ? value : "";
}

export function updateRequestField(fields: RequestFields, name: string, value: string | number | null): RequestFields {
  return { ...fields, [name]: value };
}
