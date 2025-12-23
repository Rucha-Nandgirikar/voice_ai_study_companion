export async function analyzePage(params: {
  backendUrl: string;
  sessionId: string;
  url: string;
  cleanedText: string;
}) {
  const { backendUrl, sessionId, url, cleanedText } = params;
  const res = await fetch(`${backendUrl.replace(/\/$/, "")}/page/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sessionId, url, cleanedText })
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Backend error (${res.status}): ${text}`);
  }
  return await res.json();
}

export async function getElevenLabsSignedUrl(params: { backendUrl: string; agentId: string }) {
  const { backendUrl, agentId } = params;
  const res = await fetch(`${backendUrl.replace(/\/$/, "")}/elevenlabs/signed_url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agentId })
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Signed URL error (${res.status}): ${text}`);
  }
  return await res.json();
}


