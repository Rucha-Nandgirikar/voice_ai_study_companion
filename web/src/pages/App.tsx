import React, { useEffect, useState } from "react";
import { AGENT_ID } from "../lib/config";
import { downloadNotesDocx, extractUrl, getNotes, resetNotes } from "../lib/api";
import { ElevenLabsConvaiPortal } from "../components/ElevenLabsConvaiPortal";

type Notes = {
  url: string;
  summary: string;
  qa: Array<{ q: string; a: string }>;
  quizzes: Array<{
    question: string;
    userAnswer?: string;
    correctAnswer?: string;
    explanation?: string;
  }>;
  updatedAt: string;
};

type SessionItem = {
  url: string;
  title: string;
  lastUsedAt: string;
};

const SESSIONS_KEY = "vasc_sessions_v1";

function safeTitleFromUrl(u: string): string {
  try {
    const url = new URL(u);
    const host = url.hostname.replace(/^www\./, "");
    const path = url.pathname && url.pathname !== "/" ? url.pathname : "";
    return (host + path).slice(0, 38);
  } catch {
    return u.slice(0, 38);
  }
}

function loadSessions(): SessionItem[] {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY);
    if (!raw) return [];
    const data = JSON.parse(raw);
    if (!Array.isArray(data)) return [];
    return data.filter((x) => x?.url && x?.title && x?.lastUsedAt);
  } catch {
    return [];
  }
}

function saveSessions(sessions: SessionItem[]) {
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions.slice(0, 50)));
}

