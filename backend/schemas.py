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


