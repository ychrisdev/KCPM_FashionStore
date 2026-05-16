const FALLBACK = "Đã xảy ra lỗi. Vui lòng thử lại.";

function collectParts(data: unknown, out: string[]): void {
  if (data == null) return;
  if (typeof data === "string") {
    const t = data.trim();
    if (t) out.push(t);
    return;
  }
  if (Array.isArray(data)) {
    for (const item of data) collectParts(item, out);
    return;
  }
  if (typeof data === "object") {
    const o = data as Record<string, unknown>;
    if (typeof o.detail === "string") {
      const t = o.detail.trim();
      if (t) out.push(t);
      return;
    }
    if (Array.isArray(o.detail)) {
      for (const item of o.detail) collectParts(item, out);
      return;
    }
    for (const [k, v] of Object.entries(o)) {
      if (k === "detail") continue;
      collectParts(v, out);
    }
  }
}

/** Flatten DRF-style errors (kể cả lồng như `user.email`) thành một chuỗi. */
export function parseApiFieldErrors(data: unknown): string {
  const out: string[] = [];
  collectParts(data, out);
  return out.length ? out.join(" ") : FALLBACK;
}
