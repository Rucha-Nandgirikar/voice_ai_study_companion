from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup
from readability import Document
from youtube_transcript_api import YouTubeTranscriptApi


def _clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def fetch_and_extract_main_text(url: str) -> str:
    """
    Fetches HTML and extracts main readable text.
    Best-effort: Readability -> BeautifulSoup fallback.
    """
    # Special-case: YouTube transcript (best-effort; only works if captions are available).
    yt_text = _try_youtube_transcript(url)
    if yt_text:
        return yt_text

    async with httpx.AsyncClient(
        timeout=20,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; VoiceAIStudyCompanion/1.0; +https://example.com)"
        },
    ) as client:
        r = await client.get(url)
        r.raise_for_status()
        html = r.text

    # Try Readability
    try:
        doc = Document(html)
        content_html = doc.summary(html_partial=True)
        soup = BeautifulSoup(content_html, "html.parser")
        text = soup.get_text("\n")
        text = _clean_text(text)
        if len(text) >= 200:
            return text
    except Exception:
        pass

    # Fallback: strip scripts/styles and get body text
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "form"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = _clean_text(text)
    return text


def _extract_youtube_video_id(url: str) -> str | None:
    try:
        u = urlparse(url)
    except Exception:
        return None

    host = (u.netloc or "").lower()
    path = u.path or ""

    # youtu.be/<id>
    if "youtu.be" in host:
        vid = path.strip("/").split("/")[0]
        return vid or None

    # youtube.com/watch?v=<id>
    if "youtube.com" in host:
        qs = parse_qs(u.query or "")
        vid = (qs.get("v") or [None])[0]
        if vid:
            return vid

        # youtube.com/embed/<id>
        if path.startswith("/embed/"):
            vid = path.split("/embed/", 1)[1].split("/")[0]
            return vid or None

    return None


def _try_youtube_transcript(url: str) -> str | None:
    vid = _extract_youtube_video_id(url)
    if not vid:
        return None

    try:
        # Prefer English; will fall back to whatever is available.
        items = YouTubeTranscriptApi.get_transcript(vid, languages=["en", "en-US", "en-GB"])
        text = "\n".join((it.get("text") or "") for it in items).strip()
        text = _clean_text(text)
        return text if len(text) >= 200 else None
    except Exception:
        return None



