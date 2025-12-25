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

export async function resetNotes(params: { url: string }) {
  const base = originOnly(BACKEND_URL);
  const endpoint = `${base}/notes/reset`;
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params)
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Notes reset failed (${res.status}) @ ${endpoint}: ${text}`);
  }
  return await res.json();
}

export async function downloadNotesDocx(params: { url: string }) {
  const base = originOnly(BACKEND_URL);
  const endpoint = `${base}/notes/download.docx?url=${encodeURIComponent(params.url)}`;
  const res = await fetch(endpoint);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Notes download failed (${res.status}) @ ${endpoint}: ${text}`);
  }
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "study-notes.docx";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1500);
}



