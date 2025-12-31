# Database Schema - What Gets Stored

The application uses PostgreSQL with the following tables:

## 1. `study_sessions` Table

**Purpose:** Stores session metadata and progress tracking

**Columns:**
- `session_id` (TEXT, PRIMARY KEY) - Unique session identifier (e.g., "sess_abc123...")
- `url` (TEXT, NOT NULL) - The URL being studied in this session
- `selected_topics` (JSONB, DEFAULT '[]') - **Topics the user selected for THIS session** (fresh selection each time)
- `completed_topics` (JSONB, DEFAULT '[]') - **Topics marked as completed** (aggregated across sessions for progress tracking)
- `current_topic` (TEXT, DEFAULT '') - Currently active topic being studied
- `created_at` (TIMESTAMPTZ) - When the session was created
- `updated_at` (TIMESTAMPTZ) - Last time the session was updated

**When data is stored:**
- `POST /sessions/start` → Creates new session with:
  - Fresh `selected_topics` from user's UI selection
  - `completed_topics` copied from latest session for that URL (if exists)
- `POST /sessions/progress/mark_topic_done` → Adds topic to `completed_topics`
- `POST /sessions/progress/set_current_topic` → Updates `current_topic`
- `updated_at` is updated whenever notes are modified

---

## 2. `session_notes` Table

**Purpose:** Stores session summary and raw transcript data

**Columns:**
- `session_id` (TEXT, PRIMARY KEY, FK to study_sessions) - Links to session
- `url` (TEXT, NOT NULL) - URL for this session (duplicated for convenience)
- `summary` (TEXT, DEFAULT '') - Summary text saved by agent
- `questions` (JSONB, DEFAULT '[]') - Array of question strings (legacy, may be empty)
- `turns` (JSONB, DEFAULT '[]') - Array of transcript turns: `[{role: "user"|"agent", text: "..."}]`
- `updated_at` (TIMESTAMPTZ) - Last update timestamp

**When data is stored:**
- `POST /sessions/start` → Creates empty notes record
- `POST /notes/set_summary` → Updates `summary`
- `POST /notes/append_turn` → Appends to `turns` array
- `POST /notes/reset` → Clears summary, questions, turns

---

## 3. `session_qa` Table

**Purpose:** Stores Q&A pairs (user questions + tutor answers)

**Columns:**
- `id` (BIGSERIAL, PRIMARY KEY) - Auto-incrementing ID
- `session_id` (TEXT, FK to study_sessions, CASCADE DELETE) - Links to session
- `q` (TEXT, NOT NULL) - Question text
- `a` (TEXT, NOT NULL) - Answer text
- `created_at` (TIMESTAMPTZ) - When the Q&A was saved

**When data is stored:**
- `POST /notes/append_qa` → Inserts new Q&A pair
- `POST /notes/reset` → Deletes all Q&A for the session

---

## 4. `session_quizzes` Table

**Purpose:** Stores quiz interactions with feedback

**Columns:**
- `id` (BIGSERIAL, PRIMARY KEY) - Auto-incrementing ID
- `session_id` (TEXT, FK to study_sessions, CASCADE DELETE) - Links to session
- `question` (TEXT, NOT NULL) - Quiz question/prompt
- `user_answer` (TEXT, DEFAULT '') - User's answer
- `correct_answer` (TEXT, DEFAULT '') - Correct answer
- `explanation` (TEXT, DEFAULT '') - Explanation/feedback
- `created_at` (TIMESTAMPTZ) - When the quiz was saved

**When data is stored:**
- `POST /notes/append_quiz` → Inserts new quiz record
- `POST /notes/reset` → Deletes all quizzes for the session

---

## Data Flow Summary

### When a new session starts:
1. **study_sessions**: Creates new row with:
   - Fresh `selected_topics` from user's selection
   - `completed_topics` copied from previous session (if exists)
   - New `session_id`

2. **session_notes**: Creates empty row linked to the session

### During a call:
- **session_qa**: Agent calls `append_qa` → new rows inserted
- **session_quizzes**: Agent calls `append_quiz` → new rows inserted
- **session_notes**: Agent calls `set_summary` or `append_turn` → updates row
- **study_sessions**: Agent calls `mark_topic_done` or `set_current_topic` → updates row

### What is NOT stored:
- Raw page content (fetched on-demand via `/extract`)
- Topic list from page (fetched on-demand via `/topics`)
- User authentication/login info
- Call audio/transcripts (only Q&A and quiz data)

### Relationships:
- All tables link to `study_sessions` via `session_id`
- CASCADE DELETE: Deleting a session deletes all related notes, Q&A, and quizzes
- Sessions can have multiple Q&A pairs and quizzes (1-to-many relationship)

