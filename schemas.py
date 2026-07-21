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
    BEHAVIORAL = "behavioral"


class QuestionType(str, Enum):
    """Specific question format type."""
    OPEN_ENDED = "open_ended"
    BEHAVIORAL = "behavioral"
    MCQ = "mcq"
    YES_NO = "yes_no"
    CODING = "coding"
    DEBUGGING = "debugging"
    SYSTEM_DESIGN = "system_design"


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
    """An interview question with an identifier, category, and metadata."""
    id: str
    text: str
    category: QuestionCategory
    question_type: QuestionType = QuestionType.OPEN_ENDED
    difficulty: str = ""
    expected_keywords: list[str] = []
    options: list[str] = []
    correct_answer: str | bool | None = None
    starter_code: str = ""
    language: str = ""
    evaluation_type: str = ""
    buggy_code: str = ""
    expected_fix: str = ""
    evaluation_focus: list[str] = []


class Evaluation(BaseModel):
    """Scores for a single answer across communication and technical dimensions."""
    clarity: int = Field(..., ge=1, le=10)
    completeness: int = Field(..., ge=1, le=10)
    relevance: int = Field(..., ge=1, le=10)
    grammar: int = Field(..., ge=1, le=10)
    impact: int = Field(..., ge=1, le=10)
    technical_depth: int = Field(..., ge=1, le=10)
    architecture_design: int = Field(..., ge=1, le=10)
    problem_solving: int = Field(..., ge=1, le=10)
    tradeoff_analysis: int = Field(..., ge=1, le=10)
    strengths: list[str]
    weaknesses: list[str]
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


class QuestionConfig(BaseModel):
    """Configuration for question generation — type distribution, count, and seniority targeting."""
    total_questions: int = 5
    distribution: dict[QuestionType, float] = Field(
        default_factory=lambda: {
            QuestionType.OPEN_ENDED: 0.60,
            QuestionType.BEHAVIORAL: 0.40,
        }
    )

    def counts(self) -> dict[QuestionType, int]:
        """Compute the actual number of questions per type based on distribution percentages."""
        raw = {qt: max(1, int(self.total_questions * pct)) for qt, pct in self.distribution.items()}
        total = sum(raw.values())
        diff = self.total_questions - total
        if diff > 0:
            for qt in raw:
                if diff <= 0:
                    break
                raw[qt] += 1
                diff -= 1
        elif diff < 0:
            for qt in list(raw.keys())[:-1]:
                if diff >= 0:
                    break
                reduction = min(raw[qt] - 1, -diff)
                raw[qt] -= reduction
                diff += reduction
        return raw


DEFAULT_QUESTION_CONFIG = QuestionConfig()


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
