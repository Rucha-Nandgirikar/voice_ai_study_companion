import React, { useEffect, useState } from "react";
import { AGENT_ID } from "../lib/config";
import {
  deleteSession,
  downloadNotesDocx,
  getTopics,
  startSession,
  getNotes,
  getSessions,
} from "../lib/api";
import { ElevenLabsConvaiPortal } from "../components/ElevenLabsConvaiPortal";

type Notes = {
  sessionId: string;
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
  sessionId: string;
  url: string;
  title: string;
  updatedAt: string;
};

type TopicItem = {
  level: number;
  title: string;
};

type TopicsResponse = {
  url: string;
  title?: string | null;
  topics: TopicItem[];
};

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

export function App() {
  const [url, setUrl] = useState<string>("");
  const [sessionId, setSessionId] = useState<string>("");
  const [status, setStatus] = useState<string>(
    "Paste a URL, click Start session, then start a call with the ElevenLabs Agent. During the call, paste the URL into chat and say “analyze”. The agent will write Summary / Q&A / Quizzes into Notes while you talk."
  );
  const [isStartingSession, setIsStartingSession] = useState(false);
  const [isLoadingTopics, setIsLoadingTopics] = useState(false);
  const [notes, setNotes] = useState<Notes | null>(null);
  const [isNotesAutoRefresh, setIsNotesAutoRefresh] = useState(false);
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [topics, setTopics] = useState<TopicsResponse | null>(null);
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);

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
    // Load sessions from backend (DB-backed).
    const load = async () => {
      try {
        const res = await getSessions({ limit: 50 });
        const items = Array.isArray(res?.sessions) ? res.sessions : [];
        setSessions(
          items
            .filter((x: any) => x?.url && x?.sessionId)
            .map((x: any) => ({
              sessionId: String(x.sessionId),
              url: String(x.url),
              title: safeTitleFromUrl(String(x.url)),
              updatedAt: String(x.updatedAt || ""),
            }))
        );
      } catch {
        // If backend is redeploying/unavailable, keep the current list.
      }
    };
    load();
  }, []);

  useEffect(() => {
    if (!isNotesAutoRefresh) return;
    const sid = sessionId.trim();
    if (!sid) return;

    let cancelled = false;
    const tick = async () => {
      try {
        const data = (await getNotes({ sessionId: sid })) as Notes;
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
  }, [isNotesAutoRefresh, sessionId]);

  function openPage() {
    const u = url.trim();
    if (!u) {
      setStatus("Please paste a URL first.");
      return;
    }
    // Opening in the same tab would navigate away from the app (and the widget).
    // A separate window lets the user arrange the page side-by-side with this app.
    const w = Math.min(1100, Math.max(900, window.screen.availWidth - 120));
    const h = Math.min(900, Math.max(700, window.screen.availHeight - 160));
    const left = Math.max(20, Math.round((window.screen.availWidth - w) / 2));
    const top = Math.max(20, Math.round((window.screen.availHeight - h) / 3));
    const features = [
      "noopener",
      "noreferrer",
      "popup=1",
      `width=${w}`,
      `height=${h}`,
      `left=${left}`,
      `top=${top}`,
    ].join(",");
    const opened = window.open(u, "_blank", features);
    if (!opened) {
      // Popup blocker fallback.
      window.open(u, "_blank", "noopener,noreferrer");
    }
  }

  async function onLoadTopics() {
    try {
      const u = url.trim();
      if (!u) {
        setStatus("Please paste a URL first.");
        return;
      }
      setIsLoadingTopics(true);
      setTopics(null);
      setSelectedTopics([]);
      setSessionId("");
      setStatus("Fetching topics…");
      const t = (await getTopics({ url: u })) as TopicsResponse;
      setTopics(t);
      setStatus("Topics loaded. Select up to 8 topics, then click Start session.");
    } catch (e: any) {
      setStatus(`Topics error: ${e?.message || String(e)}`);
    } finally {
      setIsLoadingTopics(false);
    }
  }

  async function onStartSession() {
    try {
      if (!url.trim()) {
        setStatus("Please paste a URL first.");
        return;
      }
      if (selectedTopics.length === 0) {
        setStatus("Select at least 1 topic (up to 8), then start the session.");
        return;
      }
      setIsStartingSession(true);
      const u = url.trim();
      setTopics(null);
      setIsNotesAutoRefresh(true);
      setStatus(
        "Session started.\n\nNext: Start the call (below), paste the URL into the conversation, and say “analyze”.\nThe agent should confirm your selected topics, then begin Topic 1 and write notes via set_summary / append_qa / append_quiz."
      );

      try {
        const sess = await startSession({ url: u, selectedTopics });
        setSessionId(String(sess?.sessionId || ""));
        // Load notes once immediately
        try {
          const n = (await getNotes({ sessionId: String(sess?.sessionId || "") })) as Notes;
          setNotes(n);
        } catch {
          setNotes(null);
        }
      } catch {
        // ignore (call can still proceed)
      }

      openPage();

      try {
        const res = await getSessions({ limit: 50 });
        const items = Array.isArray(res?.sessions) ? res.sessions : [];
        setSessions(
          items
            .filter((x: any) => x?.url && x?.sessionId)
            .map((x: any) => ({
              sessionId: String(x.sessionId),
              url: String(x.url),
              title: safeTitleFromUrl(String(x.url)),
              updatedAt: String(x.updatedAt || ""),
            }))
        );
      } catch {
        // ignore
      }
    } catch (e: any) {
      setStatus(`Start session error: ${e?.message || String(e)}`);
    } finally {
      setIsStartingSession(false);
    }
  }

  async function onSelectSession(u: string) {
    // legacy signature kept; now expects encoded "sessionId|url"
    const [sid, urlPart] = u.split("|", 2);
    const realSid = (sid || "").trim();
    const realUrl = (urlPart || "").trim();
    if (!realSid || !realUrl) return;

    setSessionId(realSid);
    setUrl(realUrl);
    setIsNotesAutoRefresh(true);
    setStatus("Loading notes…");
    // Helpful: open the URL so the user can read alongside the notes/call.
    try {
      const w = Math.min(1100, Math.max(900, window.screen.availWidth - 120));
      const h = Math.min(900, Math.max(700, window.screen.availHeight - 160));
      const left = Math.max(20, Math.round((window.screen.availWidth - w) / 2));
      const top = Math.max(20, Math.round((window.screen.availHeight - h) / 3));
      const features = [
        "noopener",
        "noreferrer",
        "popup=1",
        `width=${w}`,
        `height=${h}`,
        `left=${left}`,
        `top=${top}`,
      ].join(",");
      const opened = window.open(realUrl, "_blank", features);
      if (!opened) window.open(realUrl, "_blank", "noopener,noreferrer");
    } catch {
      // ignore
    }
    try {
      const res = await getSessions({ limit: 50 });
      const items = Array.isArray(res?.sessions) ? res.sessions : [];
      setSessions(
        items
          .filter((x: any) => x?.url && x?.sessionId)
          .map((x: any) => ({
            sessionId: String(x.sessionId),
            url: String(x.url),
            title: safeTitleFromUrl(String(x.url)),
            updatedAt: String(x.updatedAt || ""),
          }))
      );
    } catch {
      // ignore
    }
    try {
      const data = (await getNotes({ sessionId: realSid })) as Notes;
      setNotes(data);
      setStatus("Notes loaded.");
    } catch (e: any) {
      setStatus(`Load notes error: ${e?.message || String(e)}`);
    }
  }

  async function onDeleteSession(u: string) {
    const [sid] = u.split("|", 1);
    const realSid = (sid || "").trim();
    if (!realSid) return;
    try {
      await deleteSession({ sessionId: realSid });
    } catch {
      // ignore
    }
    try {
      const res = await getSessions({ limit: 50 });
      const items = Array.isArray(res?.sessions) ? res.sessions : [];
      setSessions(
        items
          .filter((x: any) => x?.url && x?.sessionId)
          .map((x: any) => ({
            sessionId: String(x.sessionId),
            url: String(x.url),
            title: safeTitleFromUrl(String(x.url)),
            updatedAt: String(x.updatedAt || ""),
          }))
      );
    } catch {
      // ignore
      setSessions((prev) => prev.filter((x) => x.sessionId !== realSid));
    }
    if (sessionId.trim() === realSid) {
      setUrl("");
      setSessionId("");
      setNotes(null);
      setTopics(null);
      setSelectedTopics([]);
      setIsNotesAutoRefresh(false);
      setStatus(
        "Paste a URL, click Start session, then start a call with the ElevenLabs Agent. During the call, paste the URL into chat and say “analyze”. The agent will write Summary / Q&A / Quizzes into Notes while you talk."
      );
    }
  }

  async function onRefreshNotes() {
    try {
      const sid = sessionId.trim();
      if (!sid) {
        setStatus("Start/select a session first.");
        return;
      }
      setStatus("Refreshing notes…");
      const data = (await getNotes({ sessionId: sid })) as Notes;
      setNotes(data);
      setStatus("Notes refreshed.");
    } catch (e: any) {
      setStatus(`Refresh notes error: ${e?.message || String(e)}`);
    }
  }

  async function onDownloadNotes() {
    try {
      const sid = sessionId.trim();
      if (!sid) {
        setStatus("Start/select a session first.");
        return;
      }
      setStatus("Preparing notes download…");
      await downloadNotesDocx({ sessionId: sid });
      setStatus("Downloaded notes (study-notes.docx).");
    } catch (e: any) {
      setStatus(`Download notes error: ${e?.message || String(e)}`);
    }
  }

  return (
    <div className="page">
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
              const key = `${s.sessionId}|${s.url}`;
              const active = sessionId.trim() === s.sessionId;
              return (
                <div
                  key={key}
                  className={`sessionItem ${active ? "active" : ""}`}
                  onClick={() => onSelectSession(key)}
                  role="button"
                  tabIndex={0}
                >
                  <div className="sessionItemTop">
                    <div className="sessionTitle" title={s.url}>
                      {s.title} <span className="muted">({s.sessionId.slice(0, 8)})</span>
                    </div>
                    <button
                      className="sessionDelete"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSession(key);
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
            <div className="hero">
              <img className="heroLogo" src="/robot.svg" alt="Robot logo" />
              <h1 className="heroTitle">AI Study Buddy</h1>
              {/* <div className="heroSubtitle">
                Paste any URL → extract content → start a call with ElevenLabs Agent → the agent uses Gemini to summarize, tutor, and quiz you
              </div> */}
              {/* <div className="heroMeta muted">
                Backend: <code>{new URL(import.meta.env.VITE_BACKEND_URL || "http://localhost").origin}</code>
              </div> */}
            </div>

            <div className="card">
              <label>Paste your URL here</label>
              <div className="row">
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://…"
                />
                <button className="secondary" onClick={onLoadTopics} disabled={isLoadingTopics}>
                  {isLoadingTopics ? "Loading…" : "Get topics"}
                </button>
                <button onClick={onStartSession} disabled={isStartingSession || selectedTopics.length === 0}>
                  {isStartingSession ? "Starting…" : "Start session"}
                </button>
                <button className="secondary" onClick={onDownloadNotes} disabled={!url.trim()}>
                  Download notes
                </button>
                <button className="secondary" onClick={onRefreshNotes} disabled={!url.trim()}>
                  Refresh notes
                </button>
              </div>
              <div className="status">{status}</div>
            </div>

            <div className="card callCard" style={{ marginTop: 12 }}>
              <div style={{ fontWeight: 800, marginBottom: 6, textAlign: "center" }}>Start the call</div>
              {!AGENT_ID ? (
                <div className="muted" style={{ fontSize: 12, textAlign: "center" }}>
                  Missing <code>VITE_AGENT_ID</code>. Set it in <code>web/.env</code> (local) or Vercel env vars.
                </div>
              ) : (
                <>
                  <div className="muted" style={{ fontSize: 12, textAlign: "center" }}>
                    Tip: In the call, paste the URL and say “analyze”. Notes will update here automatically.
                  </div>
                  <div id="convai-root" className="convaiRoot" />
                  <ElevenLabsConvaiPortal agentId={AGENT_ID} />
                </>
              )}
            </div>

            {topics?.topics?.length ? (
              <div className="card" style={{ marginTop: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 12 }}>
                  <div style={{ fontWeight: 800 }}>Topics on this page</div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    (best-effort from headings)
                  </div>
                </div>
                {topics.title ? (
                  <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
                    Title: <code>{topics.title}</code>
                  </div>
                ) : null}
                <div style={{ marginTop: 10 }}>
                  <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
                    Select up to <strong>8</strong> topics for today’s session.
                  </div>
                  {topics.topics.slice(0, 40).map((t, i) => {
                    const indent = Math.max(0, Math.min(3, (t.level || 2) - 2)) * 12;
                    const checked = selectedTopics.includes(t.title);
                    const disabled = !checked && selectedTopics.length >= 8;
                    return (
                      <label
                        key={`${t.title}-${i}`}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          fontSize: 13,
                          lineHeight: 1.4,
                          marginBottom: 6,
                          paddingLeft: indent,
                          color: disabled ? "#94a3b8" : undefined,
                          cursor: disabled ? "not-allowed" : "pointer",
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          disabled={disabled}
                          onChange={(e) => {
                            const on = e.target.checked;
                            setSelectedTopics((prev) => {
                              if (on) {
                                if (prev.includes(t.title) || prev.length >= 8) return prev;
                                return [...prev, t.title];
                              }
                              return prev.filter((x) => x !== t.title);
                            });
                          }}
                        />
                        {t.title}
                      </label>
                    );
                  })}
                  {topics.topics.length > 40 ? (
                    <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
                      Showing first 40 topics.
                    </div>
                  ) : null}
                </div>
              </div>
            ) : null}

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
    </div>
  );
}


