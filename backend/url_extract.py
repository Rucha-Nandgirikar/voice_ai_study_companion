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


def _is_github(host: str) -> bool:
    host = (host or "").lower()
    return host == "github.com" or host.endswith(".github.com")


def _github_owner_repo_from_path(path: str) -> tuple[str, str] | None:
    # /owner/repo/...
    parts = [p for p in (path or "").split("/") if p]
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    # ignore obvious non-repo paths
    if owner in {"features", "orgs", "settings", "login", "apps"}:
        return None
    return owner, repo


async def _try_github_raw(url: str) -> str | None:
    """
    If the URL points to a GitHub repo page or file view, fetch the raw content instead.
    This avoids extracting GitHub's UI shell ("signed in/out", nav, etc).
    """
    try:
        u = urlparse(url)
    except Exception:
        return None

    if not _is_github(u.netloc or ""):
        return None

    owner_repo = _github_owner_repo_from_path(u.path or "")
    if not owner_repo:
        return None
    owner, repo = owner_repo

    parts = [p for p in (u.path or "").split("/") if p]

    async with httpx.AsyncClient(
        timeout=20,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (compatible; VoiceAIStudyCompanion/1.0)"},
    ) as client:
        # Case A: /owner/repo/blob/<branch>/<path...>  -> raw file
        if len(parts) >= 5 and parts[2] == "blob":
            branch = parts[3]
            file_path = "/".join(parts[4:])
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
            try:
                r = await client.get(raw_url)
                r.raise_for_status()
                text = _clean_text(r.text)
                return text if len(text) >= 50 else None
            except Exception:
                return None

        # Case B: repo root (or any non-blob page): fetch default branch then try README.*
        # GitHub API is unauthenticated but rate-limited; best-effort.
        default_branch = None
        try:
            meta = await client.get(f"https://api.github.com/repos/{owner}/{repo}")
            if meta.status_code == 200:
                default_branch = (meta.json() or {}).get("default_branch")
        except Exception:
            default_branch = None

        # Try common branches if API fails
        branches = [b for b in [default_branch, "main", "master"] if b]
        readmes = ["README.md", "README.MD", "README.rst", "README.txt", "readme.md"]

        for br in branches:
            for name in readmes:
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{br}/{name}"
                try:
                    r = await client.get(raw_url)
                    if r.status_code == 404:
                        continue
                    r.raise_for_status()
                    text = _clean_text(r.text)
                    if len(text) >= 200:
                        return text
                except Exception:
                    continue

    return None


async def fetch_and_extract_main_text(url: str) -> str:
    """
    Fetches HTML and extracts main readable text.
    Best-effort: Readability -> BeautifulSoup fallback.
    """
    # Special-case: GitHub pages often extract UI shell instead of README.
    gh_text = await _try_github_raw(url)
    if gh_text:
        return gh_text

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



