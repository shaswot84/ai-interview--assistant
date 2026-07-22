"""Tests for Pydantic schema validation — field constraints, enums, and defaults."""

import pytest
from pydantic import ValidationError

from schemas import (
    Competency,
    Evaluation,
    LetterGrade,
    Question,
    Scorecard,
    Seniority,
    SessionState,
    UserProfile,
)


class TestUserProfile:
    """UserProfile field validation — role length, seniority enum."""

    def test_valid_profile(self):
        profile = UserProfile(
            role="Backend Engineer",
            seniority=Seniority.SENIOR,
            industry="FinTech",
            interview_type="technical",
        )
        assert profile.role == "Backend Engineer"

    def test_rejects_invalid_seniority_string(self):
        with pytest.raises(ValidationError):
            UserProfile(
                role="Engineer",
                seniority="king",
                industry="Tech",
                interview_type="technical",
            )

    def test_rejects_short_role(self):
        with pytest.raises(ValidationError):
            UserProfile(
                role="AB",
                seniority=Seniority.JUNIOR,
                industry="Tech",
                interview_type="technical",
            )


class TestQuestion:
    """Question should accept valid category values."""

    def test_valid_question(self):
        q = Question(
            id="q1", text="What is OOP?", category=Competency.ALGORITHMS
        )
        assert q.category == Competency.ALGORITHMS


class TestEvaluation:
    """Evaluation scores dict values must be in the 1–10 range."""

    def test_valid_evaluation(self):
        eval_ = Evaluation(
            scores={"clarity": 8, "correctness": 9},
            strengths=["S1", "S2", "S3"],
            weaknesses=["W1", "W2", "W3"],
            grammar_correction="Fixed grammar.",
            simplified_version="Simple version.",
            actionable_feedback="Be more specific.",
        )
        assert eval_.scores["clarity"] == 8
        assert eval_.scores["correctness"] == 9

    def test_rejects_score_below_1(self):
        with pytest.raises(ValidationError):
            Evaluation(
                scores={"clarity": 0, "correctness": 5},
                strengths=[], weaknesses=[],
                grammar_correction="x", simplified_version="y", actionable_feedback="z",
            )

    def test_rejects_score_above_10(self):
        with pytest.raises(ValidationError):
            Evaluation(
                scores={"clarity": 11, "correctness": 5},
                strengths=[], weaknesses=[],
                grammar_correction="x", simplified_version="y", actionable_feedback="z",
            )

    def test_rejects_any_dimension_out_of_bounds(self):
        base = {
            "strengths": [], "weaknesses": [],
            "grammar_correction": "x", "simplified_version": "y", "actionable_feedback": "z",
        }
        for val in (0, 11, -1, 100):
            with pytest.raises(ValidationError):
                Evaluation(scores={"dummy": val}, **base)


class TestScorecard:
    """Scorecard must use a valid LetterGrade enum value."""

    def test_valid_scorecard(self):
        sc = Scorecard(
            strengths=["Good communication"],
            improvements=["Be more concise"],
            model_answer="A good answer...",
            overall_assessment="Solid performance.",
            grade=LetterGrade.B,
        )
        assert sc.grade == LetterGrade.B

    def test_rejects_invalid_grade_string(self):
        with pytest.raises(ValidationError):
            Scorecard(
                strengths=[],
                improvements=[],
                model_answer="x",
                overall_assessment="y",
                grade="Z",
            )


class TestSessionState:
    """SessionState defaults and full construction."""

    def test_default_state_is_idle(self):
        state = SessionState()
        assert state.current_state.value == "IDLE"

    def test_can_set_full_state(self):
        profile = UserProfile(
            role="Dev", seniority=Seniority.MID, industry="Tech", interview_type="behavioural"
        )
        questions = [
            Question(id="q1", text="Q1?", category=Competency.API_DESIGN),
            Question(id="q2", text="Q2?", category=Competency.COMMUNICATION),
        ]
        state = SessionState(
            profile=profile,
            questions=questions,
            current_question_index=0,
        )
        assert state.profile is not None
        assert len(state.questions) == 2
