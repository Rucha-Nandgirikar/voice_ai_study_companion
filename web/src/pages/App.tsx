import React, { useEffect, useState } from "react";
import { AGENT_ID } from "../lib/config";
import { extractUrl } from "../lib/api";

export function App() {
  const [url, setUrl] = useState<string>("");
  const [status, setStatus] = useState<string>("Paste a URL, click Analyze, then Start.");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [preview, setPreview] = useState<string>("");

  useEffect(() => {
    // Load ElevenLabs widget embed script once.
    const existing = document.querySelector<HTMLScriptElement>(
      'script[src="https://unpkg.com/@elevenlabs/convai-widget-embed"]'
    );
    if (existing) return;
    const s = document.createElement("script");
    s.src = "https://unpkg.com/@elevenlabs/convai-widget-embed";
    s.async = true;
    s.type = "text/javascript";
    document.body.appendChild(s);
  }, []);

  function openPage() {
    const u = url.trim();
    if (!u) {
      setStatus("Please paste a URL first.");
      return;
    }
    // Opening in the same tab would navigate away from the app (and the widget).
    // New tab lets the user read while the call UI stays open.
    window.open(u, "_blank", "noopener,noreferrer");
  }

  async function onAnalyze() {
    try {
      if (!url.trim()) {
        setStatus("Please paste a URL first.");
        return;
      }
      setIsAnalyzing(true);
      setStatus("Extracting main content…");
      const data = await extractUrl({ url: url.trim() });
      const cleaned = (data?.cleanedText || "") as string;
      setPreview(cleaned.slice(0, 600));
      setStatus(
        "Extracted! Now use the ElevenLabs widget below and say: “Summarize this page.”\n\nTip: If your agent has a tool, ask it to ‘fetch and summarize’ this URL."
      );
      openPage();
    } catch (e: any) {
      setStatus(`Analyze error: ${e?.message || String(e)}`);
    } finally {
      setIsAnalyzing(false);
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
          Backend: <code>{new URL(import.meta.env.VITE_BACKEND_URL || "http://localhost").origin}</code>
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
            <button className="secondary" onClick={openPage} disabled={!url.trim()}>
              Open page
            </button>
          </div>
          <div className="status">{status}</div>
        </div>

        {preview && (
          <div className="card" style={{ marginTop: 12 }}>
            <div style={{ fontWeight: 800, marginBottom: 6 }}>Extract preview</div>
            <div style={{ fontSize: 13, lineHeight: 1.4, whiteSpace: "pre-wrap" }}>{preview}</div>
          </div>
        )}
      </div>

      <div className="bottomBar">
        <div className="bottomInner">
          {!AGENT_ID ? (
            <div className="msg">
              <strong>Missing VITE_AGENT_ID.</strong> Set it in <code>web/.env</code> (local) or Vercel env vars.
            </div>
          ) : (
            <elevenlabs-convai agent-id={AGENT_ID}></elevenlabs-convai>
          )}
        </div>
      </div>
    </div>
  );
}


