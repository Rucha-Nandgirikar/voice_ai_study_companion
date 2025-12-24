import { BACKEND_URL } from "./config";

function originOnly(raw: string): string {
  const u = new URL(raw);
  return u.origin;
}

export async function extractUrl(params: { url: string }) {
  const base = originOnly(BACKEND_URL);
  const endpoint = `${base}/extract`;
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params)
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Extract failed (${res.status}) @ ${endpoint}: ${text}`);
  }
  return await res.json();
}



