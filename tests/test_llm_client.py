"""Tests for the LLM client — retry logic, question generation, evaluation, and scorecards."""

from unittest.mock import MagicMock, patch

import pytest

from llm_client import (
    _EvaluationResponse,
    _FollowUpResponse,
    _ScorecardResponse,
    QuestionsResponse,
    _call_with_retry,
    evaluate_answer,
    generate_follow_up,
    generate_questions,
    synthesize_scorecard,
)
from schemas import (
    Competency,
    Evaluation,
    Question,
    QuestionType,
    Scorecard,
    Seniority,
    SessionState,
    UserProfile,
)


def _mock_chat_completion(content: str):
    """Return a mock OpenAI chat completion with the given string content."""
    mock_message = MagicMock()
    mock_message.content = content
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


A_PROFILE = UserProfile(
    role="Backend Engineer",
    seniority=Seniority.MID,
    industry="FinTech",
    interview_type="technical",
)

A_QUESTION = Question(
    id="q1",
    text="What is a RESTful API?",
    category=Competency.API_DESIGN,
)

VALID_QUESTIONS_JSON = """{
  "questions": [
    {"id": "q1", "text": "What is REST?", "category": "api_design"},
    {"id": "q2", "text": "Explain ACID.", "category": "databases"},
    {"id": "q3", "text": "How do you debug a memory leak?", "category": "debugging"},
    {"id": "q4", "text": "Tell me about a conflict.", "category": "communication"},
    {"id": "q5", "text": "How do you prioritise?", "category": "ownership"}
  ]
}"""

VALID_EVALUATION_JSON = """{
  "clarity": 8,
  "completeness": 7,
  "relevance": 9,
  "correctness": 8,
  "technical_depth": 7,
  "problem_solving": 8,
  "tradeoff_analysis": 6,
  "strengths": ["Clear", "Structured", "Relevant"],
  "weaknesses": ["Depth", "Trade-offs", "Grammar"],
  "grammar_correction": "Fixed grammar.",
  "simplified_version": "Simpler version.",
  "actionable_feedback": "Be more specific."
}"""

VALID_SCORECARD_JSON = """{
  "strengths": ["Good communication"],
  "improvements": ["Be more concise"],
  "model_answer": "A comprehensive answer...",
  "overall_assessment": "Solid performance.",
  "grade": "B"
}"""


