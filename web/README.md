# Web UI (React)

Simple single-page web app:
- paste a URL → backend fetches + extracts → Gemini summarizes/topics
- Start/Stop call using ElevenLabs React SDK (signed URL from backend)

## Configure

Copy `web/env.example` → `web/.env` (create file) and set:
- `VITE_BACKEND_URL` (Cloud Run base URL)
- `VITE_AGENT_ID` (ElevenLabs Agent ID)

## Run locally

```bash
cd web
npm install
npm run dev
```




