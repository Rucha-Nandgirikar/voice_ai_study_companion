from __future__ import annotations

import os
from io import BytesIO

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from docx import Document
from dotenv import load_dotenv

from backend.schemas import (
    ExtractRequest,
    ExtractResponse,
    ExtractChunkRequest,
    ExtractChunkResponse,
    ExtractPartsRequest,
    ExtractPartsResponse,
    ExtractPart,
    SummarizeRequest,
    SummarizeResponse,
    NotesAppendQuestionRequest,
    NotesAppendTurnRequest,
    NotesAppendQARequest,
    NotesAppendQuizRequest,
    NotesGetResponse,
    NotesResetRequest,
    NotesSetSummaryRequest,
    SessionTouchRequest,
    SessionsListResponse,
)
from backend.notes_repo import PostgresNotesRepo, make_notes_repo
from backend.url_extract import fetch_and_extract_main_text
from backend.gemini_api import GeminiError, gemini_generate_text, get_gemini_model


load_dotenv()
app = FastAPI(title="Voice AI Study Companion API", version="0.2.0")
notes_repo = make_notes_repo()

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
            "/summarize",
            "/sessions",
            "/sessions/touch",
            "/sessions (DELETE)",
            "/notes/reset",
            "/notes/set_summary",
            "/notes/append_question",
            "/notes/append_turn",
            "/notes/append_qa",
            "/notes/append_quiz",
            "/notes",
            "/notes/download.docx",
        ],
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.on_event("startup")
def _startup() -> None:
    if isinstance(notes_repo, PostgresNotesRepo):
        notes_repo.ensure_schema()


