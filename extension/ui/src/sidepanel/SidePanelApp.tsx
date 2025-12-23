import React, { useEffect, useMemo, useState } from "react";
import { useConversation } from "@elevenlabs/react";
import { analyzePage, getElevenLabsSignedUrl } from "./api";
import { extractPage } from "./chromeExtract";
import { DEFAULTS, loadSettings, saveSettings, Settings } from "./storage";

type ChatMsg = { role: "user" | "agent"; text: string };

export function SidePanelApp() {
  const [settings, setSettings] = useState<Settings>(DEFAULTS);
  const [status, setStatus] = useState<string>("Ready.");
  const [topics, setTopics] = useState<string[]>([]);
  const [chat, setChat] = useState<ChatMsg[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [micState, setMicState] = useState<"unknown" | "granted" | "denied" | "prompt">("unknown");
  const extensionId = useMemo(() => chrome?.runtime?.id || "", []);
  const [volume, setVolume] = useState<number>(1);
  const [audioEvents, setAudioEvents] = useState<number>(0);
  const [outputLevel, setOutputLevel] = useState<number>(0);
  const [autoMute, setAutoMute] = useState<boolean>(true);
  const [micMuted, setMicMuted] = useState<boolean>(false);

  useEffect(() => {
    loadSettings().then(setSettings).catch(() => {});
  }, []);

  async function refreshMicState() {
    try {
      // Permissions API isn't always available for microphone in all contexts; best-effort.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const perm = await (navigator.permissions as any)?.query?.({ name: "microphone" });
      const state = (perm?.state || "").toString();
      if (state === "granted" || state === "denied" || state === "prompt") {
        setMicState(state);
      } else {
        setMicState("unknown");
      }
    } catch {
      setMicState("unknown");
    }
  }

  useEffect(() => {
    refreshMicState();
  }, []);

  const conversation = useConversation({
    agentId: settings.agentId || undefined,
    // Ensure audio isn't accidentally muted by default.
    volume,
    onAudio: () => {
      setAudioEvents((n) => n + 1);
    },
    onMessage: (m: any) => {
      // Best-effort rendering across SDK message shapes
      const role = (m?.role || m?.speaker || "").toString().toLowerCase();
      const text = (m?.text || m?.message || m?.content || "").toString();
      if (!text) return;
      setChat((prev) => [
        ...prev,
        { role: role.includes("user") ? "user" : "agent", text }
      ]);
    },
    onError: (e: any) => {
      setStatus(`Agent error: ${e?.message || String(e)}`);
    }
  });

  const isConnected = !!(conversation as any)?.isSessionActive;
  const agentStatus = ((conversation as any)?.status || "unknown").toString();
  const isSpeaking = !!(conversation as any)?.isSpeaking;

  // Auto-mute mic while the agent is speaking to prevent echo/barged-in interruption.
  useEffect(() => {
    if (!isConnected) return;
    if (!autoMute) return;
    try {
      (conversation as any)?.setMicMuted?.(!!isSpeaking);
      setMicMuted(!!isSpeaking);
    } catch {
      // ignore
    }
  }, [autoMute, isConnected, isSpeaking, conversation]);

  useEffect(() => {
    const id = window.setInterval(() => {
      try {
        const v = (conversation as any)?.getOutputVolume?.();
        if (typeof v === "number" && !Number.isNaN(v)) setOutputLevel(v);
      } catch {
        // ignore
      }
    }, 250);
    return () => window.clearInterval(id);
  }, [conversation]);

  async function onSave() {
    await saveSettings(settings);
    setStatus("Saved settings.");
  }

  async function onAnalyze() {
    setIsAnalyzing(true);
    setTopics([]);
    try {
      setStatus("Extracting main content…");
      const { cleanedText, url } = await extractPage();
      if (!cleanedText || cleanedText.length < 50) {
        throw new Error("Couldn’t extract enough readable text from this page.");
      }
      setStatus("Sending to backend for analysis…");
      const data = await analyzePage({
        backendUrl: settings.backendUrl,
        sessionId: settings.sessionId,
        url,
        cleanedText
      });
      setTopics((data?.topics || []).slice(0, 12));
      setStatus("Analyzed! Start the voice tutor, or click “Speak summary”.");
    } catch (e: any) {
      setStatus(`Analyze error: ${e?.message || String(e)}`);
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function ensureMic() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Immediately stop tracks; we only want to ensure permission is granted.
      stream.getTracks().forEach((t) => t.stop());
      await refreshMicState();
    } catch (e: any) {
      await refreshMicState();
      const name = e?.name || "UnknownError";
      const msg = e?.message || String(e);
      throw new Error(`${name}: ${msg}`);
    }
  }

  async function onStartVoice() {
    try {
      if (!settings.agentId) {
        setStatus("Please paste your ElevenLabs Agent ID first, then Save.");
        return;
      }
      await ensureMic();
      setStatus("Starting voice session… (fetching signed URL)");
      const { signedUrl } = await getElevenLabsSignedUrl({
        backendUrl: settings.backendUrl,
        agentId: settings.agentId
      });
      await (conversation as any).startSession?.({ signedUrl });
      // Force volume after start as well (some SDKs apply volume only after session exists).
      await (conversation as any).setVolume?.({ volume });
      // Start with mic unmuted; auto-mute may toggle based on speaking state.
      await (conversation as any).setMicMuted?.(false);
      setMicMuted(false);
      setStatus("Voice session started. Say: “Summarize this page.”");
    } catch (e: any) {
      setStatus(`Start error: ${e?.message || String(e)}`);
    }
  }

  async function onStopVoice() {
    try {
      setStatus("Stopping voice session…");
      await (conversation as any).stopSession?.();
      setStatus("Stopped.");
    } catch (e: any) {
      setStatus(`Stop error: ${e?.message || String(e)}`);
    }
  }

  async function waitForConnected(timeoutMs = 8000) {
    const start = Date.now();
    // Some SDKs expose status; we also track it via callbacks.
    while (Date.now() - start < timeoutMs) {
      const st = (agentStatus || "").toLowerCase();
      if (st === "connected") return;
      // If the SDK reports session active, still allow a short grace period.
      if ((conversation as any)?.isSessionActive && st !== "disconnected") return;
      await new Promise((r) => setTimeout(r, 200));
    }
    throw new Error(`Timed out waiting for connection (status=${agentStatus}).`);
  }

  function openInTab() {
    const url = chrome.runtime.getURL("dist/index.html");
    chrome.tabs.create({ url });
    setStatus("Opened in a new tab. Try Start voice tutor there (mic prompts are often more reliable).");
  }

  async function speakSummary() {
    try {
      if (!settings.agentId) {
        setStatus("Please paste your ElevenLabs Agent ID first, then Save.");
        return;
      }
      if (!isConnected || (agentStatus || "").toLowerCase() !== "connected") {
        // Try a clean restart if the websocket is closing/closed.
        try {
          await (conversation as any).stopSession?.();
        } catch {}
        await onStartVoice();
        await waitForConnected();
      }
      setStatus("Asking the tutor to summarize (spoken) …");
      await (conversation as any).sendUserMessage?.(
        "Summarize this page in 4 to 6 sentences, then ask me which topic I want to start with."
      );
    } catch (e: any) {
      setStatus(`Speak summary error: ${e?.message || String(e)}`);
    }
  }

  async function playTestTone() {
    try {
      setStatus("Playing test tone… (If you hear nothing, check Sound permission for the extension page.)");
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = 440;
      // Louder than before; this should be clearly audible if audio is allowed.
      gain.gain.value = 0.2;
      osc.connect(gain);
      gain.connect(ctx.destination);
      const before = ctx.state;
      await ctx.resume();
      const after = ctx.state;
      osc.start();
      setStatus(`Test tone playing. AudioContext state: ${before} -> ${after} (sampleRate=${ctx.sampleRate}).`);
      setTimeout(async () => {
        osc.stop();
        await ctx.close();
        setStatus("Test tone finished. If you didn’t hear it, check system/Chrome audio output.");
      }, 400);
    } catch (e: any) {
      setStatus(`Test tone error: ${e?.message || String(e)}`);
    }
  }

  return (
    <div className="container">
      <div className="card">
        <div style={{ fontWeight: 800, fontSize: 14 }}>Voice AI Study Companion</div>
        <div className="muted" style={{ marginTop: 4 }}>
          Analyze the current page, then talk to your ElevenLabs Agent—inside this side panel.
        </div>
      </div>

      <div className="card">
        <div className="row" style={{ gap: 10 }}>
          <div style={{ flex: 1 }}>
            <label>Backend URL (Cloud Run)</label>
            <input
              value={settings.backendUrl}
              onChange={(e) => setSettings((s) => ({ ...s, backendUrl: e.target.value }))}
              placeholder={DEFAULTS.backendUrl}
            />
          </div>
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <div style={{ flex: 1 }}>
            <label>Session ID (must match your Agent tool)</label>
            <input
              value={settings.sessionId}
              onChange={(e) => setSettings((s) => ({ ...s, sessionId: e.target.value }))}
              placeholder={DEFAULTS.sessionId}
            />
          </div>
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <div style={{ flex: 1 }}>
            <label>ElevenLabs Agent ID</label>
            <input
              value={settings.agentId}
              onChange={(e) => setSettings((s) => ({ ...s, agentId: e.target.value }))}
              placeholder="Paste from ElevenLabs dashboard"
            />
          </div>
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <button className="secondary" onClick={onSave}>
            Save
          </button>
          <button onClick={onAnalyze} disabled={isAnalyzing}>
            {isAnalyzing ? "Analyzing…" : "Analyze page"}
          </button>
        </div>
      </div>

      <div className="card">
        <div style={{ fontWeight: 800, fontSize: 13 }}>Mic diagnostics</div>
        <div className="muted" style={{ marginTop: 6 }}>
          Permission state: <code>{micState}</code>
        </div>
        <div className="muted" style={{ marginTop: 6 }}>
          If you never see a mic prompt and it stays <code>denied</code>, reset permissions here:
          <div style={{ marginTop: 6 }}>
            <code>
              chrome://settings/content/siteDetails?site=chrome-extension%3A%2F%2F{extensionId}
            </code>
          </div>
          Then set Microphone to <code>Allow</code>, reload the extension, and try again.
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <button className="secondary" onClick={async () => {
            try {
              setStatus("Requesting microphone permission…");
              await ensureMic();
              setStatus("Microphone permission looks OK. Now start the voice tutor.");
            } catch (e: any) {
              setStatus(`Mic test error: ${e?.message || String(e)}`);
            }
          }}>
            Test microphone
          </button>
          <button className="secondary" onClick={refreshMicState}>
            Refresh
          </button>
        </div>
      </div>

      <div className="card">
        <div className="row">
          <button onClick={onStartVoice} disabled={isConnected}>
            Start voice tutor
          </button>
          <button className="secondary" onClick={onStopVoice} disabled={!isConnected}>
            Stop
          </button>
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <button className="secondary" onClick={speakSummary}>
            Speak summary
          </button>
          <div style={{ flex: 1 }}>
            <label>Volume</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={volume}
              onChange={(e) => setVolume(parseFloat(e.target.value))}
            />
          </div>
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <button className="secondary" onClick={playTestTone}>
            Play test tone
          </button>
          <div className="muted" style={{ flex: 1 }}>
            Agent: <code>{agentStatus}</code> · Speaking: <code>{String(isSpeaking)}</code> · Audio events:{" "}
            <code>{audioEvents}</code> · Output level: <code>{outputLevel.toFixed(2)}</code>
          </div>
        </div>
        <div className="row" style={{ marginTop: 10, alignItems: "flex-end" }}>
          <div style={{ flex: 1 }}>
            <label>Auto-mute mic while agent speaks (recommended)</label>
            <input
              type="checkbox"
              checked={autoMute}
              onChange={(e) => setAutoMute(e.target.checked)}
            />
          </div>
          <button
            className="secondary"
            disabled={!isConnected || autoMute}
            onClick={async () => {
              try {
                const next = !micMuted;
                await (conversation as any)?.setMicMuted?.(next);
                setMicMuted(next);
                setStatus(next ? "Mic muted." : "Mic unmuted.");
              } catch (e: any) {
                setStatus(`Mic toggle error: ${e?.message || String(e)}`);
              }
            }}
          >
            {micMuted ? "Unmute mic" : "Mute mic"}
          </button>
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <button
            className="secondary"
            disabled={!isConnected}
            onMouseDown={async () => {
              if (autoMute) return;
              try {
                await (conversation as any)?.setMicMuted?.(false);
                setMicMuted(false);
              } catch {}
            }}
            onMouseUp={async () => {
              if (autoMute) return;
              try {
                await (conversation as any)?.setMicMuted?.(true);
                setMicMuted(true);
              } catch {}
            }}
          >
            Hold to talk (push-to-talk)
          </button>
          <div className="muted" style={{ flex: 1 }}>
            Tip: use headphones for best full-duplex conversation.
          </div>
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <button className="secondary" onClick={openInTab}>
            Open UI in a tab (mic fallback)
          </button>
        </div>
        <div className="muted" style={{ marginTop: 10 }}>
          After analyzing, try: <code>Summarize this page</code> → <code>Start with DNS</code> →{" "}
          <code>Quiz me</code>.
        </div>
        <div className="status" style={{ marginTop: 10 }}>
          {status}
        </div>

        {topics.length > 0 && (
          <>
            <div className="muted" style={{ marginTop: 10, fontWeight: 700 }}>
              Topics
            </div>
            <ul className="topics">
              {topics.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </>
        )}

        {chat.length > 0 && (
          <div className="chat">
            {chat.slice(-20).map((m, idx) => (
              <div key={idx} className={`msg ${m.role}`}>
                <strong style={{ textTransform: "capitalize" }}>{m.role}:</strong> {m.text}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


