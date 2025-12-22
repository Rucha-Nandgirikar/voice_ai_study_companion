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
        model = _env("GEMINI_MODEL", "gemini-1.5-pro")
        self.model = model

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
        resp = self.client.models.generate_content(
            model=self.model,
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
        # google-genai returns parsed JSON in resp.parsed when schema is provided.
        parsed = getattr(resp, "parsed", None)
        if isinstance(parsed, dict):
            return parsed
        # fallback: best-effort
        text = (resp.text or "").strip()
        raise RuntimeError(f"Model did not return parsed JSON. Raw: {text[:500]}")


