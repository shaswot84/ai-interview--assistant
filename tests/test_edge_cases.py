"""Edge-case tests — injection resistance, score clamping, retry exhaustion, fallback, isolation."""

from unittest.mock import MagicMock, patch

import httpx
import pytest
from openai import APIError, RateLimitError

from llm_client import (
    _EvaluationResponse,
    QuestionsResponse,
    _call_with_retry,
    evaluate_answer,
    generate_questions,
    synthesize_scorecard,
)
from schemas import (
    Competency,
    Evaluation,
    InterviewState,
    LetterGrade,
    Question,
    QuestionType,
    Seniority,
    SessionState,
    UserProfile,
)
from scoring import calculate_overall_score, get_letter_grade


A_PROFILE = UserProfile(
    role="Engineer",
    seniority=Seniority.MID,
    industry="Tech",
    interview_type="technical",
)

A_QUESTION = Question(id="q1", text="Test?", category=Competency.ALGORITHMS)


def _mock_chat_completion(content: str | None):
    """Return a mock OpenAI chat completion (content may be None)."""
    mock_message = MagicMock()
    mock_message.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


class TestInjectionResistance:
    """Verify score clamping and injection-guard presence in the evaluation prompt."""

    @patch("llm_client._call_with_retry")
    def test_out_of_range_scores_are_clamped(self, mock_call):
        mock_call.return_value = _EvaluationResponse(
            strengths=[], weaknesses=[],
            grammar_correction="", simplified_version="", actionable_feedback="",
            clarity=100, completeness=-5, relevance=999,
            correctness=50, problem_solving=200, tradeoff_analysis=0,
        )
        result = evaluate_answer(A_QUESTION, "malicious answer", A_PROFILE)
        assert result.scores["clarity"] == 10
        assert result.scores["completeness"] == 1
        assert result.scores["relevance"] == 10
        assert result.scores["correctness"] == 10
        assert result.scores["problem_solving"] == 10
        assert result.scores["tradeoff_analysis"] == 1

    def test_injection_guard_placeholder_in_prompt(self):
        from prompts import EVALUATION_PROMPT
        assert "{injection_guard}" in EVALUATION_PROMPT

    @patch("llm_client._call_with_retry")
    def test_legitimate_scores_unchanged(self, mock_call):
        mock_call.return_value = _EvaluationResponse(
            strengths=["A", "B", "C"], weaknesses=["D", "E", "F"],
            grammar_correction="x", simplified_version="y", actionable_feedback="z",
            clarity=3, completeness=4, relevance=5,
            correctness=8, problem_solving=9, tradeoff_analysis=4,
        )
        result = evaluate_answer(A_QUESTION, "good answer", A_PROFILE)
        assert result.scores["clarity"] == 3
        assert result.scores["completeness"] == 4
        assert result.scores["relevance"] == 5
        assert result.scores["correctness"] == 8
        assert result.scores["problem_solving"] == 9
        assert result.scores["tradeoff_analysis"] == 4


class TestMalformedJSON:
    """Malformed or null LLM responses should trigger retries then raise."""

    @patch("llm_client.get_openai_client")
    def test_malformed_json_retries_then_fails(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_chat_completion(
            "not valid json"
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(RuntimeError, match="LLM call failed after 2 retries"):
            _call_with_retry(
                messages=[{"role": "user", "content": "hi"}],
                response_model=QuestionsResponse,
                max_retries=2,
            )

    @patch("llm_client.get_openai_client")
    def test_null_content_retries_then_fails(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_chat_completion(None)
        mock_get_client.return_value = mock_client

        with pytest.raises(RuntimeError, match="LLM call failed"):
            _call_with_retry(
                messages=[{"role": "user", "content": "hi"}],
                response_model=QuestionsResponse,
                max_retries=2,
            )


class TestRetryExhaustion:
    """APIError and RateLimitError should exhaust retries then raise."""

    @patch("llm_client.get_openai_client")
    def test_api_error_retries_then_raises(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = APIError(
            message="Server error", request=MagicMock(), body=None,
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(RuntimeError, match="LLM call failed after 2 retries"):
            _call_with_retry(
                messages=[{"role": "user", "content": "hi"}],
                response_model=QuestionsResponse,
                max_retries=2,
            )

    @patch("llm_client.get_openai_client")
    def test_rate_limit_error_retries_then_raises(self, mock_get_client):
        mock_client = MagicMock()
        mock_response = MagicMock(spec=httpx.Response, status_code=429, headers={})
        mock_client.chat.completions.create.side_effect = RateLimitError(
            message="Rate limited", response=mock_response, body=None,
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(RuntimeError, match="LLM call failed after 2 retries"):
            _call_with_retry(
                messages=[{"role": "user", "content": "hi"}],
                response_model=QuestionsResponse,
                max_retries=2,
            )

    @patch("llm_client._call_with_retry")
    @patch("llm_client.fallback_questions")
    def test_question_gen_falls_back_on_llm_failure(self, mock_fallback, mock_call):
        mock_call.side_effect = RuntimeError("LLM down")
        mock_fallback.return_value = []
        result = generate_questions(A_PROFILE)
        assert result == []
        mock_fallback.assert_called_once_with(A_PROFILE, needed=5, question_config=None)


class TestAllSkipped:
    """Edge cases when no evaluations exist."""

    def test_overall_score_zero_when_no_evaluations(self):
        assert calculate_overall_score({}) == 0.0

    def test_letter_grade_f_when_score_is_zero(self):
        assert get_letter_grade(0.0) == LetterGrade.F

    def test_synthesize_needs_profile(self):
        state = SessionState()
        with pytest.raises(ValueError, match="Cannot synthesize scorecard without a profile"):
            synthesize_scorecard(state)

    def test_session_state_isolation(self):
        s1 = SessionState(current_state=InterviewState.IDLE, profile=A_PROFILE)
        s2 = SessionState()
        assert s1 is not s2
        assert s1.profile is not None
        assert s2.profile is None


class TestFallback:
    """Verify the static fallback question bank returns the correct ratio."""

    def test_fallback_questions_returns_correct_ratio(self):
        from fallback_data import fallback_questions
        result = fallback_questions(A_PROFILE, needed=5)
        assert len(result) == 5
        tech = [q for q in result if q.category != Competency.COMMUNICATION and q.category != Competency.LEADERSHIP and q.category != Competency.OWNERSHIP]
        behav = [q for q in result if q.category in (Competency.COMMUNICATION, Competency.LEADERSHIP, Competency.OWNERSHIP)]
        assert len(tech) == 3
        assert len(behav) == 2
