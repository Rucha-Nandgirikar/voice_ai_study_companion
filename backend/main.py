from __future__ import annotations

import os
from io import BytesIO

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from docx import Document

from backend.schemas import (
    ExtractRequest,
    ExtractResponse,
    NotesAppendQuestionRequest,
    NotesAppendTurnRequest,
    NotesGetResponse,
    NotesResetRequest,
    NotesSetSummaryRequest,
)
from backend.notes_store import append_question, append_turn, get_notes, reset_notes, set_summary
from backend.url_extract import fetch_and_extract_main_text


app = FastAPI(title="Voice AI Study Companion API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root() -> dict:
    return {
        "ok": True,
        "service": "voice-ai-study-companion",
        "endpoints": [
            "/health",
            "/extract",
            "/notes/reset",
            "/notes/set_summary",
            "/notes/append_question",
            "/notes/append_turn",
            "/notes",
            "/notes/download.docx",
        ],
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/extract", response_model=ExtractResponse)
async def extract(req: ExtractRequest) -> ExtractResponse:
    """
    Option B backend: the agent handles all LLM calls (Gemini configured in ElevenLabs).
    This endpoint only fetches & extracts the main page text.
    """
    try:
        text = await fetch_and_extract_main_text(req.url)
        if not text or len(text) < 200:
            raise HTTPException(status_code=400, detail="Could not extract enough readable text from that URL.")
        return ExtractResponse(url=req.url, cleanedText=text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extract failed: {e}")


@app.post("/notes/reset", response_model=NotesGetResponse)
def notes_reset(req: NotesResetRequest) -> NotesGetResponse:
    rec = reset_notes(req.url)
    return NotesGetResponse(url=rec.url, summary=rec.summary, questions=rec.questions, turns=rec.turns, updatedAt=rec.updated_at)


@app.post("/notes/set_summary", response_model=NotesGetResponse)
def notes_set_summary(req: NotesSetSummaryRequest) -> NotesGetResponse:
    rec = set_summary(req.url, req.summary)
    return NotesGetResponse(url=rec.url, summary=rec.summary, questions=rec.questions, turns=rec.turns, updatedAt=rec.updated_at)


@app.post("/notes/append_question", response_model=NotesGetResponse)
def notes_append_question(req: NotesAppendQuestionRequest) -> NotesGetResponse:
    rec = append_question(req.url, req.question)
    return NotesGetResponse(url=rec.url, summary=rec.summary, questions=rec.questions, turns=rec.turns, updatedAt=rec.updated_at)


@app.post("/notes/append_turn", response_model=NotesGetResponse)
def notes_append_turn(req: NotesAppendTurnRequest) -> NotesGetResponse:
    rec = append_turn(req.url, req.role, req.text)
    return NotesGetResponse(url=rec.url, summary=rec.summary, questions=rec.questions, turns=rec.turns, updatedAt=rec.updated_at)


@app.get("/notes", response_model=NotesGetResponse)
def notes_get(url: str) -> NotesGetResponse:
    rec = get_notes(url)
    if not rec:
        # If notes were not started yet, return an empty record to simplify clients.
        rec = reset_notes(url)
    return NotesGetResponse(url=rec.url, summary=rec.summary, questions=rec.questions, turns=rec.turns, updatedAt=rec.updated_at)


@app.get("/notes/download.docx")
def notes_download_docx(url: str) -> StreamingResponse:
    rec = get_notes(url) or reset_notes(url)

    doc = Document()
    doc.add_heading("Voice AI Study Notes", level=1)
    doc.add_paragraph(f"Source URL: {rec.url}")
    doc.add_paragraph(f"Last updated: {rec.updated_at}")

    doc.add_heading("Summary", level=2)
    doc.add_paragraph(rec.summary or "(No summary saved yet)")

    doc.add_heading("Questions asked", level=2)
    if rec.questions:
        for q in rec.questions:
            doc.add_paragraph(q, style="List Bullet")
    else:
        doc.add_paragraph("(No questions saved yet)")

    doc.add_heading("Call transcript (Q/A)", level=2)
    if rec.turns:
        for t in rec.turns:
            role = (t.get("role") or "").strip().lower()
            text = (t.get("text") or "").strip()
            if not text:
                continue
            prefix = "You:" if role == "user" else "Tutor:"
            doc.add_paragraph(f"{prefix} {text}")
    else:
        doc.add_paragraph("(No transcript turns saved yet)")

    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)

    filename = "study-notes.docx"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        bio,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )



