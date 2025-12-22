from __future__ import annotations

import os
from typing import Any

from google import genai
from google.genai import types


def _env(name: str, default: str | None = None) -> str | None:
    val = os.environ.get(name)
    if val is None or val.strip() == "":
        return default
    return val


class GeminiClient:
    """
    Supports two modes:
    - Vertex AI mode (recommended on Cloud Run): GOOGLE_CLOUD_PROJECT + GOOGLE_CLOUD_LOCATION
    - API key mode (local/dev): GOOGLE_API_KEY
    """

    def __init__(self) -> None:
        # Vertex AI model availability can vary by project/region. Prefer a widely available default.
        # Users can override with GEMINI_MODEL env var (e.g., gemini-1.5-pro-002).
        self.model = _env("GEMINI_MODEL", "gemini-1.5-flash-002")  # good default on Vertex

        api_key = _env("GOOGLE_API_KEY")
        project = _env("GOOGLE_CLOUD_PROJECT")
        location = _env("GOOGLE_CLOUD_LOCATION", "us-central1")

        if api_key:
            self.client = genai.Client(api_key=api_key)
        elif project:
            # Uses ADC (service account) on Cloud Run
            self.client = genai.Client(vertexai=True, project=project, location=location)
        else:
            raise RuntimeError(
                "Missing config: set GOOGLE_API_KEY (local) or GOOGLE_CLOUD_PROJECT (+ optional GOOGLE_CLOUD_LOCATION) (Vertex/Cloud Run)."
            )

    def generate_json(self, *, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Uses response_schema to strongly bias well-formed JSON output.
        """
        # Retry with fallback models if the configured model isn't available.
        candidates = [
            self.model,
            "gemini-1.5-flash",
            "gemini-1.5-pro-002",
            "gemini-1.5-pro",
        ]

        last_err: Exception | None = None
        resp = None
        for m in candidates:
            try:
                resp = self.client.models.generate_content(
                    model=m,
                    contents=[
                        types.Content(role="user", parts=[types.Part(text=user)]),
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        response_mime_type="application/json",
                        response_schema=schema,
                        temperature=0.4,
                    ),
                )
                break
            except Exception as e:
                last_err = e
                msg = str(e)
                # Only retry on model lookup/access style failures.
                if "Publisher Model" in msg and ("NOT_FOUND" in msg or "was not found" in msg or "does not have access" in msg):
                    continue
                raise

        if resp is None:
            raise RuntimeError(f"All model candidates failed. Last error: {last_err}")
        # google-genai returns parsed JSON in resp.parsed when schema is provided.
        parsed = getattr(resp, "parsed", None)
        if isinstance(parsed, dict):
            return parsed
        # fallback: best-effort
        text = (resp.text or "").strip()
        raise RuntimeError(f"Model did not return parsed JSON. Raw: {text[:500]}")




