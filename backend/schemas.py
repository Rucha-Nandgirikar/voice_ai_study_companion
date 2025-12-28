from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Difficulty(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class AnalyzePageRequest(BaseModel):
    sessionId: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    cleanedText: str = Field(..., min_length=1, description="Main educational content from the page")


class UrlAnalyzeRequest(BaseModel):
    sessionId: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1, description="Public URL to fetch and analyze server-side")


class Section(BaseModel):
    id: str
    title: str
    summary: str
    keyPoints: list[str]
    sourceExcerpt: str


class AnalyzePageResponse(BaseModel):
    summary: str
    topics: list[str]
    sections: list[Section]


class ConversationTurnRequest(BaseModel):
    sessionId: str = Field(..., min_length=1)
    userTranscript: str = Field(..., min_length=1)


class TutorAction(str, Enum):
    teach = "TEACH"
    summarize = "SUMMARIZE"
    quiz = "QUIZ"
    clarify = "CLARIFY"


class ConversationTurnResponse(BaseModel):
    action: TutorAction
    assistantText: str
    nextQuestion: str | None = None
    difficulty: Difficulty
    selectedSectionId: str | None = None


class ElevenLabsSignedUrlRequest(BaseModel):
    agentId: str = Field(..., min_length=1)


class ElevenLabsSignedUrlResponse(BaseModel):
    signedUrl: str


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


class ExtractChunkRequest(BaseModel):
    url: str = Field(..., min_length=1, description="Public URL to fetch and extract server-side")
    offset: int = Field(0, ge=0, description="Character offset into the extracted text")
    maxChars: int = Field(
        12000,
        ge=500,
        le=200_000,
        description="Maximum number of characters to return for this chunk",
    )


class ExtractChunkResponse(BaseModel):
    url: str
    offset: int
    chunk: str
    nextOffset: int | None = None
    totalChars: int | None = None


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
    url: str = Field(..., min_length=1)


class NotesSetSummaryRequest(BaseModel):
    url: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1, description="Session/page summary to store as notes")


class NotesAppendQuestionRequest(BaseModel):
    url: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1, description="A question asked during the call")


class NotesAppendTurnRequest(BaseModel):
    url: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1, description="Who said it: 'user' or 'agent'")
    text: str = Field(..., min_length=1, description="Utterance text to append to notes")


class NotesAppendQARequest(BaseModel):
    url: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1, description="User question (or tutor prompt) to store in notes")
    answer: str = Field(..., min_length=1, description="Tutor answer to store in notes")


class NotesAppendQuizRequest(BaseModel):
    url: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1, description="Quiz question/prompt")
    userAnswer: str = Field("", description="User answer (optionally polished)")
    correctAnswer: str = Field("", description="Correct answer")
    explanation: str = Field("", description="Short explanation / feedback")


class NotesGetResponse(BaseModel):
    url: str
    summary: str
    questions: list[str]
    turns: list[dict[str, str]] = Field(default_factory=list)
    qa: list[dict[str, str]] = Field(default_factory=list)
    quizzes: list[dict[str, str]] = Field(default_factory=list)
    updatedAt: str


class SessionItem(BaseModel):
    url: str
    updatedAt: str


class SessionsListResponse(BaseModel):
    sessions: list[SessionItem] = Field(default_factory=list)


class SessionTouchRequest(BaseModel):
    url: str = Field(..., min_length=1)


class SummarizeRequest(BaseModel):
    url: str = Field(..., min_length=1, description="Public URL to fetch/extract and summarize server-side")
    parts: int = Field(4, ge=2, le=12, description="Number of parts to split into (default 4)")
    maxCharsPerPart: int = Field(
        9000,
        ge=500,
        le=200_000,
        description="Hard limit for each part's character count (prevents oversized model inputs).",
    )


class SummarizeResponse(BaseModel):
    url: str
    summary: str
    model: str | None = None
    truncated: bool = False
    totalChars: int | None = None


class TopicsRequest(BaseModel):
    url: str = Field(..., min_length=1, description="Public URL to fetch and extract topic headings from")


class TopicItem(BaseModel):
    level: int = Field(..., ge=1, le=6, description="Heading level (1-6)")
    title: str = Field(..., min_length=1)


class TopicsResponse(BaseModel):
    url: str
    title: str | None = None
    topics: list[TopicItem] = Field(default_factory=list)



