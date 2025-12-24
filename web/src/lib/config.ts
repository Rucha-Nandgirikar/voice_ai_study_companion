// IMPORTANT: In production, Vite statically replaces `import.meta.env.VITE_*` references.
// Dynamic access like `import.meta.env[key]` will NOT be inlined and can be undefined.

export const BACKEND_URL =
  (import.meta.env.VITE_BACKEND_URL || "").trim() ||
  "https://voice-ai-study-companion-801406519570.us-central1.run.app";

export const AGENT_ID = (import.meta.env.VITE_AGENT_ID || "").trim();