export function App() {
  const [url, setUrl] = useState<string>("");
  const [status, setStatus] = useState<string>(
    "Paste a URL, click Analyze, then start a call with the ElevenLabs Agent (bottom-right) for a spoken summary and Gemini-powered tutoring, quizzes, etc."
  );
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [preview, setPreview] = useState<string>("");
  const [notes, setNotes] = useState<Notes | null>(null);
  const [isNotesAutoRefresh, setIsNotesAutoRefresh] = useState(false);
  const [sessions, setSessions] = useState<SessionItem[]>([]);

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

  useEffect(() => {
    setSessions(loadSessions());
  }, []);

  useEffect(() => {
    if (!isNotesAutoRefresh) return;
    const u = url.trim();
    if (!u) return;

    let cancelled = false;
    const tick = async () => {
      try {
        const data = (await getNotes({ url: u })) as Notes;
        if (!cancelled) setNotes(data);
      } catch {
        // ignore transient errors during deploys
      }
    };

    tick();
    const id = window.setInterval(tick, 4000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [isNotesAutoRefresh, url]);

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
      const u = url.trim();
      await resetNotes({ url: u });
      setNotes(null);
      setIsNotesAutoRefresh(true);
      setStatus("Extracting main content…");
      const data = await extractUrl({ url: u });
      const cleaned = (data?.cleanedText || "") as string;
      setPreview(cleaned.slice(0, 600));
      setStatus(
        "Extracted! Now use the ElevenLabs widget below and say: “Summarize this page.”\n\nTip: If your agent has a tool, ask it to ‘fetch and summarize’ this URL."
      );
      openPage();

      // Save to local sidebar history
      const now = new Date().toISOString();
      const item: SessionItem = { url: u, title: safeTitleFromUrl(u), lastUsedAt: now };
      setSessions((prev) => {
        const next = [item, ...prev.filter((x) => x.url !== u)];
        saveSessions(next);
        return next;
      });
    } catch (e: any) {
      setStatus(`Analyze error: ${e?.message || String(e)}`);
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function onSelectSession(u: string) {
    setUrl(u);
    setIsNotesAutoRefresh(true);
    setStatus("Loading notes…");
    try {
      const data = (await getNotes({ url: u })) as Notes;
      setNotes(data);
      setStatus("Notes loaded.");
    } catch (e: any) {
      setStatus(`Load notes error: ${e?.message || String(e)}`);
    }
  }

  function onDeleteSession(u: string) {
    setSessions((prev) => {
      const next = prev.filter((x) => x.url !== u);
      saveSessions(next);
      return next;
    });
    if (url.trim() === u) {
      setUrl("");
      setNotes(null);
      setPreview("");
      setIsNotesAutoRefresh(false);
      setStatus(
        "Paste a URL, click Analyze, then start a call with the ElevenLabs Agent (bottom-right) for a spoken summary and Gemini-powered tutoring, quizzes, etc."
      );
    }
  }

  async function onRefreshNotes() {
    try {
      const u = url.trim();
      if (!u) {
        setStatus("Paste a URL first (notes are saved per URL).");
        return;
      }
      setStatus("Refreshing notes…");
      const data = (await getNotes({ url: u })) as Notes;
      setNotes(data);
      setStatus("Notes refreshed.");
    } catch (e: any) {
      setStatus(`Refresh notes error: ${e?.message || String(e)}`);
    }
  }

  async function onDownloadNotes() {
    try {
      const u = url.trim();
      if (!u) {
        setStatus("Paste a URL first (notes are saved per URL).");
        return;
      }
      setStatus("Preparing notes download…");
      await downloadNotesDocx({ url: u });
      setStatus("Downloaded notes (study-notes.docx).");
    } catch (e: any) {
      setStatus(`Download notes error: ${e?.message || String(e)}`);
    }
  }

  return (
    <div className="page">
      <div className="header">
        <div>
          <h1>Voice AI Study Companion</h1>
          <div className="muted">
            Paste a URL → extract content → start a call → ElevenLabs Agent (Gemini brain) summarizes, tutors, and quizzes
          </div>
        </div>
        <div className="muted">
          Backend: <code>{new URL(import.meta.env.VITE_BACKEND_URL || "http://localhost").origin}</code>
        </div>
      </div>

      <div className="layout">
        <aside className="sidebar">
          <div className="sidebarTitle">Sessions</div>
          <div className="sessionList">
            {sessions.length === 0 ? (
              <div className="muted" style={{ fontSize: 12 }}>
                No sessions yet. Paste a URL and click Analyze.
              </div>
            ) : null}
            {sessions.map((s) => {
              const active = url.trim() === s.url;
              return (
                <div
                  key={s.url}
                  className={`sessionItem ${active ? "active" : ""}`}
                  onClick={() => onSelectSession(s.url)}
                  role="button"
                  tabIndex={0}
                >
                  <div className="sessionItemTop">
                    <div className="sessionTitle" title={s.url}>
                      {s.title}
                    </div>
                    <button
                      className="sessionDelete"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(s.url);
                      }}
                      aria-label="Delete session"
                      type="button"
                    >
                      ×
                    </button>
                  </div>
                  <div className="sessionMeta">{s.url}</div>
                </div>
              );
            })}
          </div>
        </aside>

        <main className="main">
          <div className="content">
            <div className="card">
              <label>Paste your URL here</label>
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
                <button className="secondary" onClick={onDownloadNotes} disabled={!url.trim()}>
                  Download notes
                </button>
                <button className="secondary" onClick={onRefreshNotes} disabled={!url.trim()}>
                  Refresh notes
                </button>
                {/* <button className="secondary" onClick={openPage} disabled={!url.trim()}>
                  Open page
                </button> */}
              </div>
              <div className="status">{status}</div>
            </div>

            {preview && (
              <div className="card" style={{ marginTop: 12 }}>
                <div style={{ fontWeight: 800, marginBottom: 6 }}>Extract preview</div>
                <div style={{ fontSize: 13, lineHeight: 1.4, whiteSpace: "pre-wrap" }}>{preview}</div>
              </div>
            )}

            <div className="card" style={{ marginTop: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
                <div style={{ fontWeight: 800 }}>Notes (auto-updates after you end the call)</div>
                <label className="muted" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <input
                    type="checkbox"
                    checked={isNotesAutoRefresh}
                    onChange={(e) => setIsNotesAutoRefresh(e.target.checked)}
                  />
                  Auto refresh
                </label>
              </div>
              <div className="muted" style={{ marginTop: 6 }}>
                {notes?.updatedAt ? (
                  <>
                    Last updated: <code>{notes.updatedAt}</code>
                  </>
                ) : (
                  <>No notes yet. Start a call and ask the agent to analyze, then hang up.</>
                )}
              </div>

              {notes?.summary ? (
                <div style={{ marginTop: 10 }}>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>Summary</div>
                  <div style={{ whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.4 }}>{notes.summary}</div>
                </div>
              ) : null}

              {notes?.qa?.length ? (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>Q&amp;A</div>
                  {notes.qa.map((pair, i) => (
                    <div key={i} style={{ marginBottom: 10 }}>
                      <div style={{ fontSize: 13 }}>
                        <strong>Q{i + 1}.</strong> {pair.q}
                      </div>
                      <div style={{ fontSize: 13, marginTop: 4 }}>
                        <strong>A{i + 1}.</strong> {pair.a}
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}

              {notes?.quizzes?.length ? (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontWeight: 700, marginBottom: 6 }}>Quizzes</div>
                  {notes.quizzes.map((qz, i) => (
                    <div key={i} style={{ marginBottom: 10 }}>
                      <div style={{ fontSize: 13 }}>
                        <strong>Quiz {i + 1}.</strong> {qz.question}
                      </div>
                      {qz.userAnswer ? (
                        <div style={{ fontSize: 13, marginTop: 4 }}>
                          <strong>Your answer:</strong> {qz.userAnswer}
                        </div>
                      ) : null}
                      {qz.correctAnswer ? (
                        <div style={{ fontSize: 13, marginTop: 4 }}>
                          <strong>Correct answer:</strong> {qz.correctAnswer}
                        </div>
                      ) : null}
                      {qz.explanation ? (
                        <div style={{ fontSize: 13, marginTop: 4 }}>
                          <strong>Explanation:</strong> {qz.explanation}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
        </main>
      </div>

      <div className="bottomBar">
        <div className="bottomInner">
          {!AGENT_ID ? (
            <div className="msg">
              {/* <strong>Missing VITE_AGENT_ID.</strong> Set it in <code>web/.env</code> (local) or Vercel env vars. */}
              <div className="muted" style={{ marginTop: 6 }}>
                Debug: <code>import.meta.env.VITE_AGENT_ID</code> is{" "}
                <code>{String(import.meta.env.VITE_AGENT_ID || "") || "(empty)"}</code>
              </div>
            </div>
          ) : (
            <>
              <div className="msg">
                <strong>Call widget:</strong> look for the floating ElevenLabs call button (bottom-right).
              </div>
              <ElevenLabsConvaiPortal agentId={AGENT_ID} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}


