from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Protocol


def _now_iso() -> str:
    # Keep ISO in UTC-like format; DB uses timestamptz anyway.
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class StudySession:
    session_id: str
    url: str
    selected_topics: list[str] = field(default_factory=list)
    completed_topics: list[str] = field(default_factory=list)
    current_topic: str = ""
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)


@dataclass
class Notes:
    session_id: str
    url: str
    summary: str = ""
    questions: list[str] = field(default_factory=list)
    turns: list[dict[str, str]] = field(default_factory=list)
    qa: list[dict[str, str]] = field(default_factory=list)
    quizzes: list[dict[str, str]] = field(default_factory=list)
    updated_at: str = field(default_factory=_now_iso)


class StudyRepo(Protocol):
    def ensure_schema(self) -> None: ...

    def start_session(self, url: str, selected_topics: list[str]) -> StudySession: ...

    def get_session(self, session_id: str) -> StudySession | None: ...

    def latest_session_for_url(self, url: str) -> StudySession | None: ...

    def find_session_by_url_and_topics(self, url: str, selected_topics: list[str]) -> StudySession | None: ...

    def list_sessions(self, limit: int = 50) -> list[StudySession]: ...

    def delete_session(self, session_id: str) -> None: ...

    # Notes
    def reset_notes(self, session_id: str) -> Notes: ...

    def get_notes(self, session_id: str) -> Notes | None: ...

    def set_summary(self, session_id: str, summary: str) -> Notes: ...

    def append_turn(self, session_id: str, role: str, text: str) -> Notes: ...

    def append_qa(self, session_id: str, question: str, answer: str) -> Notes: ...

    def append_quiz(
        self, session_id: str, question: str, user_answer: str, correct_answer: str, explanation: str
    ) -> Notes: ...

    def mark_topic_done(self, session_id: str, topic_title: str) -> StudySession: ...


