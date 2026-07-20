"""Tests for the session state machine — valid/invalid transitions and timer auto-skip."""

from datetime import datetime, timedelta, timezone

import pytest

from schemas import (
    InterviewState,
    Question,
    QuestionCategory,
    Seniority,
    SessionState,
    UserProfile,
)
from session_state import InvalidTransitionError, transition


def _state_with_questions(n: int = 3, state: InterviewState = InterviewState.IDLE) -> SessionState:
    """Helper — build a SessionState with n questions at the given state."""
    questions = [
        Question(id=f"q{i}", text=f"Question {i}?", category=QuestionCategory.TECHNICAL)
        for i in range(n)
    ]
    profile = UserProfile(
        role="Engineer",
        seniority=Seniority.MID,
        industry="Tech",
        interview_type="technical",
    )
    return SessionState(
        current_state=state,
        profile=profile,
        questions=questions,
        current_question_index=0,
    )


class TestInvalidTransition:
    """Actions that should not be allowed from the current state."""

    def test_raises_on_illegal_action(self):
        state = SessionState(current_state=InterviewState.IDLE)
        with pytest.raises(InvalidTransitionError):
            transition(state, "submit_answer")

    def test_raises_on_unknown_action(self):
        state = SessionState(current_state=InterviewState.IDLE)
        with pytest.raises(InvalidTransitionError):
            transition(state, "nonexistent")


class TestValidTransitions:
    """Every allowed state → action pair must produce the expected next state."""

    def test_idle_to_onboarding(self):
        state = SessionState(current_state=InterviewState.IDLE)
        result = transition(state, "start")
        assert result.current_state == InterviewState.ONBOARDING

    def test_onboarding_to_generating(self):
        state = SessionState(current_state=InterviewState.ONBOARDING)
        result = transition(state, "submit_profile")
        assert result.current_state == InterviewState.GENERATING

    def test_generating_to_interviewing(self):
        state = SessionState(current_state=InterviewState.GENERATING)
        result = transition(state, "questions_ready")
        assert result.current_state == InterviewState.INTERVIEWING

    def test_interviewing_to_evaluating(self):
        state = _state_with_questions(state=InterviewState.INTERVIEWING)
        result = transition(state, "submit_answer")
        assert result.current_state == InterviewState.EVALUATING

    def test_interviewing_skip_to_evaluating(self):
        state = _state_with_questions(state=InterviewState.INTERVIEWING)
        result = transition(state, "skip")
        assert result.current_state == InterviewState.EVALUATING

    def test_evaluating_to_feedback(self):
        state = SessionState(current_state=InterviewState.EVALUATING)
        result = transition(state, "evaluation_done")
        assert result.current_state == InterviewState.FEEDBACK

    def test_feedback_next_question_to_interviewing(self):
        state = _state_with_questions(state=InterviewState.FEEDBACK)
        result = transition(state, "next_question")
        assert result.current_state == InterviewState.INTERVIEWING

    def test_feedback_finish_to_completed(self):
        state = _state_with_questions(state=InterviewState.FEEDBACK)
        result = transition(state, "finish")
        assert result.current_state == InterviewState.COMPLETED

    def test_interviewing_end_early_to_completed(self):
        state = _state_with_questions(state=InterviewState.INTERVIEWING)
        result = transition(state, "end_early")
        assert result.current_state == InterviewState.COMPLETED

    def test_feedback_end_early_to_completed(self):
        state = _state_with_questions(state=InterviewState.FEEDBACK)
        result = transition(state, "end_early")
        assert result.current_state == InterviewState.COMPLETED

    def test_completed_to_debrief(self):
        state = SessionState(current_state=InterviewState.COMPLETED)
        result = transition(state, "show_debrief")
        assert result.current_state == InterviewState.DEBRIEF


class TestTimerAutoSkip:
    """submit_answer should auto-convert to timeout_skip when the timer has expired."""

    def test_auto_skip_when_timed_out(self):
        limit = 180
        state = _state_with_questions(state=InterviewState.INTERVIEWING)
        state.question_started_at = datetime.now(timezone.utc) - timedelta(seconds=limit + 5)
        result = transition(state, "submit_answer")
        assert result.current_state == InterviewState.EVALUATING

    def test_within_limit_passthrough(self):
        state = _state_with_questions(state=InterviewState.INTERVIEWING)
        state.question_started_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        result = transition(state, "submit_answer")
        assert result.current_state == InterviewState.EVALUATING


class TestQuestionIndexManagement:
    """Verify that next_question resets the timer."""

    def test_next_question_sets_timer(self):
        state = _state_with_questions(state=InterviewState.FEEDBACK)
        state.question_started_at = None
        result = transition(state, "next_question")
        assert result.current_state == InterviewState.INTERVIEWING
        assert result.question_started_at is not None
