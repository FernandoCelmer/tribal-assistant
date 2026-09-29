export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export function errorText(error: unknown, status: number): string {
  const detail = (error as { detail?: unknown } | undefined)?.detail;
  if (!detail) return `HTTP ${status}`;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => (d as { msg?: string }).msg ?? String(d)).join("; ");
  return (detail as { message?: string }).message ?? JSON.stringify(detail);
}
