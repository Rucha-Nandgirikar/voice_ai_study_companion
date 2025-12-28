from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractRequest(BaseModel):
    url: str = Field(..., min_length=1, description="Public URL to fetch and extract server-side")
    maxChars: int | None = Field(
        None,
        ge=500,
        le=200_000,
        description="Optional hard limit for returned cleanedText character count (prevents tool payloads from being too large).",
    )


class ExtractResponse(BaseModel):
    url: str
    cleanedText: str
    truncated: bool = False
    totalChars: int | None = None
    title: str | None = None


class ExtractPartsRequest(BaseModel):
    url: str = Field(..., min_length=1, description="Public URL to fetch and extract server-side")
    parts: int = Field(4, ge=2, le=12, description="Number of parts to split into (default 4)")
    maxCharsPerPart: int = Field(
        9000,
        ge=500,
        le=200_000,
        description="Hard limit for each part's character count (prevents oversized tool payloads).",
    )


class ExtractPart(BaseModel):
    index: int = Field(..., ge=1, description="1-based part index")
    totalParts: int = Field(..., ge=1, description="Total number of parts")
    offset: int = Field(..., ge=0, description="Character offset into the full extracted text")
    text: str


class ExtractPartsResponse(BaseModel):
    url: str
    title: str | None = None
    parts: list[ExtractPart]
    truncated: bool = False
    totalChars: int | None = None


class NotesResetRequest(BaseModel):
    sessionId: str = Field(..., min_length=1)


class NotesSetSummaryRequest(BaseModel):
    sessionId: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1, description="Session/page summary to store as notes")


class NotesAppendQuestionRequest(BaseModel):
    sessionId: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1, description="A question asked during the call")


class NotesAppendTurnRequest(BaseModel):
    sessionId: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1, description="Who said it: 'user' or 'agent'")
    text: str = Field(..., min_length=1, description="Utterance text to append to notes")


class NotesAppendQARequest(BaseModel):
    sessionId: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1, description="User question (or tutor prompt) to store in notes")
    answer: str = Field(..., min_length=1, description="Tutor answer to store in notes")


class NotesAppendQuizRequest(BaseModel):
    sessionId: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1, description="Quiz question/prompt")
    userAnswer: str = Field("", description="User answer (optionally polished)")
    correctAnswer: str = Field("", description="Correct answer")
    explanation: str = Field("", description="Short explanation / feedback")


class NotesGetResponse(BaseModel):
    sessionId: str
    url: str
    summary: str
    questions: list[str]
    turns: list[dict[str, str]] = Field(default_factory=list)
    qa: list[dict[str, str]] = Field(default_factory=list)
    quizzes: list[dict[str, str]] = Field(default_factory=list)
    updatedAt: str


class SessionItem(BaseModel):
    sessionId: str
    url: str
    selectedTopics: list[str] = Field(default_factory=list)
    completedTopics: list[str] = Field(default_factory=list)
    currentTopic: str = ""
    createdAt: str = ""
    updatedAt: str = ""


class SessionsListResponse(BaseModel):
    sessions: list[SessionItem] = Field(default_factory=list)


class SessionLatestResponse(BaseModel):
    session: SessionItem | None = None


class SessionStartRequest(BaseModel):
    url: str = Field(..., min_length=1)
    selectedTopics: list[str] = Field(default_factory=list, description="Up to 8 selected topic titles")


class TopicsRequest(BaseModel):
    url: str = Field(..., min_length=1, description="Public URL to fetch and extract topic headings from")


class TopicItem(BaseModel):
    level: int = Field(..., ge=1, le=6, description="Heading level (1-6)")
    title: str = Field(..., min_length=1)


class TopicsResponse(BaseModel):
    url: str
    title: str | None = None
    topics: list[TopicItem] = Field(default_factory=list)
