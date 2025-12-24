from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup
from readability import Document


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