class TestCallWithRetry:
    """_call_with_retry — success path and retry exhaustion."""
    @patch("llm_client.get_openai_client")
    def test_returns_parsed_model(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_chat_completion(
            VALID_QUESTIONS_JSON
        )
        mock_get_client.return_value = mock_client

        result = _call_with_retry(
            messages=[{"role": "user", "content": "hello"}],
            response_model=QuestionsResponse,
        )
        assert isinstance(result, QuestionsResponse)
        assert len(result.questions) == 5

    @patch("llm_client.get_openai_client")
    def test_raises_after_max_retries(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = ValueError("API error")
        mock_get_client.return_value = mock_client

        with pytest.raises(RuntimeError, match="LLM call failed after 2 retries"):
            _call_with_retry(
                messages=[{"role": "user", "content": "hello"}],
                response_model=QuestionsResponse,
                max_retries=2,
            )


class TestGenerateQuestions:
    """generate_questions — LLM success and fallback paths."""
    @patch("llm_client._call_with_retry")
    def test_returns_questions_from_llm(self, mock_call):
        expected = [
            Question(id="q1", text="What is REST?", category=Competency.API_DESIGN),
        ]
        mock_call.return_value = QuestionsResponse(questions=expected)
        result = generate_questions(A_PROFILE)
        assert result == expected

    @patch("llm_client._call_with_retry")
    @patch("llm_client.fallback_questions")
    def test_falls_back_on_llm_failure(self, mock_fallback, mock_call):
        mock_call.side_effect = RuntimeError("API down")
        fallback_qs = [
            Question(id="f1", text="Fallback?", category=Competency.PROBLEM_SOLVING),
        ]
        mock_fallback.return_value = fallback_qs
        result = generate_questions(A_PROFILE)
        assert result == fallback_qs
        mock_fallback.assert_called_once_with(A_PROFILE, needed=5, question_config=None)

    @patch("llm_client._call_with_retry")
    def test_generated_questions_have_unique_competencies(self, mock_call):
        expected = [
            Question(id="q1", text="Q1", category=Competency.ALGORITHMS),
            Question(id="q2", text="Q2", category=Competency.DATABASES),
            Question(id="q3", text="Q3", category=Competency.API_DESIGN),
            Question(id="q4", text="Q4", category=Competency.COMMUNICATION),
            Question(id="q5", text="Q5", category=Competency.OWNERSHIP),
        ]
        mock_call.return_value = QuestionsResponse(questions=expected)
        result = generate_questions(A_PROFILE)
        competencies = [q.category for q in result]
        assert len(competencies) == len(set(competencies))

    @patch("llm_client._call_with_retry")
    def test_generated_questions_are_not_cliches(self, mock_call):
        mock_call.return_value = QuestionsResponse(questions=[
            Question(id="q1", text="What is REST?", category=Competency.API_DESIGN),
            Question(id="q2", text="Explain ACID.", category=Competency.DATABASES),
            Question(id="q3", text="How do you debug a crash?", category=Competency.DEBUGGING),
        ])
        result = generate_questions(A_PROFILE)
        cliche_phrases = ["what is docker", "explain oop", "what is polymorphism"]
        for q in result:
            lowered = q.text.lower()
            assert not any(phrase in lowered for phrase in cliche_phrases), q.text

    @patch("llm_client._call_with_retry")
    def test_generated_questions_include_industry_context(self, mock_call):
        mock_call.return_value = QuestionsResponse(questions=[
            Question(id="q1", text="How would you handle fraud detection in FinTech?", category=Competency.PROBLEM_SOLVING,
                     expected_keywords=["fraud", "consistency"]),
            Question(id="q2", text="Explain ACID.", category=Competency.DATABASES),
        ])
        result = generate_questions(A_PROFILE)
        industry = A_PROFILE.industry.lower()
        assert any(industry in q.text.lower() or industry in " ".join(q.expected_keywords).lower() for q in result)


class TestEvaluateAnswer:
    """evaluate_answer — validates the returned Evaluation object."""
    @patch("llm_client._call_with_retry")
    def test_returns_evaluation(self, mock_call):
        mock_call.return_value = _EvaluationResponse(
            strengths=["Clear", "Structured", "Relevant"],
            weaknesses=["Depth", "Trade-offs", "Grammar"],
            grammar_correction="Fixed.",
            simplified_version="Simple.",
            actionable_feedback="More detail.",
            # Extra fields → dimension scores
            clarity=8,
            clarity_reason="Explained concepts clearly but missed details.",
            completeness=7,
            completeness_reason="Covered main points but omitted edge cases.",
            relevance=9,
            correctness=8,
            technical_depth=7,
            problem_solving=8,
            tradeoff_analysis=6,
            # Confidence
            confidence=0.85,
        )
        result = evaluate_answer(A_QUESTION, "My answer", A_PROFILE)
        assert isinstance(result, Evaluation)
        assert result.scores["clarity"] == 8
        assert result.scores["technical_depth"] == 7
        assert result.score_reasons["clarity_reason"] == "Explained concepts clearly but missed details."
        assert result.score_reasons["completeness_reason"] == "Covered main points but omitted edge cases."
        assert result.confidence == 0.85
        assert result.strengths == ["Clear", "Structured", "Relevant"]


class TestEvaluateAnswerDeterministic:
    """Deterministic evaluation for MCQ and Yes/No question types."""

    def test_mcq_correct_answer(self):
        q = Question(
            id="q1", text="What is 2+2?", category=Competency.PROBLEM_SOLVING,
            question_type=QuestionType.MCQ, correct_answer="4",
        )
        result = evaluate_answer(q, "4", A_PROFILE)
        assert isinstance(result, Evaluation)
        assert result.scores["correctness"] == 10
        assert result.actionable_feedback == "Correct."
        assert result.strengths == ["Correct answer"]

    def test_mcq_wrong_answer(self):
        q = Question(
            id="q2", text="What is 2+2?", category=Competency.PROBLEM_SOLVING,
            question_type=QuestionType.MCQ, correct_answer="4",
        )
        result = evaluate_answer(q, "5", A_PROFILE)
        assert result.scores["correctness"] == 1
        assert "Incorrect" in result.actionable_feedback
        assert "4" in result.actionable_feedback
        assert result.weaknesses == ["Incorrect answer"]

    def test_mcq_case_insensitive(self):
        q = Question(
            id="q3", text="What is REST?", category=Competency.API_DESIGN,
            question_type=QuestionType.MCQ, correct_answer="Representational State Transfer",
        )
        result = evaluate_answer(q, "representational state transfer", A_PROFILE)
        assert result.scores["correctness"] == 10
        assert result.actionable_feedback == "Correct."

    def test_yes_no_correct(self):
        q = Question(
            id="q4", text="Is Python interpreted?", category=Competency.ALGORITHMS,
            question_type=QuestionType.YES_NO, correct_answer="Yes",
        )
        result = evaluate_answer(q, "Yes", A_PROFILE)
        assert result.scores["correctness"] == 10
        assert result.actionable_feedback == "Correct."

    def test_yes_no_wrong(self):
        q = Question(
            id="q5", text="Is Python interpreted?", category=Competency.ALGORITHMS,
            question_type=QuestionType.YES_NO, correct_answer="Yes",
        )
        result = evaluate_answer(q, "No", A_PROFILE)
        assert result.scores["correctness"] == 1
        assert "Incorrect" in result.actionable_feedback

    def test_mcq_no_correct_answer_falls_back_to_empty(self):
        q = Question(
            id="q6", text="Test", category=Competency.PROBLEM_SOLVING,
            question_type=QuestionType.MCQ, correct_answer=None,
        )
        result = evaluate_answer(q, "anything", A_PROFILE)
        assert result.scores["correctness"] == 1


class TestSynthesizeScorecard:
    """synthesize_scorecard — validates Scorecard output and profile requirement."""
    @patch("llm_client._call_with_retry")
    def test_returns_scorecard(self, mock_call):
        mock_call.return_value = _ScorecardResponse(
            strengths=["Good"],
            improvements=["Needs work"],
            model_answer="Ideal answer",
            overall_assessment="Decent",
            grade="B",
        )
        state = SessionState(profile=A_PROFILE)
        result = synthesize_scorecard(state)
        assert isinstance(result, Scorecard)
        assert result.grade.value == "B"

    def test_raises_without_profile(self):
        state = SessionState()
        with pytest.raises(ValueError, match="Cannot synthesize scorecard without a profile"):
            synthesize_scorecard(state)


class TestGenerateFollowUp:
    """generate_follow_up — validates follow-up question generation."""

    @patch("llm_client._call_with_retry")
    def test_returns_follow_up_text(self, mock_call):
        from schemas import Evaluation
        mock_call.return_value = _FollowUpResponse(follow_up="Can you explain the trade-offs?")
        sample_eval = Evaluation(
            scores={"clarity": 7, "technical_depth": 6},
            strengths=[], weaknesses=[],
            grammar_correction="", simplified_version="", actionable_feedback="",
        )
        result = generate_follow_up(A_QUESTION, "My answer", sample_eval, A_PROFILE)
        assert result == "Can you explain the trade-offs?"

    def test_raises_on_empty_answer(self):
        from schemas import Evaluation
        sample_eval = Evaluation(
            scores={}, strengths=[], weaknesses=[],
            grammar_correction="", simplified_version="", actionable_feedback="",
        )
        with pytest.raises(ValueError, match="Question and answer are required"):
            generate_follow_up(A_QUESTION, "", sample_eval, A_PROFILE)

    def test_raises_on_empty_question(self):
        from schemas import Evaluation
        sample_eval = Evaluation(
            scores={}, strengths=[], weaknesses=[],
            grammar_correction="", simplified_version="", actionable_feedback="",
        )
        empty_q = Question(id="q0", text="", category=Competency.PROBLEM_SOLVING)
        with pytest.raises(ValueError, match="Question and answer are required"):
            generate_follow_up(empty_q, "answer", sample_eval, A_PROFILE)
