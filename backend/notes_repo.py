from __future__ import annotations

import os
import json
from typing import Protocol

from backend.notes_store import NotesRecord, append_qa, append_quiz, get_notes, reset_notes, set_summary


class NotesRepo(Protocol):
    def reset(self, url: str) -> NotesRecord: ...

    def set_summary(self, url: str, summary: str) -> NotesRecord: ...

    def append_question(self, url: str, question: str) -> NotesRecord: ...

    def append_turn(self, url: str, role: str, text: str) -> NotesRecord: ...

    def append_qa(self, url: str, question: str, answer: str) -> NotesRecord: ...

    def append_quiz(
        self, url: str, question: str, user_answer: str, correct_answer: str, explanation: str
    ) -> NotesRecord: ...

    def get(self, url: str) -> NotesRecord | None: ...


class InMemoryNotesRepo:
    def reset(self, url: str) -> NotesRecord:
        return reset_notes(url)

    def set_summary(self, url: str, summary: str) -> NotesRecord:
        return set_summary(url, summary)

    def append_question(self, url: str, question: str) -> NotesRecord:
        # Lazy import to avoid circular deps.
        from backend.notes_store import append_question  # type: ignore

        return append_question(url, question)

    def append_turn(self, url: str, role: str, text: str) -> NotesRecord:
        # Lazy import to avoid circular deps.
        from backend.notes_store import append_turn  # type: ignore

        return append_turn(url, role, text)

    def append_qa(self, url: str, question: str, answer: str) -> NotesRecord:
        return append_qa(url, question, answer)

    def append_quiz(
        self, url: str, question: str, user_answer: str, correct_answer: str, explanation: str
    ) -> NotesRecord:
        return append_quiz(url, question, user_answer, correct_answer, explanation)

    def get(self, url: str) -> NotesRecord | None:
        return get_notes(url)