class InMemoryStudyRepo:
    def __init__(self) -> None:
        self._sessions: dict[str, StudySession] = {}
        self._notes: dict[str, Notes] = {}

    def ensure_schema(self) -> None:
        return

    def start_session(self, url: str, selected_topics: list[str]) -> StudySession:
        # selected_topics comes from user's fresh selection in the UI (always starts empty, user chooses freely)
        sel = [t.strip() for t in (selected_topics or []) if str(t).strip()][:8]
        # Always create a new session
        sid = f"sess_{uuid.uuid4().hex}"
        # IMPORTANT: Only copy completedTopics from previous sessions. selectedTopics always starts fresh from user's choice.
        latest = self.latest_session_for_url(url)
        completed_from_previous = latest.completed_topics.copy() if latest else []
        s = StudySession(
            session_id=sid,
            url=url,
            selected_topics=sel,  # Fresh selection from user (not copied from previous session)
            completed_topics=completed_from_previous,  # Only completed topics are copied for progress tracking
        )
        self._sessions[sid] = s
        n = Notes(session_id=sid, url=url)
        self._notes[sid] = n
        return s

    def get_session(self, session_id: str) -> StudySession | None:
        return self._sessions.get(session_id)

    def latest_session_for_url(self, url: str) -> StudySession | None:
        # best-effort: pick latest updated session for the url
        items = [s for s in self._sessions.values() if s.url == url]
        items.sort(key=lambda s: s.updated_at, reverse=True)
        return items[0] if items else None

    def find_session_by_url_and_topics(self, url: str, selected_topics: list[str]) -> StudySession | None:
        """Find a session with matching URL and selectedTopics (normalized comparison)."""
        def normalize_topics(ts: list[str]) -> list[str]:
            return sorted([t.strip() for t in ts if str(t).strip()])

        target_normalized = normalize_topics(selected_topics or [])
        for s in self._sessions.values():
            if s.url == url and normalize_topics(s.selected_topics) == target_normalized:
                return s
        return None

    def list_sessions(self, limit: int = 50) -> list[StudySession]:
        items = list(self._sessions.values())
        items.sort(key=lambda s: s.updated_at, reverse=True)
        return items[: max(1, int(limit or 50))]

    def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._notes.pop(session_id, None)

    def reset_notes(self, session_id: str) -> Notes:
        s = self._sessions.get(session_id)
        if not s:
            raise ValueError("Unknown sessionId")
        n = Notes(session_id=session_id, url=s.url)
        self._notes[session_id] = n
        s.updated_at = _now_iso()
        return n

    def get_notes(self, session_id: str) -> Notes | None:
        return self._notes.get(session_id)

    def set_summary(self, session_id: str, summary: str) -> Notes:
        s = self._sessions.get(session_id)
        if not s:
            raise ValueError("Unknown sessionId")
        n = self._notes.get(session_id) or Notes(session_id=session_id, url=s.url)
        n.summary = (summary or "").strip()
        n.updated_at = _now_iso()
        self._notes[session_id] = n
        s.updated_at = n.updated_at
        return n

    def append_turn(self, session_id: str, role: str, text: str) -> Notes:
        s = self._sessions.get(session_id)
        if not s:
            raise ValueError("Unknown sessionId")
        r = (role or "").strip().lower()
        if r not in {"user", "agent"}:
            r = "agent"
        t = (text or "").strip()
        if not t:
            raise ValueError("Missing text")
        n = self._notes.get(session_id) or Notes(session_id=session_id, url=s.url)
        n.turns.append({"role": r, "text": t})
        n.updated_at = _now_iso()
        self._notes[session_id] = n
        s.updated_at = n.updated_at
        return n

    def append_qa(self, session_id: str, question: str, answer: str) -> Notes:
        s = self._sessions.get(session_id)
        if not s:
            raise ValueError("Unknown sessionId")
        q = (question or "").strip()
        a = (answer or "").strip()
        if not q or not a:
            raise ValueError("Missing question/answer")
        n = self._notes.get(session_id) or Notes(session_id=session_id, url=s.url)
        n.qa.append({"q": q, "a": a})
        n.updated_at = _now_iso()
        self._notes[session_id] = n
        s.updated_at = n.updated_at
        return n

    def append_quiz(
        self, session_id: str, question: str, user_answer: str, correct_answer: str, explanation: str
    ) -> Notes:
        s = self._sessions.get(session_id)
        if not s:
            raise ValueError("Unknown sessionId")
        q = (question or "").strip()
        if not q:
            raise ValueError("Missing question")
        ua = (user_answer or "").strip()
        ca = (correct_answer or "").strip()
        ex = (explanation or "").strip()
        n = self._notes.get(session_id) or Notes(session_id=session_id, url=s.url)
        n.quizzes.append(
            {"question": q, "userAnswer": ua, "correctAnswer": ca, "explanation": ex}
        )
        n.updated_at = _now_iso()
        self._notes[session_id] = n
        s.updated_at = n.updated_at
        return n

    def mark_topic_done(self, session_id: str, topic_title: str) -> StudySession:
        s = self._sessions.get(session_id)
        if not s:
            raise ValueError("Unknown sessionId")
        topic = (topic_title or "").strip()
        if not topic:
            raise ValueError("Missing topicTitle")
        # Only add if it's in selectedTopics and not already in completedTopics
        if topic in s.selected_topics and topic not in s.completed_topics:
            s.completed_topics.append(topic)
            s.updated_at = _now_iso()
        return s

