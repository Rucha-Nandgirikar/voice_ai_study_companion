function env(key: string, fallback = ""): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const v = (import.meta as any)?.env?.[key];
  if (typeof v === "string" && v.trim()) return v.trim();
  return fallback;
}

export const BACKEND_URL = env(
  "VITE_BACKEND_URL",
  "https://voice-ai-study-companion-801406519570.us-central1.run.app"
);

export const AGENT_ID = env("VITE_AGENT_ID", "");


