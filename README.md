# Voice AI Study Companion (Hackathon MVP)

Voice-first tutor that runs as a simple web app (paste a URL) and uses:

- **ElevenLabs Agents** for conversational voice UX (STT/TTS + persona)
- **Google Gemini** (configured via ElevenLabs Agents) for LLM reasoning and conversation intelligence
- **Cloud Run** to host the backend API (FastAPI)

**Note:** Gemini is configured within the ElevenLabs Agents platform, providing the AI reasoning capabilities. The backend does not directly call Google Cloud APIs - all LLM interactions are handled through ElevenLabs.

This repo contains:
- `backend/`: FastAPI backend (Cloud Run)
- `web/`: React web UI (Vercel or any static host)

## What is Cloud Run?

**Cloud Run** runs your backend as a containerized HTTP service. You deploy a Docker image; Google handles HTTPS, scaling, logs, and IAM.

## Backend API (FastAPI)

### Endpoints

- `GET /health`
- `POST /extract` (agent tool: fetch + extract content server-side from a pasted URL)
- `POST /topics` (UI: list headings/topics from a pasted URL)
- `POST /sessions/start` (UI: create a new study session for this URL with selected topics)
- `GET /sessions` (UI: list sessions for the left sidebar)
- `GET /sessions/latest?url=...` (agent: find the latest session for that URL, including selected topics)
- `POST /sessions/progress/mark_topic_done` (agent: mark a topic as completed)
- Notes (MVP; persisted in Postgres if DATABASE_URL is set):
  - `GET /notes?sessionId=...` (fetch notes for a session)
  - `POST /notes/reset` (reset notes for a session)
  - `POST /notes/set_summary` (agent saves a summary)
  - `POST /notes/append_qa` (agent saves a Q&A pair)
  - `POST /notes/append_quiz` (agent saves a quiz item with feedback)
  - (optional) `POST /notes/append_turn` (raw transcript turns)
  - (legacy) `POST /notes/append_question`
  - `GET /notes/download.docx?sessionId=...` (download notes as a Word document)

Notes:
- `/topics` is best-effort: it reads page structure (headings / markdown headings). Some pages may have weak/empty headings.

### Optional: Persist notes in Postgres (Cloud SQL)
By default notes are stored **in-memory** (they reset if Cloud Run restarts). To persist notes:

- Create a **Cloud SQL for PostgreSQL** instance
- Set `DATABASE_URL` on Cloud Run
- (Recommended) attach the Cloud SQL instance to your Cloud Run service

Example `DATABASE_URL` for Cloud Run using the Cloud SQL Unix socket:

```text
DATABASE_URL=postgresql://USER:PASSWORD@/DB_NAME?host=/cloudsql/PROJECT:REGION:INSTANCE
```

Deploy with Cloud SQL attached (Cloud Shell):

```bash
gcloud run deploy voice-ai-study-companion \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances PROJECT:REGION:INSTANCE \
  --set-env-vars DATABASE_URL="postgresql://USER:PASSWORD@/DB_NAME?host=/cloudsql/PROJECT:REGION:INSTANCE"
```

Also ensure the Cloud Run runtime service account has the **Cloud SQL Client** role.

### ElevenLabs Agent tools (recommended)
Add these as **Webhook tools** on your ElevenLabs Agent so notes are saved automatically:

- `fetch_page_content(url)` → calls `POST /extract`
- `get_latest_session(url)` → calls `GET /sessions/latest?url=...` and returns `sessionId` + selectedTopics + completedTopics
- `set_summary(sessionId, summary)` → calls `POST /notes/set_summary`
- `append_qa(sessionId, question, answer)` → calls `POST /notes/append_qa` (recommended)
- `append_quiz(sessionId, question, userAnswer, correctAnswer, explanation)` → calls `POST /notes/append_quiz` (recommended)
- `mark_topic_done(sessionId, topicTitle)` → calls `POST /sessions/progress/mark_topic_done` (track completed topics)
- (optional) `append_turn(sessionId, role, text)` → calls `POST /notes/append_turn` (raw transcript)

Then tell the agent in its system prompt:
- At call start (or when user says "analyze" / is silent):
  - Read the URL from the user message
  - Call `get_latest_session(url)` to get `sessionId` + selectedTopics + completedTopics
  - If completedTopics exist:
    - If 1-3 topics: "In previous sessions, you successfully completed topics: [list them]. Today's session covers [selectedTopics]."
    - If 4+ topics: "In previous sessions, you successfully completed [count]+ topics. Today's session covers [selectedTopics]."
  - Confirm: "Today, would you like to study topics 1–8: …?" If confirmed, begin with Topic 1.
- Call `fetch_page_content(url)` ONCE at the start using the `url` from `get_latest_session(url)` response. You don't need to fetch again when switching topics - use the content you already fetched.
- After completing a topic (user understands it), call `mark_topic_done(sessionId, topicTitle)` to track progress.
- After summarizing a topic/block, call `set_summary(sessionId, summary)` (you can append/overwrite depending on your prompt).
- When the user asks a question and you answer it, call `append_qa(sessionId, question, answer)`.
- When you run a quiz, call `append_quiz(sessionId, ...)` with the prompt and feedback.

**Note:** If the user pastes the same URL again later, `get_latest_session(url)` returns the same latest session (same sessionId and selectedTopics). To start a NEW session with different topics, the user must go to the web UI and click "Start session" again with new topic selections.

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

**Note:** The backend does not directly call Google Cloud APIs. Gemini is configured within ElevenLabs Agents platform, so no `GOOGLE_API_KEY` is needed in the backend code. All LLM reasoning happens through ElevenLabs.

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
