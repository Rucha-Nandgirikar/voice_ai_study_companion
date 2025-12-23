export type Settings = {
  backendUrl: string;
  sessionId: string;
  agentId: string;
};

export const DEFAULTS: Settings = {
  backendUrl: "https://voice-ai-study-companion-801406519570.us-central1.run.app",
  sessionId: "demo1",
  agentId: ""
};

export async function loadSettings(): Promise<Settings> {
  const res = await chrome.storage.sync.get(["backendUrl", "sessionId", "agentId"]);
  return {
    backendUrl: (res.backendUrl as string) || DEFAULTS.backendUrl,
    sessionId: (res.sessionId as string) || DEFAULTS.sessionId,
    agentId: (res.agentId as string) || DEFAULTS.agentId
  };
}

export async function saveSettings(next: Settings) {
  await chrome.storage.sync.set(next);
}