class PostgresNotesRepo:
    """
    Minimal Postgres storage for notes keyed by URL.
    Requires DATABASE_URL.
    """

    def __init__(self, database_url: str):
        self.database_url = database_url

    def _connect(self):
        # Import lazily so local dev can run without Postgres deps installed
        # (and only requires psycopg when DATABASE_URL is set).
        import psycopg  # type: ignore
        from psycopg.rows import dict_row  # type: ignore

        return psycopg.connect(self.database_url, row_factory=dict_row)

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS notes (
                      url TEXT PRIMARY KEY,
                      summary TEXT NOT NULL DEFAULT '',
                      questions JSONB NOT NULL DEFAULT '[]'::jsonb,
                      turns JSONB NOT NULL DEFAULT '[]'::jsonb,
                      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    """
                )
                # Back-compat for older deployments where the table existed without these columns.
                cur.execute("ALTER TABLE notes ADD COLUMN IF NOT EXISTS questions JSONB NOT NULL DEFAULT '[]'::jsonb;")
                cur.execute("ALTER TABLE notes ADD COLUMN IF NOT EXISTS turns JSONB NOT NULL DEFAULT '[]'::jsonb;")
                # We no longer store QA/quizzes in JSONB columns (moved to relational tables below).
                # Drop legacy columns if they exist to avoid type/default/constraint mismatches causing 500s.
                cur.execute("ALTER TABLE notes DROP COLUMN IF EXISTS qa;")
                cur.execute("ALTER TABLE notes DROP COLUMN IF EXISTS quizzes;")

                # Heal any legacy NULLs so jsonb concatenation never fails.
                cur.execute("UPDATE notes SET questions = '[]'::jsonb WHERE questions IS NULL;")
                cur.execute("UPDATE notes SET turns = '[]'::jsonb WHERE turns IS NULL;")
                cur.execute("UPDATE notes SET questions = '[]'::jsonb WHERE jsonb_typeof(questions) <> 'array';")
                cur.execute("UPDATE notes SET turns = '[]'::jsonb WHERE jsonb_typeof(turns) <> 'array';")

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS notes_qa (
                      id BIGSERIAL PRIMARY KEY,
                      url TEXT NOT NULL REFERENCES notes(url) ON DELETE CASCADE,
                      q TEXT NOT NULL,
                      a TEXT NOT NULL,
                      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_notes_qa_url ON notes_qa(url);")

                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS notes_quizzes (
                      id BIGSERIAL PRIMARY KEY,
                      url TEXT NOT NULL REFERENCES notes(url) ON DELETE CASCADE,
                      question TEXT NOT NULL,
                      user_answer TEXT NOT NULL DEFAULT '',
                      correct_answer TEXT NOT NULL DEFAULT '',
                      explanation TEXT NOT NULL DEFAULT '',
                      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_notes_quizzes_url ON notes_quizzes(url);")
            conn.commit()

    def _get_full_record(self, conn, url: str) -> NotesRecord | None:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT url, summary, questions, turns, updated_at FROM notes WHERE url = %s;",
                (url,),
            )
            row = cur.fetchone()
            if not row:
                return None

            cur.execute(
                "SELECT q, a FROM notes_qa WHERE url = %s ORDER BY id ASC;",
                (url,),
            )
            qa_rows = cur.fetchall() or []

            cur.execute(
                """
                SELECT question, user_answer, correct_answer, explanation
                  FROM notes_quizzes
                 WHERE url = %s
                 ORDER BY id ASC;
                """,
                (url,),
            )
            quiz_rows = cur.fetchall() or []

        rec = _row_to_record(row)
        rec.qa = [{"q": (r.get("q") or ""), "a": (r.get("a") or "")} for r in qa_rows]
        rec.quizzes = [
            {
                "question": (r.get("question") or ""),
                "userAnswer": (r.get("user_answer") or ""),
                "correctAnswer": (r.get("correct_answer") or ""),
                "explanation": (r.get("explanation") or ""),
            }
            for r in quiz_rows
        ]
        return rec

    def reset(self, url: str) -> NotesRecord:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO notes (url, summary, questions, turns, updated_at)
                    VALUES (%s, '', '[]'::jsonb, '[]'::jsonb, now())
                    ON CONFLICT (url) DO UPDATE
                      SET summary = EXCLUDED.summary,
                          questions = EXCLUDED.questions,
                          turns = EXCLUDED.turns,
                          updated_at = EXCLUDED.updated_at
                    RETURNING url;
                    """,
                    (url,),
                )
                cur.fetchone()

                cur.execute("DELETE FROM notes_qa WHERE url = %s;", (url,))
                cur.execute("DELETE FROM notes_quizzes WHERE url = %s;", (url,))
            conn.commit()
            rec = self._get_full_record(conn, url)
        if not rec:
            raise ValueError("Missing row")
        return rec

    def set_summary(self, url: str, summary: str) -> NotesRecord:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO notes (url, summary, questions, turns, updated_at)
                    VALUES (%s, %s, '[]'::jsonb, '[]'::jsonb, now())
                    ON CONFLICT (url) DO UPDATE
                      SET summary = EXCLUDED.summary,
                          updated_at = EXCLUDED.updated_at
                    RETURNING url;
                    """,
                    (url, summary.strip()),
                )
                cur.fetchone()
            conn.commit()
            rec = self._get_full_record(conn, url)
        if not rec:
            raise ValueError("Missing row")
        return rec

    def append_question(self, url: str, question: str) -> NotesRecord:
        q = (question or "").strip()
        if not q:
            raise ValueError("Missing question")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO notes (url, summary, questions, turns, updated_at)
                    VALUES (%s, '', '[]'::jsonb, '[]'::jsonb, now())
                    ON CONFLICT (url) DO NOTHING;
                    """,
                    (url,),
                )
                cur.execute(
                    """
                    UPDATE notes
                       SET questions = COALESCE(questions, '[]'::jsonb) || jsonb_build_array(%s::text),
                           updated_at = now()
                     WHERE url = %s
                    RETURNING url;
                    """,
                    (q, url),
                )
                cur.fetchone()
            conn.commit()
            rec = self._get_full_record(conn, url)
        if not rec:
            raise ValueError("Missing row")
        return rec

    def append_turn(self, url: str, role: str, text: str) -> NotesRecord:
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
                    INSERT INTO notes (url, summary, questions, turns, updated_at)
                    VALUES (%s, '', '[]'::jsonb, '[]'::jsonb, now())
                    ON CONFLICT (url) DO NOTHING;
                    """,
                    (url,),
                )
                cur.execute(
                    """
                    UPDATE notes
                       SET turns = COALESCE(turns, '[]'::jsonb) || jsonb_build_array(
                             jsonb_build_object('role', %s::text, 'text', %s::text)
                           ),
                           updated_at = now()
                     WHERE url = %s
                    RETURNING url;
                    """,
                    (r, t, url),
                )
                cur.fetchone()
            conn.commit()
            rec = self._get_full_record(conn, url)
        if not rec:
            raise ValueError("Missing row")
        return rec

    def append_qa(self, url: str, question: str, answer: str) -> NotesRecord:
        q = (question or "").strip()
        a = (answer or "").strip()
        if not q or not a:
            raise ValueError("Missing question/answer")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO notes (url, summary, questions, turns, updated_at)
                    VALUES (%s, '', '[]'::jsonb, '[]'::jsonb, now())
                    ON CONFLICT (url) DO NOTHING;
                    """,
                    (url,),
                )
                cur.execute(
                    "INSERT INTO notes_qa (url, q, a) VALUES (%s, %s, %s);",
                    (url, q, a),
                )
                cur.execute("UPDATE notes SET updated_at = now() WHERE url = %s;", (url,))
            conn.commit()
            rec = self._get_full_record(conn, url)
        if not rec:
            raise ValueError("Missing row")
        return rec

    def append_quiz(
        self, url: str, question: str, user_answer: str, correct_answer: str, explanation: str
    ) -> NotesRecord:
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
                    INSERT INTO notes (url, summary, questions, turns, updated_at)
                    VALUES (%s, '', '[]'::jsonb, '[]'::jsonb, now())
                    ON CONFLICT (url) DO NOTHING;
                    """,
                    (url,),
                )
                cur.execute(
                    """
                    INSERT INTO notes_quizzes (url, question, user_answer, correct_answer, explanation)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (url, q, ua, ca, ex),
                )
                cur.execute("UPDATE notes SET updated_at = now() WHERE url = %s;", (url,))
            conn.commit()
            rec = self._get_full_record(conn, url)
        if not rec:
            raise ValueError("Missing row")
        return rec

    def get(self, url: str) -> NotesRecord | None:
        with self._connect() as conn:
            rec = self._get_full_record(conn, url)
        return rec


def _row_to_record(row: dict | None) -> NotesRecord:
    if not row:
        raise ValueError("Missing row")
    rec = NotesRecord(url=row["url"])
    rec.summary = row.get("summary") or ""
    rec.questions = _coerce_json_list(row.get("questions"))
    rec.turns = _coerce_json_list(row.get("turns"))
    rec.qa = []
    rec.quizzes = []
    rec.updated_at = (row.get("updated_at") or "").isoformat() if hasattr(row.get("updated_at"), "isoformat") else str(row.get("updated_at"))
    return rec


def _coerce_json_list(value) -> list:
    """
    Psycopg JSONB typically comes back as Python objects, but can be returned as a JSON string
    depending on adapters / drivers. Normalize to a Python list for API serialization.
    """
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
    # Unknown type (e.g. a driver wrapper). Best-effort: try JSON serialization.
    try:
        parsed = json.loads(str(value))
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def make_notes_repo() -> NotesRepo:
    db_url = (os.environ.get("DATABASE_URL") or "").strip()
    if db_url:
        repo = PostgresNotesRepo(db_url)
        return repo
    return InMemoryNotesRepo()


