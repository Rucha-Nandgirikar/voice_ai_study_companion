from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
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
        self.model = _env("GEMINI_MODEL", "gemini-1.5-flash-002")

        api_key = _env("GOOGLE_API_KEY")
        project = _env("GOOGLE_CLOUD_PROJECT")
        location = _env("GOOGLE_CLOUD_LOCATION", "us-central1")

        if api_key:
            self._api_key = api_key
            self._mode = "api_key"
            self.client = genai.Client(api_key=api_key)
        elif project:
            self._api_key = None
            self._mode = "vertex"
            # Uses ADC (service account) on Cloud Run
            self.client = genai.Client(vertexai=True, project=project, location=location)
        else:
            raise RuntimeError(
                "Missing config: set GOOGLE_API_KEY (local) or GOOGLE_CLOUD_PROJECT (+ optional GOOGLE_CLOUD_LOCATION) (Vertex/Cloud Run)."
            )

    def _list_models_api_key(self) -> list[dict[str, Any]]:
        if not self._api_key:
            return []
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        q = urllib.parse.urlencode({"key": self._api_key})
        req = urllib.request.Request(f"{url}?{q}", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:  # nosec - controlled URL
            payload = resp.read().decode("utf-8")
        data = json.loads(payload)
        return list(data.get("models", []) or [])

    @staticmethod
    def _pick_working_models_from_list(models: list[dict[str, Any]]) -> list[str]:
        def supports_generate(m: dict[str, Any]) -> bool:
            methods = m.get("supportedGenerationMethods") or []
            return "generateContent" in methods

        names: list[str] = []
        for m in models:
            if not supports_generate(m):
                continue
            name = (m.get("name") or "").strip()
            if name.startswith("models/"):
                name = name[len("models/") :]
            if name:
                names.append(name)

        # Prefer flash variants for latency/cost, then pro for quality.
        preferred: list[str] = []
        for kw in ["flash", "pro"]:
            for n in names:
                if kw in n and n not in preferred:
                    preferred.append(n)
        for n in names:
            if n not in preferred:
                preferred.append(n)
        return preferred

    def generate_json(self, *, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        candidates: list[str] = [
            self.model,
            "gemini-1.5-flash",
            "gemini-1.5-pro-002",
            "gemini-1.5-pro",
        ]

        last_err: Exception | None = None
        resp = None
        tried: set[str] = set()

        i = 0
        while i < len(candidates):
            m = candidates[i]
            i += 1
            if m in tried:
                continue
            tried.add(m)
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
                is_model_not_found = (
                    "NOT_FOUND" in msg
                    and ("was not found" in msg or "not found" in msg or "is not found" in msg)
                    and ("Publisher Model" in msg or "models/" in msg or "Call ListModels" in msg)
                )

                if is_model_not_found and self._mode == "api_key":
                    try:
                        models = self._list_models_api_key()
                        extra = self._pick_working_models_from_list(models)[:10]
                        candidates.extend(extra)
                    except Exception:
                        pass
                    continue

                if is_model_not_found and self._mode == "vertex":
                    continue

                raise

        if resp is None:
            raise RuntimeError(f"All model candidates failed. Last error: {last_err}")

        parsed = getattr(resp, "parsed", None)
        if isinstance(parsed, dict):
            return parsed

        text = (resp.text or "").strip()
        raise RuntimeError(f"Model did not return parsed JSON. Raw: {text[:500]}")


