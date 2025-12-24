import React, { useMemo, useState } from "react";
import { useConversation } from "@elevenlabs/react";
import { AGENT_ID } from "../lib/config";
import { getSignedUrl, urlAnalyze } from "../lib/api";

type Msg = { role: "user" | "agent"; text: string };

export function App() {
  const sessionId = useMemo(() => crypto.randomUUID(), []);
  const [url, setUrl] = useState<string>("");
  const [status, setStatus] = useState<string>("Paste a URL, click Analyze, then Start.");
  const [topics, setTopics] = useState<string[]>([]);
  const [summary, setSummary] = useState<string>("");
  const [chat, setChat] = useState<Msg[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const conversation = useConversation({
    agentId: AGENT_ID || undefined,
    onMessage: (m: any) => {
      const role = (m?.role || m?.speaker || "").toString().toLowerCase();
      const text = (m?.text || m?.message || m?.content || "").toString();
      if (!text) return;
      setChat((prev) => [...prev, { role: role.includes("user") ? "user" : "agent", text }].slice(-30));
    },
    onError: (e: any) => setStatus(`Agent error: ${e?.message || String(e)}`)
  });

  const isConnected = !!(conversation as any)?.isSessionActive;
  const agentStatus = ((conversation as any)?.status || "unknown").toString();

  async function onAnalyze() {
    try {
      if (!url.trim()) {
        setStatus("Please paste a URL first.");
        return;
      }
      setIsAnalyzing(true);
      setStatus("Analyzing URL…");
      const data = await urlAnalyze({ sessionId, url: url.trim() });
      setSummary(data?.summary || "");
      setTopics((data?.topics || []).slice(0, 12));
      setStatus("Analyzed. Click Start and say: “Summarize this page.”");
    } catch (e: any) {
      setStatus(`Analyze error: ${e?.message || String(e)}`);
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function onStart() {
    try {
      if (!AGENT_ID) {
        setStatus("Missing VITE_AGENT_ID. Set it in web/.env or Vercel env vars.");
        return;
      }
      await navigator.mediaDevices.getUserMedia({ audio: true });
      setStatus("Starting voice session…");
      const { signedUrl } = await getSignedUrl({ agentId: AGENT_ID });
      await (conversation as any).startSession?.({ signedUrl });
      setStatus("Connected. Ask a question (voice).");
    } catch (e: any) {
      setStatus(`Start error: ${e?.message || String(e)}`);
    }
  }

  async function onStop() {
    try {
      setStatus("Stopping…");
      await (conversation as any).stopSession?.();
      setStatus("Stopped.");
    } catch (e: any) {
      setStatus(`Stop error: ${e?.message || String(e)}`);
    }
  }

  return (
    <div className="page">
      <div className="header">
        <div>
          <h1>Voice AI Study Companion</h1>
          <div className="muted">Paste URL → Gemini analyzes → ElevenLabs voice tutor</div>
        </div>
        <div className="muted">
          Session: <code>{sessionId.slice(0, 8)}</code> · Agent: <code>{agentStatus}</code>
        </div>
      </div>

      <div className="content">
        <div className="card">
          <label>Paste a tutorial URL</label>
          <div className="row">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://…"
            />
            <button onClick={onAnalyze} disabled={isAnalyzing}>
              {isAnalyzing ? "Analyzing…" : "Analyze"}
            </button>
          </div>
          <div className="status">{status}</div>
        </div>

        {summary && (
          <div className="card" style={{ marginTop: 12 }}>
            <div style={{ fontWeight: 800, marginBottom: 6 }}>Summary</div>
            <div style={{ fontSize: 13, lineHeight: 1.4 }}>{summary}</div>
          </div>
        )}

        {topics.length > 0 && (
          <div className="card" style={{ marginTop: 12 }}>
            <div style={{ fontWeight: 800, marginBottom: 6 }}>Topics</div>
            <ul className="topics">
              {topics.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="bottomBar">
        <div className="bottomInner">
          <button onClick={onStart} disabled={isConnected}>
            Start call
          </button>
          <button className="secondary" onClick={onStop} disabled={!isConnected}>
            Stop
          </button>
          <div className="chatStrip">
            {chat.length === 0 ? (
              <div className="msg">
                <strong>Tip:</strong> After starting, say “Summarize this page” then “Start with &lt;topic&gt;”.
              </div>
            ) : (
              chat.slice(-6).map((m, i) => (
                <div className="msg" key={i}>
                  <strong>{m.role}:</strong> {m.text}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


