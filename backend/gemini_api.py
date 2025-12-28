from __future__ import annotations

import os
import re
from typing import Any

import httpx


class GeminiError(RuntimeError):
    pass


class GeminiRateLimitError(GeminiError):
    def __init__(self, message: str, retry_after_seconds: int | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def get_gemini_api_key() -> str | None:
    # Accept either name to reduce confusion.
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def get_gemini_model() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


async def gemini_generate_text(*, prompt: str, model: str | None = None, api_key: str | None = None) -> str:
    """
    Minimal Gemini REST call (no SDK) to avoid extra dependencies.
    Uses Generative Language API: models/{model}:generateContent
    """
    api_key = api_key or get_gemini_api_key()
    if not api_key:
        raise GeminiError("Missing GEMINI_API_KEY (or GOOGLE_API_KEY). Set it in Cloud Run env vars or locally.")

    model = model or get_gemini_model()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    payload: dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 900,
        },
    }

    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.post(url, params={"key": api_key}, json=payload)
        if r.status_code >= 400:
            # Try to detect quota/rate-limit and surface it cleanly.
            retry_after: int | None = None
            try:
                data = r.json()
                err = (data or {}).get("error") or {}
                details = err.get("details") or []
                for d in details:
                    if (d or {}).get("@type", "").endswith("RetryInfo"):
                        delay = (d or {}).get("retryDelay") or ""
                        m = re.match(r"^(?P<s>\d+)\s*s?$", str(delay).strip())
                        if m:
                            retry_after = int(m.group("s"))
            except Exception:
                pass

            if r.status_code == 429:
                raise GeminiRateLimitError(
                    f"Gemini rate limit / quota exceeded. Fix billing/quota, then retry."
                    + (f" Suggested retry after ~{retry_after}s." if retry_after else ""),
                    retry_after_seconds=retry_after,
                )

            raise GeminiError(f"Gemini generate failed ({r.status_code}): {r.text}")
        data = r.json()

    try:
        candidates = data.get("candidates") or []
        content = (candidates[0] or {}).get("content") or {}
        parts = content.get("parts") or []
        text = (parts[0] or {}).get("text") or ""
        text = str(text).strip()
        if not text:
            raise KeyError("empty text")
        return text
    except Exception as e:
        raise GeminiError(f"Gemini response parse failed: {e}; raw={data}")


