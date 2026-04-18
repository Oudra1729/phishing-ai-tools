const BASE = import.meta.env.VITE_API_BASE || "";

async function parseJson(res) {
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    return { error: text || "Invalid JSON" };
  }
}

export async function fetchHealth() {
  const res = await fetch(`${BASE}/health`);
  return parseJson(res);
}

export async function predict(payload) {
  const res = await fetch(`${BASE}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await parseJson(res);
  return { ok: res.ok, status: res.status, data };
}

export async function explain(url) {
  const res = await fetch(`${BASE}/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ url }),
  });
  const data = await parseJson(res);
  return { ok: res.ok, status: res.status, data };
}

export async function fetchExamples() {
  const res = await fetch(`${BASE}/examples`);
  const data = await parseJson(res);
  return { ok: res.ok, data };
}

/** Rough URL extraction (first match) — aligned with backend heuristics for UX */
export function firstUrlFromText(text) {
  if (!text) return null;
  const m = text.match(/https?:\/\/[^\s<>"']+|www\.[^\s<>"']+/i);
  return m ? m[0] : null;
}
