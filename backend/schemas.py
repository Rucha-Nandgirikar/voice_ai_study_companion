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


class ExtractResponse(BaseModel):
    url: str
    cleanedText: str


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



