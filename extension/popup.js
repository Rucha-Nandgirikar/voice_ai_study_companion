const DEFAULT_BACKEND =
  "https://voice-ai-study-companion-801406519570.us-central1.run.app";
const DEFAULT_SESSION = "demo1";

const $ = (id) => document.getElementById(id);

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function sendToContent(tabId, message) {
  return await chrome.tabs.sendMessage(tabId, message);
}

async function ensureContentScript(tab) {
  const url = tab?.url || "";
  // Chrome blocks extensions on internal/restricted pages.
  if (
    url.startsWith("chrome://") ||
    url.startsWith("chrome-extension://") ||
    url.startsWith("edge://") ||
    url.startsWith("about:") ||
    url.startsWith("view-source:")
  ) {
    throw new Error("Chrome blocks extensions on this page. Open a normal https webpage and try again.");
  }

  try {
    // Ping existing content script.
    await sendToContent(tab.id, { type: "PING" });
    return;
  } catch (_e) {
    // If not present, inject it and try again.
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["content.js"],
    });
  }
}

function setStatus(msg) {
  $("status").textContent = msg;
}

function renderTopics(topics) {
  const ul = $("topics");
  ul.innerHTML = "";
  (topics || []).slice(0, 8).forEach((t) => {
    const li = document.createElement("li");
    li.textContent = t;
    ul.appendChild(li);
  });
}

async function loadSettings() {
  const { backendUrl, sessionId } = await chrome.storage.sync.get([
    "backendUrl",
    "sessionId",
  ]);
  $("backendUrl").value = backendUrl || DEFAULT_BACKEND;
  $("sessionId").value = sessionId || DEFAULT_SESSION;
}

async function saveSettings() {
  const backendUrl = $("backendUrl").value.trim() || DEFAULT_BACKEND;
  const sessionId = $("sessionId").value.trim() || DEFAULT_SESSION;
  await chrome.storage.sync.set({ backendUrl, sessionId });
  return { backendUrl, sessionId };
}

async function analyze() {
  const btn = $("analyzeBtn");
  btn.disabled = true;
  renderTopics([]);

  const { backendUrl, sessionId } = await saveSettings();

  try {
    const tab = await getActiveTab();
    if (!tab?.id) throw new Error("No active tab found.");

    await ensureContentScript(tab);

    setStatus("Extracting main content…");
    const { cleanedText, url } = await sendToContent(tab.id, {
      type: "EXTRACT_PAGE",
    });

    if (!cleanedText || cleanedText.length < 50) {
      throw new Error("Couldn’t extract enough readable text from this page.");
    }

    setStatus("Sending to backend for analysis…");
    const res = await fetch(`${backendUrl.replace(/\/$/, "")}/page/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sessionId, url: url || tab.url, cleanedText }),
    });

    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`Backend error (${res.status}): ${txt}`);
    }

    const data = await res.json();
    renderTopics(data.topics || []);
    setStatus("Analyzed! Now talk to your ElevenLabs Agent.");
  } catch (e) {
    setStatus(`Error: ${e?.message || String(e)}`);
  } finally {
    btn.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadSettings();
  $("analyzeBtn").addEventListener("click", analyze);
});


