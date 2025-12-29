import { BACKEND_URL } from "./config";

function originOnly(raw: string): string {
  const u = new URL(raw);
  return u.origin;
}

export async function getTopics(params: { url: string }) {
  const base = originOnly(BACKEND_URL);
  const endpoint = `${base}/topics`;
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Topics failed (${res.status}) @ ${endpoint}: ${text}`);
  }
  return await res.json();
}

export async function startSession(params: { url: string; selectedTopics: string[] }) {
  const base = originOnly(BACKEND_URL);
  const endpoint = `${base}/sessions/start`;
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Session start failed (${res.status}) @ ${endpoint}: ${text}`);
  }
  return await res.json();
}

export async function downloadNotesDocx(params: { sessionId: string }) {
  const base = originOnly(BACKEND_URL);
  const endpoint = `${base}/notes/download.docx?sessionId=${encodeURIComponent(params.sessionId)}`;
  const res = await fetch(endpoint);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Notes download failed (${res.status}) @ ${endpoint}: ${text}`);
  }
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${params.sessionId}.docx`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1500);
}

export async function getNotes(params: { sessionId: string }) {
  const base = originOnly(BACKEND_URL);
  const endpoint = `${base}/notes?sessionId=${encodeURIComponent(params.sessionId)}`;
  const res = await fetch(endpoint);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Notes get failed (${res.status}) @ ${endpoint}: ${text}`);
  }
  return await res.json();
}

export async function getSessions(params?: { limit?: number }) {
  const base = originOnly(BACKEND_URL);
  const limit = params?.limit ?? 50;
  const endpoint = `${base}/sessions?limit=${encodeURIComponent(String(limit))}`;
  const res = await fetch(endpoint);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Sessions get failed (${res.status}) @ ${endpoint}: ${text}`);
  }
  return await res.json();
}

export async function getLatestSession(params: { url: string }) {
  const base = originOnly(BACKEND_URL);
  const endpoint = `${base}/sessions/latest?url=${encodeURIComponent(params.url)}`;
  const res = await fetch(endpoint);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Latest session get failed (${res.status}) @ ${endpoint}: ${text}`);
  }
  return await res.json();
}

export async function deleteSession(params: { sessionId: string }) {
  const base = originOnly(BACKEND_URL);
  const endpoint = `${base}/sessions?sessionId=${encodeURIComponent(params.sessionId)}`;
  const res = await fetch(endpoint, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Sessions delete failed (${res.status}) @ ${endpoint}: ${text}`);
  }
  return await res.json();
}



