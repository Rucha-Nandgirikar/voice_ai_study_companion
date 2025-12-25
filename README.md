# Voice AI Study Companion (Hackathon MVP)

Voice-first tutor that runs as a simple web app (paste a URL) and uses:

- **ElevenLabs Agents** for conversational voice UX (STT/TTS + persona)
- **ElevenLabs Agents** (configured with Gemini in ElevenLabs) for reasoning + voice
- **Cloud Run** to host the backend API (FastAPI)

This repo contains:
- `backend/`: FastAPI backend (Cloud Run)
- `web/`: React web UI (Vercel or any static host)

## What is Cloud Run?

**Cloud Run** runs your backend as a containerized HTTP service. You deploy a Docker image; Google handles HTTPS, scaling, logs, and IAM.

## Backend API (FastAPI)

### Endpoints (Option B: agent does all LLM)

- `GET /health`
- `POST /extract` (fetch + extract content server-side from a pasted URL)
- Notes (MVP; in-memory):
  - `POST /notes/reset` (start notes for a URL)
  - `POST /notes/set_summary` (agent saves a summary)
  - `POST /notes/append_question` (agent saves questions asked)
  - `POST /notes/append_turn` (agent saves full call turns: user + tutor)
  - `GET /notes/download.docx?url=...` (download notes as a Word document)

Notes:
- For **YouTube URLs**, `/extract` will try to fetch a transcript (only works if captions are available). If unavailable, it falls back to regular HTML extraction.

### ElevenLabs Agent tools (recommended)
Add these as **Webhook tools** on your ElevenLabs Agent so notes are saved automatically:

- `fetch_page_content(url)` → calls `POST /extract`
- `set_summary(url, summary)` → calls `POST /notes/set_summary`
- `append_turn(url, role, text)` → calls `POST /notes/append_turn` (recommended)
  - `role`: `user` or `agent`
  - `text`: the utterance
- (optional) `append_question(url, question)` → calls `POST /notes/append_question`

Then tell the agent in its system prompt:
- When a user provides a URL / says “analyze”, call `fetch_page_content(url)` first.
- After summarizing, call `set_summary(url, summary)`.
- After each user question, call `append_turn(url, "user", question)`.
- After each tutor answer, call `append_turn(url, "agent", answer)`.

### Session memory (MVP)

Session is keyed by `sessionId` and stored in an in-memory TTL cache:
- difficulty level
- page summary/topics/sections
- last N conversation turns

For a hackathon MVP, this is enough. For stability across instances, swap to Firestore/Redis later.

## ElevenLabs Agent tool contract (recommended)

In ElevenLabs Agents, define a tool that calls your backend on each user utterance.

### Tool: `tutor_turn`

**Request (Agent -> Backend)**

```json
{
  "sessionId": "abc123",
  "userTranscript": "Start with databases and explain simply."
}
```

**Response (Backend -> Agent)**

```json
{
  "action": "TEACH",
  "assistantText": "Great—let’s start with databases. A database is ...",
  "nextQuestion": "Want a quick example, or should I quiz you?",
  "difficulty": "beginner",
  "selectedSectionId": "sec_2"
}
```

### Page analysis call (Client -> Backend)

`POST /page/analyze`

```json
{
  "sessionId": "abc123",
  "url": "https://example.com/system-design",
  "cleanedText": "…extracted main content text…"
}
```

Returns:

```json
{
  "summary": "…",
  "topics": ["…"],
  "sections": [
    {
      "id": "sec_1",
      "title": "…",
      "summary": "…",
      "keyPoints": ["…"],
      "sourceExcerpt": "…"
    }
  ]
}
```

## Local run

### 1) Create a venv and install deps

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) Configure env vars (pick one mode)

#### Env vars (local/dev)

Option B backend does **not** call Google. No `GOOGLE_API_KEY` needed.

### 3) Run

```bash
python -m backend
```

Open `http://localhost:8080/health`

## Deploy to Cloud Run (simple path)

You’ll need a GCP project with billing enabled.

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud run deploy voice-ai-study-companion \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,GOOGLE_CLOUD_LOCATION=us-central1
```

Notes:
- `--source .` uses Google’s buildpacks (no Docker required). This repo also includes a Dockerfile if you prefer.
- For production, don’t use `--allow-unauthenticated`; instead restrict via IAM and call from your extension backend.

## Deploy the web UI (Vercel)

1. Push this repo to GitHub.
2. In Vercel, **Import Project** → select this repo.
3. Set **Root Directory** to `web/`.
4. Add env vars:
   - `VITE_BACKEND_URL` = your Cloud Run base URL
   - `VITE_AGENT_ID` = your ElevenLabs Agent ID
5. Deploy.

Local dev:

```bash
cd web
npm install
npm run dev
```
