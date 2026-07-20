"""Performance benchmarks — latency targets for LLM calls (requires API key)."""

import os
import time

import pytest
from dotenv import load_dotenv

load_dotenv()


def _key_is_placeholder(key: str | None) -> bool:
    """Return True if the API key is missing or set to a placeholder value."""
    if not key:
        return True
    key = key.strip()
    if key in ("", "sk-...", "gsk-...", "OPENAI_API_KEY"):
        return True
    return False


HAS_KEY = not _key_is_placeholder(os.getenv("OPENAI_API_KEY"))

pytestmark = pytest.mark.skipif(not HAS_KEY, reason="OpenAI API key not configured")


@pytest.fixture
def profile():
    """Standard profile for performance tests."""
    from schemas import Seniority, UserProfile
    return UserProfile(
        role="Backend Engineer",
        seniority=Seniority.SENIOR,
        industry="FinTech",
        interview_type="technical",
    )


@pytest.fixture
def sample_questions():
    """Five sample questions for evaluation/scorecard benchmarks."""
    from schemas import Question, QuestionCategory
    return [
        Question(id="q1", text="What is REST?", category=QuestionCategory.TECHNICAL),
        Question(id="q2", text="Explain ACID properties.", category=QuestionCategory.TECHNICAL),
        Question(id="q3", text="What is Docker?", category=QuestionCategory.TECHNICAL),
        Question(id="q4", text="Tell me about a conflict.", category=QuestionCategory.BEHAVIOURAL),
        Question(id="q5", text="How do you prioritise?", category=QuestionCategory.BEHAVIOURAL),
    ]


@pytest.mark.slow
def test_question_generation_latency(profile):
    """Question generation should complete in under 3 seconds."""
    from llm_client import generate_questions
    start = time.time()
    questions = generate_questions(profile)
    elapsed = time.time() - start
    assert elapsed < 3.0, f"Question generation took {elapsed:.2f}s (limit 3s)"
    assert len(questions) == 5


@pytest.mark.slow
def test_answer_evaluation_latency(profile, sample_questions):
    """Answer evaluation should complete in under 3 seconds."""
    from llm_client import evaluate_answer
    answer = "REST is an architectural style that uses HTTP methods for CRUD operations on resources."
    start = time.time()
    eval_ = evaluate_answer(sample_questions[0], answer, profile)
    elapsed = time.time() - start
    assert elapsed < 3.0, f"Answer evaluation took {elapsed:.2f}s (limit 3s)"
    assert eval_.clarity >= 1


@pytest.mark.slow
def test_scorecard_synthesis_latency(profile, sample_questions):
    """Scorecard synthesis should complete in under 3 seconds."""
    from llm_client import synthesize_scorecard
    from schemas import SessionState, Evaluation
    state = SessionState(profile=profile, questions=sample_questions)
    state.transcript = {q.id: "A sample answer." for q in sample_questions}
    state.evaluations = {
        q.id: Evaluation(
            clarity=7, completeness=7, relevance=7, grammar=7, impact=7,
            technical_depth=7, architecture_design=7, problem_solving=7, tradeoff_analysis=7,
            strengths=[], weaknesses=[],
            grammar_correction="", simplified_version="", actionable_feedback="",
        ) for q in sample_questions
    }
    start = time.time()
    sc = synthesize_scorecard(state)
    elapsed = time.time() - start
    assert elapsed < 3.0, f"Scorecard synthesis took {elapsed:.2f}s (limit 3s)"
    assert sc.grade is not None
