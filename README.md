# Voice AI Study Companion (Hackathon MVP)

Voice-first tutor that runs on any webpage (via extension/widget) and uses:

- **ElevenLabs Agents** for conversational voice UX (STT/TTS + persona)
- **Google Cloud Gemini / Vertex AI** for reasoning (summarize, teach, quiz, adapt)
- **Cloud Run** to host the backend API (FastAPI)

This repo currently contains the **backend** scaffold needed for the hackathon demo.

## What is Cloud Run?

**Cloud Run** runs your backend as a containerized HTTP service. You deploy a Docker image; Google handles HTTPS, scaling, logs, and IAM.

## Backend API (FastAPI)

### Endpoints

- `GET /health`
- `POST /page/analyze`
- `POST /conversation/turn`

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

### Page analysis call (Extension -> Backend)

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

#### Mode A: Vertex AI (recommended on Cloud Run)

- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION` (e.g. `us-central1`)
- `GEMINI_MODEL` (default: `gemini-1.5-pro`)

Cloud Run will use the service account (ADC).

#### Mode B: Gemini API key (local/dev)

- `GOOGLE_API_KEY`
- `GEMINI_MODEL` (default: `gemini-1.5-pro`)

### 3) Run

```bash
python -m app
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
  --set-env-vars GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,GOOGLE_CLOUD_LOCATION=us-central1,GEMINI_MODEL=gemini-1.5-pro
```

Notes:
- `--source .` uses Google’s buildpacks (no Docker required). This repo also includes a Dockerfile if you prefer.
- For production, don’t use `--allow-unauthenticated`; instead restrict via IAM and call from your extension backend.


