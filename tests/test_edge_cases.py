from unittest.mock import MagicMock, patch

import pytest
from openai import APIError

from llm_client import (
    _EvaluationResponse,
    _ScorecardResponse,
    QuestionsResponse,
    _call_with_retry,
    evaluate_answer,
    generate_questions,
    synthesize_scorecard,
)
from schemas import (
    Evaluation,
    LetterGrade,
    Question,
    QuestionCategory,
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

A_QUESTION = Question(id="q1", text="Test?", category=QuestionCategory.TECHNICAL)


def _mock_chat_completion(content: str | None):
    mock_message = MagicMock()
    mock_message.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


class TestInjectionResistance:
    @patch("llm_client._call_with_retry")
    def test_out_of_range_scores_are_clamped(self, mock_call):
        mock_call.return_value = _EvaluationResponse(
            clarity=100, completeness=-5, relevance=999, grammar=0, impact=11,
            grammar_correction="", simplified_version="", actionable_feedback="",
        )
        result = evaluate_answer(A_QUESTION, "malicious answer", A_PROFILE)
        assert result.clarity == 10
        assert result.completeness == 1
        assert result.relevance == 10
        assert result.grammar == 1
        assert result.impact == 10

    def test_injection_guard_in_prompt(self):
        from prompts import EVALUATION_PROMPT, INJECTION_GUARD
        assert INJECTION_GUARD in EVALUATION_PROMPT

    @patch("llm_client._call_with_retry")
    def test_legitimate_scores_unchanged(self, mock_call):
        mock_call.return_value = _EvaluationResponse(
            clarity=3, completeness=4, relevance=5, grammar=6, impact=7,
            grammar_correction="x", simplified_version="y", actionable_feedback="z",
        )
        result = evaluate_answer(A_QUESTION, "good answer", A_PROFILE)
        assert result.clarity == 3
        assert result.completeness == 4
        assert result.relevance == 5
        assert result.grammar == 6
        assert result.impact == 7


class TestMalformedJSON:
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

    @patch("llm_client._call_with_retry")
    @patch("llm_client.fallback_questions")
    def test_question_gen_falls_back_on_llm_failure(self, mock_fallback, mock_call):
        mock_call.side_effect = RuntimeError("LLM down")
        mock_fallback.return_value = []
        result = generate_questions(A_PROFILE)
        assert result == []
        mock_fallback.assert_called_once_with(A_PROFILE, needed=5)


class TestAllSkipped:
    def test_overall_score_zero_when_no_evaluations(self):
        assert calculate_overall_score({}) == 0.0

    def test_letter_grade_f_when_score_is_zero(self):
        assert get_letter_grade(0.0) == LetterGrade.F

    def test_synthesize_needs_profile(self):
        state = SessionState()
        with pytest.raises(ValueError, match="Cannot synthesize scorecard without a profile"):
            synthesize_scorecard(state)


class TestFallback:
    def test_fallback_questions_returns_correct_ratio(self):
        from fallback_data import fallback_questions
        result = fallback_questions(A_PROFILE, needed=5)
        assert len(result) == 5
        tech = [q for q in result if q.category == QuestionCategory.TECHNICAL]
        behav = [q for q in result if q.category == QuestionCategory.BEHAVIOURAL]
        assert len(tech) == 3
        assert len(behav) == 2
