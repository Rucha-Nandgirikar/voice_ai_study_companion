from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.gemini_client import GeminiClient
from app.memory import SessionStore
from app.prompts import ANALYZE_SYSTEM, TURN_SYSTEM
from app.schemas import (
    AnalyzePageRequest,
    AnalyzePageResponse,
    ConversationTurnRequest,
    ConversationTurnResponse,
)


def _truncate(text: str, max_chars: int = 30_000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[TRUNCATED]"


app = FastAPI(title="Voice AI Study Companion API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = SessionStore()


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/page/analyze", response_model=AnalyzePageResponse)
def page_analyze(req: AnalyzePageRequest) -> AnalyzePageResponse:
    state = store.get_or_create(req.sessionId)

    cleaned = _truncate(req.cleanedText)
    user = (
        "Analyze this webpage content for tutoring.\n\n"
        f"URL: {req.url}\n\n"
        "CLEANED_TEXT:\n"
        f"{cleaned}\n"
    )

    schema = AnalyzePageResponse.model_json_schema()
    try:
        client = GeminiClient()
        data = client.generate_json(system=ANALYZE_SYSTEM, user=user, schema=schema)
        page = AnalyzePageResponse.model_validate(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analyze failed: {e}")

    store.set_page(req.sessionId, page)
    # Reset turns when a new page is analyzed.
    state.turns = []
    return page


@app.post("/conversation/turn", response_model=ConversationTurnResponse)
def conversation_turn(req: ConversationTurnRequest) -> ConversationTurnResponse:
    state = store.get_or_create(req.sessionId)

    if state.page is None:
        return ConversationTurnResponse(
            action="CLARIFY",
            assistantText="I’m ready. Please analyze the current page first, then tell me what topic you want to start with.",
            nextQuestion="Want me to summarize the page after you analyze it?",
            difficulty=state.difficulty,
            selectedSectionId=None,
        )

    # Append user turn first (so the model sees it in history).
    store.append_turn(req.sessionId, "user", req.userTranscript)

    topics = state.page.topics
    sections_brief = [{"id": s.id, "title": s.title, "summary": s.summary} for s in state.page.sections]
    turns = state.turns

    user = (
        "You are tutoring based on a webpage.\n\n"
        f"CURRENT_DIFFICULTY: {state.difficulty.value}\n\n"
        f"PAGE_SUMMARY: {state.page.summary}\n\n"
        f"TOPICS: {topics}\n\n"
        f"SECTIONS: {sections_brief}\n\n"
        f"RECENT_TURNS: {turns}\n\n"
        f"USER_UTTERANCE: {req.userTranscript}\n\n"
        "Return the next assistant response as JSON matching the schema."
    )

    schema = ConversationTurnResponse.model_json_schema()
    try:
        client = GeminiClient()
        data = client.generate_json(system=TURN_SYSTEM, user=user, schema=schema)
        resp = ConversationTurnResponse.model_validate(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Turn failed: {e}")

    # Update difficulty and append assistant turn for next round.
    state.difficulty = resp.difficulty
    store.append_turn(req.sessionId, "assistant", resp.assistantText)
    return resp




