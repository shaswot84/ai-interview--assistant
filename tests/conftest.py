"""Shared pytest fixtures for use across all test modules."""

import pytest

from schemas import (
    Competency,
    Evaluation,
    Question,
    Seniority,
    SessionState,
    UserProfile,
)


@pytest.fixture
def sample_profile() -> UserProfile:
    """A standard UserProfile (Senior Backend Engineer in FinTech)."""
    return UserProfile(
        role="Backend Engineer",
        seniority=Seniority.SENIOR,
        industry="FinTech",
        interview_type="technical",
    )


@pytest.fixture
def sample_questions() -> list[Question]:
    """Five sample questions (3 technical, 2 behavioural), each with a distinct competency."""
    return [
        Question(id="q1", text="What is REST?", category=Competency.API_DESIGN),
        Question(id="q2", text="Explain ACID.", category=Competency.DATABASES),
        Question(id="q3", text="What is Docker?", category=Competency.PROBLEM_SOLVING),
        Question(id="q4", text="Tell me about a conflict.", category=Competency.COMMUNICATION),
        Question(id="q5", text="How do you prioritise?", category=Competency.OWNERSHIP),
    ]


@pytest.fixture
def sample_evaluation() -> Evaluation:
    """A mid-range Evaluation fixture."""
    return Evaluation(
        clarity=8,
        completeness=7,
        relevance=9,
        grammar=6,
        impact=8,
        technical_depth=7,
        architecture_design=6,
        problem_solving=8,
        tradeoff_analysis=6,
        strengths=["Clear communication", "Good structure", "Relevant examples"],
        weaknesses=["Needs more depth", "Missing trade-offs", "Grammar issues"],
        grammar_correction="Fixed grammar.",
        simplified_version="Simpler version.",
        actionable_feedback="Be more specific.",
    )


@pytest.fixture
def sample_state(sample_profile, sample_questions) -> SessionState:
    """A fully populated SessionState with profile, questions, and partial transcript."""
    return SessionState(
        profile=sample_profile,
        questions=sample_questions,
        transcript={
            "q1": "REST is an architectural style.",
            "q2": "ACID stands for Atomicity, Consistency, Isolation, Durability.",
            "q3": None,
            "q4": "I resolved a conflict by listening.",
            "q5": None,
        },
    )
