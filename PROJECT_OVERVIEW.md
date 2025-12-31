# Voice AI Study Companion - Project Overview

## Project Summary

**Voice AI Study Companion** is a voice-first AI tutoring application that helps users learn from any web page through natural conversation. Users paste a URL, select topics they want to study, and have an interactive voice conversation with an AI tutor powered by **Google Gemini** (via ElevenLabs) that teaches, quizzes, and tracks their progress.

---

## Key Features

### 1. **Voice-First Learning Experience**
- Natural conversation with AI tutor powered by ElevenLabs Agents
- Speech-to-text and text-to-speech for hands-free learning
- Socratic teaching style - patient, encouraging, adaptive

### 2. **Content Extraction & Analysis**
- Automatically extracts and analyzes content from any web page URL
- Identifies topics/sections from page headings and structure
- Supports regular web pages and GitHub markdown files
- Content extraction happens server-side for better security

### 3. **Smart Session Management**
- Create study sessions for specific URLs with selected topics (up to 8 topics)
- Track progress across multiple sessions (topics completed)
- Resume where you left off - completed topics are remembered
- Session-based organization with unique session IDs

### 4. **Automatic Note Generation**
- AI tutor automatically saves notes during conversations:
  - **Summary**: Running summary of what's been covered
  - **Q&A**: Questions asked and answers provided
  - **Quizzes**: Quiz questions, user answers, correct answers, and explanations
- Notes update in real-time during the call
- Download notes as Word documents (.docx) named by session ID

### 5. **Progress Tracking**
- Mark topics as completed when user understands them
- Visual indicators showing which topics were completed in previous sessions
- Deterministic progress tracking per session
- Completed topics persist across sessions for the same URL

### 6. **Responsive UI**
- Clean, modern web interface
- Session sidebar showing all past sessions
- Real-time notes display (summary, Q&A, quizzes)
- Responsive design: sidebar collapses on narrow screens, full view on wider screens
- 50/50 split between notes and call widget by default

---

## How It Works

### User Workflow:
1. **Paste URL** → User enters a web page URL they want to study
2. **Select Topics** → System extracts topics from page structure; user selects up to 8 topics to study
3. **Start Session** → Creates a new study session with selected topics
4. **Voice Call** → User starts voice conversation with ElevenLabs Agent
5. **Say "Analyze"** → Agent fetches page content and begins teaching
6. **Interactive Learning** → Agent teaches topics, answers questions, gives quizzes
7. **Auto-Save Notes** → Agent automatically saves summaries, Q&A, and quizzes
8. **Review Notes** → User can view and download notes anytime
9. **Track Progress** → Completed topics are marked and remembered for future sessions

### Technical Flow:
1. **Backend API** (FastAPI on Google Cloud Run):
   - Extracts content from URLs server-side
   - Manages sessions and notes persistence (PostgreSQL)
   - Provides REST API for frontend and agent

2. **ElevenLabs Agent** (Configured with Google Gemini):
   - Handles voice conversation (STT/TTS) via ElevenLabs platform
   - Powered by Google Gemini for reasoning and conversation intelligence
   - Uses webhook tools to call backend API
   - Saves notes automatically during conversation
   - Tracks progress by marking topics as done

3. **Frontend** (React + TypeScript):
   - Web UI for session management
   - Real-time notes display
   - ElevenLabs widget integration for voice calls
   - Session sidebar and notes viewer

---

## Technology Stack

### Backend:
- **FastAPI** - Python web framework
- **PostgreSQL** - Database for session and notes persistence (Cloud SQL)
- **Google Cloud Run** - Serverless container hosting
- **BeautifulSoup + Readability** - HTML content extraction
- **python-docx** - Word document generation

### Frontend:
- **React + TypeScript** - Web UI
- **Vite** - Build tool
- **ElevenLabs Convai Widget** - Voice conversation interface
- **Deployed on Vercel** - Static hosting

### AI/ML:
- **ElevenLabs Agents** - Voice AI platform (STT/TTS + persona)
- **Google Gemini** (via ElevenLabs) - LLM for reasoning and conversation intelligence
  - Configured within ElevenLabs Agents platform
  - Powers the AI tutor's reasoning, teaching, and quiz generation
  - No direct Google Cloud API calls needed (handled by ElevenLabs)
- **Webhook Tools** - Agent-backend integration for note-saving and progress tracking

---

## Key Technical Concepts

### Session-Based Architecture:
- Each study session has a unique `sessionId`
- Sessions store: URL, selected topics, completed topics, notes
- Session-first approach: all notes and progress tied to sessionId
- Multiple sessions can exist for the same URL (different topic selections)

### Progress Tracking:
- `selectedTopics`: Fresh selection from user for each new session
- `completedTopics`: Aggregated across all sessions for a URL (shows what user has learned)
- Users can see completed topics from previous sessions (green checkmarks)
- New sessions allow fresh topic selection while preserving progress history

### Notes Structure:
- **Summary**: Text summary of content covered
- **Q&A**: Array of question-answer pairs
- **Quizzes**: Array of quiz items with question, user answer, correct answer, explanation
- Notes automatically update during voice calls
- Downloadable as formatted Word documents

### Content Extraction:
- Server-side URL content extraction (security)
- Supports HTML pages and GitHub markdown
- Extracts headings/topics from page structure
- Cleans and processes content for better LLM consumption

---

## Unique Value Propositions

1. **Voice-First**: Natural conversation instead of reading/writing
2. **Context-Aware**: Agent knows what you've learned before
3. **Automatic Note-Taking**: No need to take notes manually
4. **Progress Persistence**: Learning history tracked across sessions
5. **Flexible Learning**: Jump between topics, resume anytime
6. **Works with Any Web Page**: Just paste a URL and start learning

---

## Use Cases

- **Students**: Study course materials, research papers, documentation
- **Professionals**: Learn new technologies, understand technical articles
- **Language Learners**: Practice with content in target language
- **Research**: Deep dive into complex topics with guided explanation
- **Review**: Revisit previous learning with tracked progress

---

## Deployment Architecture

- **Backend**: Google Cloud Run (serverless, auto-scaling)
- **Database**: Cloud SQL for PostgreSQL (persistent storage)
- **Frontend**: Vercel (CDN, global distribution)
- **AI**: 
  - **ElevenLabs Agents** platform (voice conversation, STT/TTS)
  - **Google Gemini** (configured via ElevenLabs) for LLM reasoning and intelligence

---

## Current Status

- ✅ Full-featured MVP with voice conversation
- ✅ Session management and progress tracking
- ✅ Automatic note generation and downloads
- ✅ PostgreSQL persistence
- ✅ Responsive web UI
- ✅ Production-ready deployment setup
- ✅ Google Gemini integration (via ElevenLabs Agents) for AI reasoning

## Google Cloud AI Integration

This application uses **Google Gemini** for LLM-powered reasoning and conversation intelligence. Gemini is configured within the ElevenLabs Agents platform, which means:

- **No direct Google Cloud API integration needed** in the backend code
- **Simplified architecture** - ElevenLabs handles the Gemini integration
- **Already compliant** with requirements to use Google Cloud AI (Gemini)
- **Future-ready** - Can optionally migrate to direct Vertex AI integration if needed for advanced features or direct control

The application leverages Google Cloud infrastructure (Cloud Run, Cloud SQL) and Google's AI technology (Gemini) through ElevenLabs, providing a complete Google Cloud-based solution.

