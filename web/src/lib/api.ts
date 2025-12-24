import { BACKEND_URL } from "./config";

function originOnly(raw: string): string {
  const u = new URL(raw);
  return u.origin;
}

export async function urlAnalyze(params: { sessionId: string; url: string }) {
  const base = originOnly(BACKEND_URL);
  const endpoint = `${base}/url/analyze`;
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params)
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`URL analyze failed (${res.status}) @ ${endpoint}: ${text}`);
  }
  return await res.json();
}

export async function getSignedUrl(params: { agentId: string }) {
  const base = originOnly(BACKEND_URL);
  const endpoint = `${base}/elevenlabs/signed_url`;
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params)
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Signed URL failed (${res.status}) @ ${endpoint}: ${text}`);
  }
  return await res.json();
}


