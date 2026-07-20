"""Pydantic v2 schemas — all data models used throughout the application."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Seniority(str, Enum):
    """Experience level of the candidate."""
    JUNIOR = "Junior"
    MID = "Mid"
    SENIOR = "Senior"
    LEAD = "Lead"


class QuestionCategory(str, Enum):
    """Type of interview question."""
    TECHNICAL = "technical"
    BEHAVIOURAL = "behavioural"


class InterviewState(str, Enum):
    """All possible states in the interview state machine."""
    IDLE = "IDLE"
    ONBOARDING = "ONBOARDING"
    GENERATING = "GENERATING"
    INTERVIEWING = "INTERVIEWING"
    EVALUATING = "EVALUATING"
    FEEDBACK = "FEEDBACK"
    COMPLETED = "COMPLETED"
    DEBRIEF = "DEBRIEF"


class LetterGrade(str, Enum):
    """Final grade letters."""
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class UserProfile(BaseModel):
    """Candidate profile assembled during onboarding."""
    role: str = Field(..., min_length=3)
    seniority: Seniority
    industry: str
    interview_type: str


class Question(BaseModel):
    """An interview question with an identifier and category."""
    id: str
    text: str
    category: QuestionCategory


class Evaluation(BaseModel):
    """Scores for a single answer across five dimensions."""
    clarity: int = Field(..., ge=1, le=10)
    completeness: int = Field(..., ge=1, le=10)
    relevance: int = Field(..., ge=1, le=10)
    grammar: int = Field(..., ge=1, le=10)
    impact: int = Field(..., ge=1, le=10)
    grammar_correction: str
    simplified_version: str
    actionable_feedback: str


class Scorecard(BaseModel):
    """Final interview scorecard with strengths, improvements, and grade."""
    strengths: list[str]
    improvements: list[str]
    model_answer: str
    overall_assessment: str
    grade: LetterGrade


class SessionState(BaseModel):
    """Complete session state — profile, questions, answers, evaluations, and machine state."""
    current_state: InterviewState = InterviewState.IDLE
    profile: Optional[UserProfile] = None
    questions: list[Question] = []
    current_question_index: int = 0
    transcript: dict[str, Optional[str]] = {}
    evaluations: dict[str, Evaluation] = {}
    scorecard: Optional[Scorecard] = None
    question_started_at: Optional[datetime] = None
