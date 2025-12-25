from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class NotesRecord:
    url: str
    summary: str = ""
    questions: list[str] = field(default_factory=list)
    turns: list[dict[str, str]] = field(default_factory=list)  # [{"role":"user|agent","text":"..."}]
    qa: list[dict[str, str]] = field(default_factory=list)  # [{"q":"...","a":"..."}]
    quizzes: list[dict[str, str]] = field(default_factory=list)  # [{"question","userAnswer","correctAnswer","explanation"}]
    updated_at: str = field(default_factory=_now_iso)

    def touch(self) -> None:
        self.updated_at = _now_iso()


# MVP storage: in-memory (will reset if the Cloud Run instance restarts).
_STORE: dict[str, NotesRecord] = {}


def reset_notes(url: str) -> NotesRecord:
    rec = NotesRecord(url=url)
    _STORE[url] = rec
    return rec


def get_notes(url: str) -> NotesRecord | None:
    return _STORE.get(url)


def set_summary(url: str, summary: str) -> NotesRecord:
    rec = _STORE.get(url) or NotesRecord(url=url)
    rec.summary = summary.strip()
    rec.touch()
    _STORE[url] = rec
    return rec


def append_question(url: str, question: str) -> NotesRecord:
    rec = _STORE.get(url) or NotesRecord(url=url)
    q = question.strip()
    if q:
        rec.questions.append(q)
    rec.touch()
    _STORE[url] = rec
    return rec


def append_turn(url: str, role: str, text: str) -> NotesRecord:
    rec = _STORE.get(url) or NotesRecord(url=url)
    r = (role or "").strip().lower()
    if r not in {"user", "agent"}:
        r = "agent"
    t = (text or "").strip()
    if t:
        rec.turns.append({"role": r, "text": t})
    rec.touch()
    _STORE[url] = rec
    return rec


def append_qa(url: str, question: str, answer: str) -> NotesRecord:
    rec = _STORE.get(url) or NotesRecord(url=url)
    q = (question or "").strip()
    a = (answer or "").strip()
    if q and a:
        rec.qa.append({"q": q, "a": a})
    rec.touch()
    _STORE[url] = rec
    return rec


def append_quiz(
    url: str,
    question: str,
    user_answer: str,
    correct_answer: str,
    explanation: str,
) -> NotesRecord:
    rec = _STORE.get(url) or NotesRecord(url=url)
    q = (question or "").strip()
    ua = (user_answer or "").strip()
    ca = (correct_answer or "").strip()
    ex = (explanation or "").strip()
    if q:
        rec.quizzes.append(
            {
                "question": q,
                "userAnswer": ua,
                "correctAnswer": ca,
                "explanation": ex,
            }
        )
    rec.touch()
    _STORE[url] = rec
    return rec


