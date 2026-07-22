"""Pydantic v2 schemas — all data models used throughout the application."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Seniority(str, Enum):
    """Experience level of the candidate."""
    JUNIOR = "Junior"
    MID = "Mid"
    SENIOR = "Senior"
    LEAD = "Lead"


class InterviewerStyle(str, Enum):
    """Interviewer personality / style calibration."""
    FAANG = "faang"
    STARTUP = "startup"
    GAMING = "gaming"
    FINANCE = "finance"
    DEFAULT = "default"


class QuestionCategory(str, Enum):
    """Type of interview question. Kept for backward compatibility; use Competency for new questions."""
    TECHNICAL = "technical"
    BEHAVIOURAL = "behavioural"
    BEHAVIORAL = "behavioral"


class Competency(str, Enum):
    """Primary competency each question evaluates."""
    PROBLEM_SOLVING = "problem_solving"
    DEBUGGING = "debugging"
    ALGORITHMS = "algorithms"
    DATA_STRUCTURES = "data_structures"
    API_DESIGN = "api_design"
    DATABASES = "databases"
    CONCURRENCY = "concurrency"
    DISTRIBUTED_SYSTEMS = "distributed_systems"
    TESTING = "testing"
    SECURITY = "security"
    PERFORMANCE = "performance"
    COMMUNICATION = "communication"
    LEADERSHIP = "leadership"
    OWNERSHIP = "ownership"
    TRADEOFF_ANALYSIS = "tradeoff_analysis"
    SYSTEM_DESIGN = "system_design"
    OBSERVABILITY = "observability"
    MONITORING = "monitoring"
    RELIABILITY_ENGINEERING = "reliability_engineering"


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
    interviewer_style: InterviewerStyle = InterviewerStyle.DEFAULT


class Question(BaseModel):
    """An interview question with an identifier, category, and metadata."""
    id: str
    text: str
    category: Competency
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
    """Scores for a single answer — dynamic dimensions per question type."""
    scores: dict[str, int]
    score_reasons: dict[str, str] = Field(default_factory=dict)
    score_evidence: dict[str, str] = Field(default_factory=dict)
    hiring_decision: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    strengths: list[str]
    weaknesses: list[str]
    grammar_correction: str
    simplified_version: str
    actionable_feedback: str

    @field_validator("scores")
    @classmethod
    def validate_scores(cls, v: dict[str, int]) -> dict[str, int]:
        for key, val in v.items():
            if not isinstance(val, int) or val < 1 or val > 10:
                raise ValueError(f"Score for '{key}' must be 1-10, got {val}")
        return v


class Scorecard(BaseModel):
    """Final interview scorecard — LLM synthesis + deterministic stats."""
    # -- LLM-generated synthesis --
    overall_assessment: str                # 1-2 paragraphs, evidence-backed
    hiring_recommendation: str             # Strong Hire / Hire / Lean Hire / Lean No Hire / No Hire / Strong No Hire
    candidate_readiness: str               # e.g. "Close to Senior level" with why
    strongest_competencies: list[dict]     # [{"competency": "...", "why": "..."}, ...] — top 3
    weakest_competencies: list[dict]       # [{"competency": "...", "why": "..."}, ...] — bottom 3
    recurring_patterns: list[str]          # themes that appeared across ≥ 2 questions
    key_concepts_missed: list[str]         # important concepts repeatedly absent
    learning_roadmap: list[dict]           # [{"priority": 1, "area": "...", "reason": "...", "study": "..."}, ...]
    learning_resources: list[dict]         # [{"name": "...", "description": "...", "url": "..."}, ...]

    # -- Deterministic (computed in Python, not by LLM) --
    overall_score: float                   # from calculate_overall_score()
    grade: LetterGrade                     # from get_letter_grade()
    question_table: list[dict]             # from compute_question_table()
    dimension_averages: dict[str, float]   # from prepare_radar_chart_data()
    stats: dict                            # from compute_interview_stats()
    radar_interpretation: str              # from interpret_radar_chart()
    confidence_notice: str                 # from compute_confidence_notice()


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
        """Allocate exactly total_questions across types proportional to the distribution.

        Uses the largest-remainder (Hamilton) method so the counts sum to
        total_questions while honouring the requested percentages. Types whose
        share rounds down to zero are dropped entirely (a type set to 0% yields
        no questions).
        """
        total = self.total_questions
        pct_sum = sum(self.distribution.values())
        if total <= 0 or pct_sum <= 0:
            return {}

        exact = {qt: total * (pct / pct_sum) for qt, pct in self.distribution.items()}
        floored = {qt: int(v) for qt, v in exact.items()}
        remaining = total - sum(floored.values())

        # Hand out any leftover questions to the largest fractional remainders.
        by_remainder = sorted(
            exact, key=lambda qt: exact[qt] - floored[qt], reverse=True
        )
        for qt in by_remainder:
            if remaining <= 0:
                break
            floored[qt] += 1
            remaining -= 1

        return {qt: c for qt, c in floored.items() if c > 0}


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
