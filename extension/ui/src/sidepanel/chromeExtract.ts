export async function getActiveTab(): Promise<chrome.tabs.Tab> {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) throw new Error("No active tab found.");
  return tab;
}

async function sendToContent(tabId: number, message: any) {
  return await chrome.tabs.sendMessage(tabId, message);
}

export async function ensureContentScript(tab: chrome.tabs.Tab) {
  const url = tab.url || "";
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
    await sendToContent(tab.id!, { type: "PING" });
    return;
  } catch {
    await chrome.scripting.executeScript({
      target: { tabId: tab.id! },
      files: ["content.js"]
    });
  }
}

export async function extractPage(): Promise<{ cleanedText: string; url: string }> {
  const tab = await getActiveTab();
  await ensureContentScript(tab);
  const res = await sendToContent(tab.id!, { type: "EXTRACT_PAGE" });
  return { cleanedText: res.cleanedText || "", url: res.url || tab.url || "" };
}