class PostgresStudyRepo:
    """
    Postgres persistence keyed by session_id (text).
    New tables:
      - study_sessions
      - session_notes
      - session_qa
      - session_quizzes
    """

    def __init__(self, database_url: str):
        self.database_url = database_url

    def _connect(self):
        import psycopg  # type: ignore
        from psycopg.rows import dict_row  # type: ignore

        return psycopg.connect(self.database_url, row_factory=dict_row)

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS study_sessions (
                      session_id TEXT PRIMARY KEY,
                      url TEXT NOT NULL,
                      selected_topics JSONB NOT NULL DEFAULT '[]'::jsonb,
                      completed_topics JSONB NOT NULL DEFAULT '[]'::jsonb,
                      current_topic TEXT NOT NULL DEFAULT '',
                      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_study_sessions_url ON study_sessions(url);")

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS session_notes (
                      session_id TEXT PRIMARY KEY REFERENCES study_sessions(session_id) ON DELETE CASCADE,
                      url TEXT NOT NULL,
                      summary TEXT NOT NULL DEFAULT '',
                      questions JSONB NOT NULL DEFAULT '[]'::jsonb,
                      turns JSONB NOT NULL DEFAULT '[]'::jsonb,
                      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_session_notes_url ON session_notes(url);")

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS session_qa (
                      id BIGSERIAL PRIMARY KEY,
                      session_id TEXT NOT NULL REFERENCES study_sessions(session_id) ON DELETE CASCADE,
                      q TEXT NOT NULL,
                      a TEXT NOT NULL,
                      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_session_qa_session ON session_qa(session_id);")

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS session_quizzes (
                      id BIGSERIAL PRIMARY KEY,
                      session_id TEXT NOT NULL REFERENCES study_sessions(session_id) ON DELETE CASCADE,
                      question TEXT NOT NULL,
                      user_answer TEXT NOT NULL DEFAULT '',
                      correct_answer TEXT NOT NULL DEFAULT '',
                      explanation TEXT NOT NULL DEFAULT '',
                      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_session_quizzes_session ON session_quizzes(session_id);")

                # Heal NULLs / wrong types
                cur.execute("UPDATE study_sessions SET selected_topics='[]'::jsonb WHERE selected_topics IS NULL;")
                cur.execute("UPDATE study_sessions SET completed_topics='[]'::jsonb WHERE completed_topics IS NULL;")
                cur.execute("UPDATE study_sessions SET selected_topics='[]'::jsonb WHERE jsonb_typeof(selected_topics) <> 'array';")
                cur.execute("UPDATE study_sessions SET completed_topics='[]'::jsonb WHERE jsonb_typeof(completed_topics) <> 'array';")
                cur.execute("UPDATE session_notes SET questions='[]'::jsonb WHERE questions IS NULL;")
                cur.execute("UPDATE session_notes SET turns='[]'::jsonb WHERE turns IS NULL;")
                cur.execute("UPDATE session_notes SET questions='[]'::jsonb WHERE jsonb_typeof(questions) <> 'array';")
                cur.execute("UPDATE session_notes SET turns='[]'::jsonb WHERE jsonb_typeof(turns) <> 'array';")
            conn.commit()

    def start_session(self, url: str, selected_topics: list[str]) -> StudySession:
        # selected_topics comes from user's fresh selection in the UI (always starts empty, user chooses freely)
        sel = [t.strip() for t in (selected_topics or []) if str(t).strip()][:8]
        # Always create a new session
        # IMPORTANT: Only copy completedTopics from previous sessions. selectedTopics always starts fresh from user's choice.
        latest = self.latest_session_for_url(url)
        completed_from_previous = latest.completed_topics.copy() if latest else []
        sid = f"sess_{uuid.uuid4().hex}"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO study_sessions (session_id, url, selected_topics, completed_topics, current_topic, created_at, updated_at)
                    VALUES (%s, %s, %s::jsonb, %s::jsonb, '', now(), now());
                    """,
                    (sid, url, json.dumps(sel), json.dumps(completed_from_previous)),  # sel = fresh user selection, completed_from_previous = copied for progress
                )
                cur.execute(
                    """
                    INSERT INTO session_notes (session_id, url, summary, questions, turns, updated_at)
                    VALUES (%s, %s, '', '[]'::jsonb, '[]'::jsonb, now());
                    """,
                    (sid, url),
                )
            conn.commit()
        return self.get_session(sid) or StudySession(session_id=sid, url=url, selected_topics=sel)

    def get_session(self, session_id: str) -> StudySession | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT session_id, url, selected_topics, completed_topics, current_topic, created_at, updated_at
                      FROM study_sessions
                     WHERE session_id = %s;
                    """,
                    (session_id,),
                )
                row = cur.fetchone()
        return _row_to_session(row)

    def latest_session_for_url(self, url: str) -> StudySession | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT session_id, url, selected_topics, completed_topics, current_topic, created_at, updated_at
                      FROM study_sessions
                     WHERE url = %s
                     ORDER BY created_at DESC
                     LIMIT 1;
                    """,
                    (url,),
                )
                row = cur.fetchone()
        return _row_to_session(row)

    def find_session_by_url_and_topics(self, url: str, selected_topics: list[str]) -> StudySession | None:
        """Find a session with matching URL and selectedTopics (normalized comparison)."""
        def normalize_topics(ts: list[str]) -> list[str]:
            return sorted([t.strip() for t in ts if str(t).strip()])

        target_normalized = normalize_topics(selected_topics or [])
        with self._connect() as conn:
            with conn.cursor() as cur:
                # Fetch all sessions for this URL and compare selected_topics
                cur.execute(
                    """
                    SELECT session_id, url, selected_topics, completed_topics, current_topic, created_at, updated_at
                      FROM study_sessions
                     WHERE url = %s
                     ORDER BY updated_at DESC;
                    """,
                    (url,),
                )
                rows = cur.fetchall() or []
                for row in rows:
                    s = _row_to_session(row)
                    if s and normalize_topics(s.selected_topics) == target_normalized:
                        return s
        return None

    def list_sessions(self, limit: int = 50) -> list[StudySession]:
        lim = max(1, min(int(limit or 50), 200))
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT session_id, url, selected_topics, completed_topics, current_topic, created_at, updated_at
                      FROM study_sessions
                     ORDER BY updated_at DESC
                     LIMIT {lim};
                    """
                )
                rows = cur.fetchall() or []
        out: list[StudySession] = []
        for r in rows:
            s = _row_to_session(r)
            if s:
                out.append(s)
        return out

    def delete_session(self, session_id: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM study_sessions WHERE session_id = %s;", (session_id,))
            conn.commit()

    def reset_notes(self, session_id: str) -> Notes:
        s = self.get_session(session_id)
        if not s:
            raise ValueError("Unknown sessionId")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE session_notes
                       SET summary = '',
                           questions = '[]'::jsonb,
                           turns = '[]'::jsonb,
                           updated_at = now()
                     WHERE session_id = %s;
                    """,
                    (session_id,),
                )
                cur.execute("DELETE FROM session_qa WHERE session_id = %s;", (session_id,))
                cur.execute("DELETE FROM session_quizzes WHERE session_id = %s;", (session_id,))
                cur.execute("UPDATE study_sessions SET updated_at = now() WHERE session_id = %s;", (session_id,))
            conn.commit()
        return self.get_notes(session_id) or Notes(session_id=session_id, url=s.url)

    def get_notes(self, session_id: str) -> Notes | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT session_id, url, summary, questions, turns, updated_at FROM session_notes WHERE session_id = %s;",
                    (session_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                cur.execute("SELECT q, a FROM session_qa WHERE session_id = %s ORDER BY id ASC;", (session_id,))
                qa_rows = cur.fetchall() or []
                cur.execute(
                    """
                    SELECT question, user_answer, correct_answer, explanation
                      FROM session_quizzes
                     WHERE session_id = %s
                     ORDER BY id ASC;
                    """,
                    (session_id,),
                )
                quiz_rows = cur.fetchall() or []

        n = _row_to_notes(row)
        n.qa = [{"q": (r.get("q") or ""), "a": (r.get("a") or "")} for r in qa_rows]
        n.quizzes = [
            {
                "question": (r.get("question") or ""),
                "userAnswer": (r.get("user_answer") or ""),
                "correctAnswer": (r.get("correct_answer") or ""),
                "explanation": (r.get("explanation") or ""),
            }
            for r in quiz_rows
        ]
        return n

    def set_summary(self, session_id: str, summary: str) -> Notes:
        s = self.get_session(session_id)
        if not s:
            raise ValueError("Unknown sessionId")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE session_notes
                       SET summary = %s,
                           updated_at = now()
                     WHERE session_id = %s;
                    """,
                    ((summary or "").strip(), session_id),
                )
                cur.execute("UPDATE study_sessions SET updated_at = now() WHERE session_id = %s;", (session_id,))
            conn.commit()
        return self.get_notes(session_id) or Notes(session_id=session_id, url=s.url, summary=(summary or "").strip())

    def append_turn(self, session_id: str, role: str, text: str) -> Notes:
        s = self.get_session(session_id)
        if not s:
            raise ValueError("Unknown sessionId")
        r = (role or "").strip().lower()
        if r not in {"user", "agent"}:
            r = "agent"
        t = (text or "").strip()
        if not t:
            raise ValueError("Missing text")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE session_notes
                       SET turns = COALESCE(turns, '[]'::jsonb) || jsonb_build_array(
                             jsonb_build_object('role', %s::text, 'text', %s::text)
                           ),
                           updated_at = now()
                     WHERE session_id = %s;
                    """,
                    (r, t, session_id),
                )
                cur.execute("UPDATE study_sessions SET updated_at = now() WHERE session_id = %s;", (session_id,))
            conn.commit()
        return self.get_notes(session_id) or Notes(session_id=session_id, url=s.url)

    def append_qa(self, session_id: str, question: str, answer: str) -> Notes:
        s = self.get_session(session_id)
        if not s:
            raise ValueError("Unknown sessionId")
        q = (question or "").strip()
        a = (answer or "").strip()
        if not q or not a:
            raise ValueError("Missing question/answer")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO session_qa (session_id, q, a) VALUES (%s, %s, %s);", (session_id, q, a))
                cur.execute("UPDATE session_notes SET updated_at = now() WHERE session_id = %s;", (session_id,))
                cur.execute("UPDATE study_sessions SET updated_at = now() WHERE session_id = %s;", (session_id,))
            conn.commit()
        return self.get_notes(session_id) or Notes(session_id=session_id, url=s.url)

    def append_quiz(
        self, session_id: str, question: str, user_answer: str, correct_answer: str, explanation: str
    ) -> Notes:
        s = self.get_session(session_id)
        if not s:
            raise ValueError("Unknown sessionId")
        q = (question or "").strip()
        if not q:
            raise ValueError("Missing question")
        ua = (user_answer or "").strip()
        ca = (correct_answer or "").strip()
        ex = (explanation or "").strip()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO session_quizzes (session_id, question, user_answer, correct_answer, explanation)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (session_id, q, ua, ca, ex),
                )
                cur.execute("UPDATE session_notes SET updated_at = now() WHERE session_id = %s;", (session_id,))
                cur.execute("UPDATE study_sessions SET updated_at = now() WHERE session_id = %s;", (session_id,))
            conn.commit()
        return self.get_notes(session_id) or Notes(session_id=session_id, url=s.url)

    def mark_topic_done(self, session_id: str, topic_title: str) -> StudySession:
        s = self.get_session(session_id)
        if not s:
            raise ValueError("Unknown sessionId")
        topic = (topic_title or "").strip()
        if not topic:
            raise ValueError("Missing topicTitle")
        # Only add if it's in selectedTopics and not already in completedTopics
        if topic not in s.selected_topics:
            raise ValueError(f"Topic '{topic}' is not in selectedTopics for this session")
        if topic in s.completed_topics:
            # Already marked as done, just return
            return s
        updated_completed = s.completed_topics + [topic]
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE study_sessions
                       SET completed_topics = %s::jsonb,
                           updated_at = now()
                     WHERE session_id = %s;
                    """,
                    (json.dumps(updated_completed), session_id),
                )
            conn.commit()
        return self.get_session(session_id) or s

def _row_to_session(row: dict | None) -> StudySession | None:
    if not row:
        return None
    def _iso(v):
        return v.isoformat() if hasattr(v, "isoformat") else str(v or "")

    return StudySession(
        session_id=row.get("session_id") or "",
        url=row.get("url") or "",
        selected_topics=_coerce_json_list(row.get("selected_topics")),
        completed_topics=_coerce_json_list(row.get("completed_topics")),
        current_topic=row.get("current_topic") or "",
        created_at=_iso(row.get("created_at")),
        updated_at=_iso(row.get("updated_at")),
    )


def _row_to_notes(row: dict | None) -> Notes:
    if not row:
        raise ValueError("Missing row")
    def _iso(v):
        return v.isoformat() if hasattr(v, "isoformat") else str(v or "")

    return Notes(
        session_id=row.get("session_id") or "",
        url=row.get("url") or "",
        summary=row.get("summary") or "",
        questions=_coerce_json_list(row.get("questions")),
        turns=_coerce_json_list(row.get("turns")),
        qa=[],
        quizzes=[],
        updated_at=_iso(row.get("updated_at")),
    )


def _coerce_json_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode("utf-8")
        except Exception:
            return []
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    try:
        parsed = json.loads(str(value))
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def make_study_repo() -> StudyRepo:
    db_url = (os.environ.get("DATABASE_URL") or "").strip()
    if db_url:
        return PostgresStudyRepo(db_url)
    return InMemoryStudyRepo()


