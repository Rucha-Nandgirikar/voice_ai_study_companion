from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import (
    ExtractRequest,
    ExtractResponse,
)
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



