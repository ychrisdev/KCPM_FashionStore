const FALLBACK = "Đã xảy ra lỗi. Vui lòng thử lại.";

function collectString(data: string, out: string[]): void {
  const t = data.trim();
  if (t) out.push(t);
}

function collectDetail(detail: unknown, out: string[]): boolean {
  if (typeof detail === "string") { collectString(detail, out); return true; }
  if (Array.isArray(detail)) { for (const item of detail) collectParts(item, out); return true; }
  return false;
}

function collectObject(o: Record<string, unknown>, out: string[]): void {
  if (collectDetail(o.detail, out)) return;
  for (const [k, v] of Object.entries(o)) {
    if (k === "detail") continue;
    collectParts(v, out);
  }
}

function collectParts(data: unknown, out: string[]): void {
  if (data == null) return;
  if (typeof data === "string") { collectString(data, out); return; }
  if (Array.isArray(data)) { for (const item of data) collectParts(item, out); return; }
  if (typeof data === "object") collectObject(data as Record<string, unknown>, out);
}

/** Flatten DRF-style errors (kể cả lồng như `user.email`) thành một chuỗi. */
export function parseApiFieldErrors(data: unknown): string {
  const out: string[] = [];
  collectParts(data, out);
  return out.length ? out.join(" ") : FALLBACK;
}