@app.get("/sessions", response_model=SessionsListResponse)
def sessions_list(limit: int = 50) -> SessionsListResponse:
    try:
        sessions = notes_repo.list_sessions(limit=limit)
        return SessionsListResponse(sessions=sessions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sessions list failed: {e}")


@app.post("/sessions/touch")
def sessions_touch(req: SessionTouchRequest) -> dict:
    try:
        notes_repo.touch_session(req.url)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sessions touch failed: {e}")


@app.delete("/sessions")
def sessions_delete(url: str) -> dict:
    try:
        notes_repo.delete_session(url)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sessions delete failed: {e}")


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
        total = len(text)
        # Prevent oversized tool payloads (ElevenLabs tool results/context can have size limits).
        default_max = int(os.environ.get("EXTRACT_MAX_CHARS", "12000"))
        max_chars = int(req.maxChars) if req.maxChars is not None else default_max
        max_chars = max(500, min(max_chars, 200_000))
        if total > max_chars:
            clipped = text[:max_chars].rstrip()
            clipped += "\n\n[TRUNCATED]\nAsk for more by calling /extract/chunk with a higher offset."
            return ExtractResponse(url=req.url, cleanedText=clipped, truncated=True, totalChars=total)
        return ExtractResponse(url=req.url, cleanedText=text, truncated=False, totalChars=total)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extract failed: {e}")


def _split_into_parts(text: str, num_parts: int, max_chars_per_part: int) -> tuple[list[tuple[int, str]], bool]:
    """
    Split text into `num_parts` parts, aiming for paragraph boundaries.
    Returns (parts, truncated) where parts is list of (offset, part_text).
    Always returns exactly num_parts parts; some may be empty if input is short.
    """
    if num_parts < 2:
        num_parts = 2
    max_chars_per_part = max(500, min(int(max_chars_per_part), 200_000))

    total = len(text)
    if total == 0:
        return ([(0, "") for _ in range(num_parts)], False)

    # If the text is huge, only deliver up to num_parts * max_chars_per_part via this endpoint.
    deliver_cap = num_parts * max_chars_per_part
    truncated = total > deliver_cap
    deliver_text = text[:deliver_cap] if truncated else text

    paras = [p.strip() for p in deliver_text.split("\n\n") if p.strip()]
    if not paras:
        # Fallback: hard split by char length
        parts: list[tuple[int, str]] = []
        for i in range(num_parts):
            start = i * max_chars_per_part
            parts.append((start, deliver_text[start : start + max_chars_per_part]))
        return (parts, truncated)

    # Target size per part based on deliver_text length.
    target = max(1, len(deliver_text) // num_parts)
    parts_text: list[str] = []
    current: list[str] = []
    current_len = 0

    for p in paras:
        p_len = len(p) + (2 if current else 0)
        if current and (current_len + p_len > target) and (len(parts_text) < num_parts - 1):
            parts_text.append("\n\n".join(current).strip())
            current = [p]
            current_len = len(p)
        else:
            current.append(p)
            current_len += p_len

    if current:
        parts_text.append("\n\n".join(current).strip())

    # Normalize to exactly num_parts parts.
    if len(parts_text) < num_parts:
        parts_text.extend([""] * (num_parts - len(parts_text)))
    elif len(parts_text) > num_parts:
        # Merge overflow into the last part.
        head = parts_text[: num_parts - 1]
        tail = "\n\n".join(parts_text[num_parts - 1 :]).strip()
        parts_text = head + [tail]

    # Enforce max_chars_per_part for each part (hard cap).
    capped: list[str] = []
    for pt in parts_text:
        if len(pt) > max_chars_per_part:
            capped.append(pt[:max_chars_per_part].rstrip() + "\n\n[PART TRUNCATED]")
        else:
            capped.append(pt)

    # Compute offsets by searching sequentially (best-effort).
    offsets: list[int] = []
    cursor = 0
    for pt in capped:
        if not pt:
            offsets.append(cursor)
            continue
        idx = deliver_text.find(pt.replace("\n\n[PART TRUNCATED]", "").rstrip(), cursor)
        if idx == -1:
            offsets.append(cursor)
        else:
            offsets.append(idx)
            cursor = idx + len(pt)

    return (list(zip(offsets, capped)), truncated)


@app.post("/extract/parts", response_model=ExtractPartsResponse)
async def extract_parts(req: ExtractPartsRequest) -> ExtractPartsResponse:
    """
    Fetches & extracts the page text, then returns it split into N parts (default 4).
    This is designed for agents/LLMs to process large pages safely by summarizing each part.
    """
    try:
        text = await fetch_and_extract_main_text(req.url)
        if not text or len(text) < 200:
            raise HTTPException(status_code=400, detail="Could not extract enough readable text from that URL.")

        num_parts = int(req.parts or 4)
        max_chars_per_part = int(req.maxCharsPerPart or 9000)
        parts_with_offsets, truncated = _split_into_parts(text, num_parts=num_parts, max_chars_per_part=max_chars_per_part)
        parts = [
            ExtractPart(index=i + 1, totalParts=num_parts, offset=off, text=pt)
            for i, (off, pt) in enumerate(parts_with_offsets)
        ]
        return ExtractPartsResponse(url=req.url, title=None, parts=parts, truncated=truncated, totalChars=len(text))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extract parts failed: {e}")


@app.post("/summarize", response_model=SummarizeResponse)
async def summarize(req: SummarizeRequest) -> SummarizeResponse:
    """
    Backend summarization (no ElevenLabs call required).
    Uses Gemini via API key (GEMINI_API_KEY or GOOGLE_API_KEY) and stores the final summary in notes.
    """
    try:
        text = await fetch_and_extract_main_text(req.url)
        if not text or len(text) < 200:
            raise HTTPException(status_code=400, detail="Could not extract enough readable text from that URL.")

        parts_with_offsets, truncated = _split_into_parts(
            text, num_parts=int(req.parts or 4), max_chars_per_part=int(req.maxCharsPerPart or 9000)
        )
        parts_text = [pt for _, pt in parts_with_offsets if pt.strip()]
        if not parts_text:
            raise HTTPException(status_code=400, detail="No readable text parts could be extracted.")

        per_part_summaries: list[str] = []
        for i, pt in enumerate(parts_text, start=1):
            prompt = (
                "You are a study tutor.\n"
                "Summarize the following content PART into:\n"
                "- 1 short paragraph\n"
                "- 5 bullet key points\n"
                "- 3 important terms with definitions\n\n"
                f"PART {i}/{len(parts_text)}:\n{pt}"
            )
            per_part_summaries.append(await gemini_generate_text(prompt=prompt))

        combine_prompt = (
            "You are a study tutor.\n"
            "Combine the PART summaries into a final output with:\n"
            "1) A clear 8-12 sentence summary\n"
            "2) 10 key bullets (crisp)\n"
            "3) 5 quick-check questions (no answers)\n\n"
            "PART SUMMARIES:\n\n"
            + "\n\n---\n\n".join(per_part_summaries)
        )
        final_summary = await gemini_generate_text(prompt=combine_prompt)

        # Store in notes so UI + DOCX download show it immediately.
        try:
            notes_repo.set_summary(req.url, final_summary)
        except Exception:
            # Don't fail summarization if notes storage hiccups.
            pass

        return SummarizeResponse(
            url=req.url,
            summary=final_summary,
            model=get_gemini_model(),
            truncated=truncated,
            totalChars=len(text),
        )
    except GeminiError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarize failed: {e}")


@app.post("/notes/reset", response_model=NotesGetResponse)
def notes_reset(req: NotesResetRequest) -> NotesGetResponse:
    try:
        rec = notes_repo.reset(req.url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Notes reset failed: {e}")
    return NotesGetResponse(
        url=rec.url,
        summary=rec.summary,
        questions=rec.questions,
        turns=rec.turns,
        qa=rec.qa,
        quizzes=rec.quizzes,
        updatedAt=rec.updated_at,
    )


@app.post("/notes/set_summary", response_model=NotesGetResponse)
def notes_set_summary(req: NotesSetSummaryRequest) -> NotesGetResponse:
    try:
        rec = notes_repo.set_summary(req.url, req.summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Notes set_summary failed: {e}")
    return NotesGetResponse(
        url=rec.url,
        summary=rec.summary,
        questions=rec.questions,
        turns=rec.turns,
        qa=rec.qa,
        quizzes=rec.quizzes,
        updatedAt=rec.updated_at,
    )


@app.post("/notes/append_question", response_model=NotesGetResponse)
def notes_append_question(req: NotesAppendQuestionRequest) -> NotesGetResponse:
    try:
        rec = notes_repo.append_question(req.url, req.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Notes append_question failed: {e}")
    return NotesGetResponse(
        url=rec.url,
        summary=rec.summary,
        questions=rec.questions,
        turns=rec.turns,
        qa=rec.qa,
        quizzes=rec.quizzes,
        updatedAt=rec.updated_at,
    )


@app.post("/notes/append_turn", response_model=NotesGetResponse)
def notes_append_turn(req: NotesAppendTurnRequest) -> NotesGetResponse:
    try:
        rec = notes_repo.append_turn(req.url, req.role, req.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Notes append_turn failed: {e}")
    return NotesGetResponse(
        url=rec.url,
        summary=rec.summary,
        questions=rec.questions,
        turns=rec.turns,
        qa=rec.qa,
        quizzes=rec.quizzes,
        updatedAt=rec.updated_at,
    )


@app.post("/notes/append_qa", response_model=NotesGetResponse)
def notes_append_qa(req: NotesAppendQARequest) -> NotesGetResponse:
    try:
        rec = notes_repo.append_qa(req.url, req.question, req.answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Notes append_qa failed: {e}")
    return NotesGetResponse(
        url=rec.url,
        summary=rec.summary,
        questions=rec.questions,
        turns=rec.turns,
        qa=rec.qa,
        quizzes=rec.quizzes,
        updatedAt=rec.updated_at,
    )


@app.post("/notes/append_quiz", response_model=NotesGetResponse)
def notes_append_quiz(req: NotesAppendQuizRequest) -> NotesGetResponse:
    try:
        rec = notes_repo.append_quiz(req.url, req.question, req.userAnswer, req.correctAnswer, req.explanation)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Notes append_quiz failed: {e}")
    return NotesGetResponse(
        url=rec.url,
        summary=rec.summary,
        questions=rec.questions,
        turns=rec.turns,
        qa=rec.qa,
        quizzes=rec.quizzes,
        updatedAt=rec.updated_at,
    )


@app.get("/notes", response_model=NotesGetResponse)
def notes_get(url: str) -> NotesGetResponse:
    try:
        rec = notes_repo.get(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Notes get failed: {e}")
    if not rec:
        # If notes were not started yet, return an empty record to simplify clients.
        try:
            rec = notes_repo.reset(url)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Notes reset failed: {e}")
    return NotesGetResponse(
        url=rec.url,
        summary=rec.summary,
        questions=rec.questions,
        turns=rec.turns,
        qa=rec.qa,
        quizzes=rec.quizzes,
        updatedAt=rec.updated_at,
    )


@app.get("/notes/download.docx")
def notes_download_docx(url: str) -> StreamingResponse:
    rec = notes_repo.get(url) or notes_repo.reset(url)

    doc = Document()
    doc.add_heading("Voice AI Study Notes", level=1)
    doc.add_paragraph(f"Source URL: {rec.url}")
    doc.add_paragraph(f"Last updated: {rec.updated_at}")

    doc.add_heading("Summary", level=2)
    doc.add_paragraph(rec.summary or "(No summary saved yet)")

    doc.add_heading("Q&A", level=2)
    if rec.qa:
        for idx, pair in enumerate(rec.qa, start=1):
            q = (pair.get("q") or "").strip()
            a = (pair.get("a") or "").strip()
            if q:
                doc.add_paragraph(f"Q{idx}. {q}")
            if a:
                doc.add_paragraph(f"A{idx}. {a}")
            doc.add_paragraph("")  # spacer
    else:
        doc.add_paragraph("(No Q&A saved yet)")

    doc.add_heading("Quizzes", level=2)
    if rec.quizzes:
        for idx, qz in enumerate(rec.quizzes, start=1):
            q = (qz.get("question") or "").strip()
            ua = (qz.get("userAnswer") or "").strip()
            ca = (qz.get("correctAnswer") or "").strip()
            ex = (qz.get("explanation") or "").strip()
            if q:
                doc.add_paragraph(f"Quiz {idx}: {q}")
            if ua:
                doc.add_paragraph(f"Your answer: {ua}")
            if ca:
                doc.add_paragraph(f"Correct answer: {ca}")
            if ex:
                doc.add_paragraph(f"Explanation: {ex}")
            doc.add_paragraph("")  # spacer
    else:
        doc.add_paragraph("(No quizzes saved yet)")

    # Back-compat sections (optional)
    if rec.turns:
        doc.add_heading("Call transcript (raw)", level=2)
        for t in rec.turns:
            role = (t.get("role") or "").strip().lower()
            text = (t.get("text") or "").strip()
            if not text:
                continue
            prefix = "You:" if role == "user" else "Tutor:"
            doc.add_paragraph(f"{prefix} {text}")

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



