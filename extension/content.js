function isProbablyVisible(el) {
  const style = window.getComputedStyle(el);
  return style && style.display !== "none" && style.visibility !== "hidden";
}

function pickMainContainer() {
  const candidates = [
    document.querySelector("article"),
    document.querySelector("main"),
    document.querySelector('[role="main"]'),
  ].filter(Boolean);

  for (const el of candidates) {
    if (isProbablyVisible(el) && (el.innerText || "").trim().length > 400) return el;
  }
  return document.body;
}

function cleanText(text) {
  return (text || "")
    .replace(/\u00a0/g, " ")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function extractPageText() {
  const container = pickMainContainer();

  // Remove obvious noisy blocks if present (best-effort, non-destructive clone).
  const clone = container.cloneNode(true);
  clone.querySelectorAll("nav, header, footer, aside, form, button, noscript").forEach((n) => n.remove());
  clone.querySelectorAll('[aria-label*="breadcrumb" i], [class*="comment" i], [id*="comment" i]').forEach((n) => n.remove());

  const text = cleanText(clone.innerText);
  return text;
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "PING") {
    sendResponse({ ok: true });
    return true;
  }
  if (msg?.type === "EXTRACT_PAGE") {
    try {
      const cleanedText = extractPageText();
      sendResponse({ cleanedText, url: window.location.href });
    } catch (e) {
      sendResponse({ cleanedText: "", url: window.location.href, error: e?.message || String(e) });
    }
    return true;
  }
});


