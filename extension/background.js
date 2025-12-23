chrome.runtime.onInstalled.addListener(() => {
  // Ensure side panel is enabled for tabs (Chrome uses the manifest default_path).
});

chrome.action.onClicked.addListener(async (tab) => {
  try {
    if (!tab?.id) return;
    // Opens the side panel for this tab.
    await chrome.sidePanel.open({ tabId: tab.id });
  } catch (e) {
    // If the API isn't available (older Chrome), do nothing.
    console.warn("Failed to open side panel:", e);
  }
});


