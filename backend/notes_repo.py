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
                      qa JSONB NOT NULL DEFAULT '[]'::jsonb,
                      quizzes JSONB NOT NULL DEFAULT '[]'::jsonb,
                      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    """
                )
                # Back-compat for older deployments where the table existed without these columns.
                cur.execute("ALTER TABLE notes ADD COLUMN IF NOT EXISTS questions JSONB NOT NULL DEFAULT '[]'::jsonb;")
                cur.execute("ALTER TABLE notes ADD COLUMN IF NOT EXISTS turns JSONB NOT NULL DEFAULT '[]'::jsonb;")
                cur.execute("ALTER TABLE notes ADD COLUMN IF NOT EXISTS qa JSONB NOT NULL DEFAULT '[]'::jsonb;")
                cur.execute("ALTER TABLE notes ADD COLUMN IF NOT EXISTS quizzes JSONB NOT NULL DEFAULT '[]'::jsonb;")

                # If any of these columns exist with the wrong type (e.g. json/text), coerce to jsonb.
                # This avoids runtime 500s when we do jsonb concatenation (||) in append endpoints.
                cur.execute(
                    """
                    DO $$
                    BEGIN
                      IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                         WHERE table_schema = 'public' AND table_name = 'notes'
                           AND column_name = 'questions' AND udt_name <> 'jsonb'
                      ) THEN
                        ALTER TABLE notes
                          ALTER COLUMN questions TYPE jsonb
                          USING (
                            CASE
                              WHEN questions IS NULL THEN '[]'::jsonb
                              WHEN pg_typeof(questions)::text = 'jsonb' THEN questions
                              WHEN pg_typeof(questions)::text = 'json' THEN questions::jsonb
                              WHEN pg_typeof(questions)::text IN ('text', 'character varying') THEN
                                CASE WHEN btrim(questions) = '' THEN '[]'::jsonb ELSE questions::jsonb END
                              ELSE to_jsonb(questions)
                            END
                          );
                      END IF;

                      IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                         WHERE table_schema = 'public' AND table_name = 'notes'
                           AND column_name = 'turns' AND udt_name <> 'jsonb'
                      ) THEN
                        ALTER TABLE notes
                          ALTER COLUMN turns TYPE jsonb
                          USING (
                            CASE
                              WHEN turns IS NULL THEN '[]'::jsonb
                              WHEN pg_typeof(turns)::text = 'jsonb' THEN turns
                              WHEN pg_typeof(turns)::text = 'json' THEN turns::jsonb
                              WHEN pg_typeof(turns)::text IN ('text', 'character varying') THEN
                                CASE WHEN btrim(turns) = '' THEN '[]'::jsonb ELSE turns::jsonb END
                              ELSE to_jsonb(turns)
                            END
                          );
                      END IF;

                      IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                         WHERE table_schema = 'public' AND table_name = 'notes'
                           AND column_name = 'qa' AND udt_name <> 'jsonb'
                      ) THEN
                        ALTER TABLE notes
                          ALTER COLUMN qa TYPE jsonb
                          USING (
                            CASE
                              WHEN qa IS NULL THEN '[]'::jsonb
                              WHEN pg_typeof(qa)::text = 'jsonb' THEN qa
                              WHEN pg_typeof(qa)::text = 'json' THEN qa::jsonb
                              WHEN pg_typeof(qa)::text IN ('text', 'character varying') THEN
                                CASE WHEN btrim(qa) = '' THEN '[]'::jsonb ELSE qa::jsonb END
                              ELSE to_jsonb(qa)
                            END
                          );
                      END IF;

                      IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                         WHERE table_schema = 'public' AND table_name = 'notes'
                           AND column_name = 'quizzes' AND udt_name <> 'jsonb'
                      ) THEN
                        ALTER TABLE notes
                          ALTER COLUMN quizzes TYPE jsonb
                          USING (
                            CASE
                              WHEN quizzes IS NULL THEN '[]'::jsonb
                              WHEN pg_typeof(quizzes)::text = 'jsonb' THEN quizzes
                              WHEN pg_typeof(quizzes)::text = 'json' THEN quizzes::jsonb
                              WHEN pg_typeof(quizzes)::text IN ('text', 'character varying') THEN
                                CASE WHEN btrim(quizzes) = '' THEN '[]'::jsonb ELSE quizzes::jsonb END
                              ELSE to_jsonb(quizzes)
                            END
                          );
                      END IF;
                    END $$;
                    """
                )

                # Heal any legacy NULLs so jsonb concatenation never fails.
                cur.execute("UPDATE notes SET questions = '[]'::jsonb WHERE questions IS NULL;")
                cur.execute("UPDATE notes SET turns = '[]'::jsonb WHERE turns IS NULL;")
                cur.execute("UPDATE notes SET qa = '[]'::jsonb WHERE qa IS NULL;")
                cur.execute("UPDATE notes SET quizzes = '[]'::jsonb WHERE quizzes IS NULL;")

                # Also heal wrong JSON shapes (e.g. '{}' instead of '[]') for array-based columns.
                cur.execute("UPDATE notes SET questions = '[]'::jsonb WHERE jsonb_typeof(questions) <> 'array';")
                cur.execute("UPDATE notes SET turns = '[]'::jsonb WHERE jsonb_typeof(turns) <> 'array';")
                cur.execute("UPDATE notes SET qa = '[]'::jsonb WHERE jsonb_typeof(qa) <> 'array';")
                cur.execute("UPDATE notes SET quizzes = '[]'::jsonb WHERE jsonb_typeof(quizzes) <> 'array';")
            conn.commit()

    def reset(self, url: str) -> NotesRecord:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO notes (url, summary, questions, turns, qa, quizzes, updated_at)
                    VALUES (%s, '', '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, now())
                    ON CONFLICT (url) DO UPDATE
                      SET summary = EXCLUDED.summary,
                          questions = EXCLUDED.questions,
                          turns = EXCLUDED.turns,
                          qa = EXCLUDED.qa,
                          quizzes = EXCLUDED.quizzes,
                          updated_at = EXCLUDED.updated_at
                    RETURNING url, summary, questions, turns, qa, quizzes, updated_at;
                    """,
                    (url,),
                )
                row = cur.fetchone()
            conn.commit()
        return _row_to_record(row)

    def set_summary(self, url: str, summary: str) -> NotesRecord:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO notes (url, summary, questions, turns, qa, quizzes, updated_at)
                    VALUES (%s, %s, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, now())
                    ON CONFLICT (url) DO UPDATE
                      SET summary = EXCLUDED.summary,
                          updated_at = EXCLUDED.updated_at
                    RETURNING url, summary, questions, turns, qa, quizzes, updated_at;
                    """,
                    (url, summary.strip()),
                )
                row = cur.fetchone()
            conn.commit()
        return _row_to_record(row)

    def append_question(self, url: str, question: str) -> NotesRecord:
        q = (question or "").strip()
        if not q:
            raise ValueError("Missing question")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO notes (url, summary, questions, turns, qa, quizzes, updated_at)
                    VALUES (%s, '', '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, now())
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
                    RETURNING url, summary, questions, turns, qa, quizzes, updated_at;
                    """,
                    (q, url),
                )
                row = cur.fetchone()
            conn.commit()
        return _row_to_record(row)

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
                    INSERT INTO notes (url, summary, questions, turns, qa, quizzes, updated_at)
                    VALUES (%s, '', '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, now())
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
                    RETURNING url, summary, questions, turns, qa, quizzes, updated_at;
                    """,
                    (r, t, url),
                )
                row = cur.fetchone()
            conn.commit()
        return _row_to_record(row)

    def append_qa(self, url: str, question: str, answer: str) -> NotesRecord:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO notes (url, summary, questions, turns, qa, quizzes, updated_at)
                    VALUES (%s, '', '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, now())
                    ON CONFLICT (url) DO NOTHING;
                    """,
                    (url,),
                )
                cur.execute(
                    """
                    UPDATE notes
                       SET qa = (
                             CASE
                               WHEN qa IS NULL OR jsonb_typeof(qa) <> 'array' THEN '[]'::jsonb
                               ELSE qa
                             END
                           ) || jsonb_build_array(
                             jsonb_build_object('q', %s::text, 'a', %s::text)
                           ),
                           updated_at = now()
                     WHERE url = %s
                    RETURNING url, summary, questions, turns, qa, quizzes, updated_at;
                    """,
                    (question.strip(), answer.strip(), url),
                )
                row = cur.fetchone()
            conn.commit()
        return _row_to_record(row)

    def append_quiz(
        self, url: str, question: str, user_answer: str, correct_answer: str, explanation: str
    ) -> NotesRecord:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO notes (url, summary, questions, turns, qa, quizzes, updated_at)
                    VALUES (%s, '', '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, now())
                    ON CONFLICT (url) DO NOTHING;
                    """,
                    (url,),
                )
                cur.execute(
                    """
                    UPDATE notes
                       SET quizzes = (
                             CASE
                               WHEN quizzes IS NULL OR jsonb_typeof(quizzes) <> 'array' THEN '[]'::jsonb
                               ELSE quizzes
                             END
                           ) || jsonb_build_array(
                             jsonb_build_object(
                               'question', %s::text,
                               'userAnswer', %s::text,
                               'correctAnswer', %s::text,
                               'explanation', %s::text
                             )
                           ),
                           updated_at = now()
                     WHERE url = %s
                    RETURNING url, summary, questions, turns, qa, quizzes, updated_at;
                    """,
                    (
                        question.strip(),
                        (user_answer or "").strip(),
                        (correct_answer or "").strip(),
                        (explanation or "").strip(),
                        url,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return _row_to_record(row)

    def get(self, url: str) -> NotesRecord | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT url, summary, questions, turns, qa, quizzes, updated_at FROM notes WHERE url = %s;",
                    (url,),
                )
                row = cur.fetchone()
        return _row_to_record(row) if row else None


def _row_to_record(row: dict | None) -> NotesRecord:
    if not row:
        raise ValueError("Missing row")
    rec = NotesRecord(url=row["url"])
    rec.summary = row.get("summary") or ""
    rec.questions = _coerce_json_list(row.get("questions"))
    rec.turns = _coerce_json_list(row.get("turns"))
    rec.qa = _coerce_json_list(row.get("qa"))
    rec.quizzes = _coerce_json_list(row.get("quizzes"))
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


