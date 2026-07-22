"""LLM client — handles question generation, answer evaluation, and scorecard synthesis."""

import time
from typing import TypeVar

from openai import APIError, RateLimitError
from pydantic import BaseModel

from config import config
from fallback_data import fallback_questions
from prompts import SCORECARD_PROMPT, get_evaluation_prompt, get_question_prompt
from providers import get_openai_client
from schemas import Evaluation, Question, QuestionConfig, QuestionType, Scorecard, SessionState, UserProfile

T = TypeVar("T", bound=BaseModel)


class QuestionsResponse(BaseModel):
    """Pydantic model for the LLM's question-generation response."""
    questions: list[Question]


class _EvaluationResponse(BaseModel):
    """Internal Pydantic model for the LLM's evaluation response.

    Accepts arbitrary extra fields as dimension scores so each question
    type can return its own set of relevant metrics.
    """
    model_config = {"extra": "allow"}
    strengths: list[str]
    weaknesses: list[str]
    grammar_correction: str
    simplified_version: str
    actionable_feedback: str


class _ScorecardResponse(BaseModel):
    """Internal Pydantic model for the LLM's scorecard response."""
    strengths: list[str]
    improvements: list[str]
    model_answer: str
    overall_assessment: str
    grade: str


class _RoleValidationResponse(BaseModel):
    """Response model for role validation."""
    is_it_role: bool


def _call_with_retry(
    messages: list[dict],
    response_model: type[T],
    max_retries: int = 2,
    temperature: float = 0.7,
) -> T:
    """Call the LLM with exponential backoff retry. Raises RuntimeError after exhaustion."""
    client = get_openai_client()
    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=config.openai_model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature,
            )
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("Empty response from LLM")
            return response_model.model_validate_json(content)
        except (APIError, RateLimitError, ValueError) as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"LLM call failed after {max_retries} retries") from last_error


def validate_role(role: str) -> bool:
    """Use the LLM to classify whether a given role is IT-related."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a classifier that determines whether a job role is IT-related "
                "(software engineering, data science, DevOps, IT support, product management in tech, etc.). "
                "Return a JSON object with a single boolean field `is_it_role`."
            ),
        },
        {
            "role": "user",
            "content": f"Is the following job role IT-related? Role: {role}",
        },
    ]
    try:
        result = _call_with_retry(messages, _RoleValidationResponse, temperature=0)
        return result.is_it_role
    except Exception:
        return True


def generate_questions(profile: UserProfile, question_config: QuestionConfig | None = None) -> list[Question]:
    """Generate interview questions for the given profile.
    
    When no config is supplied, defaults to 5 questions (3 technical, 2 behavioural).
    Falls back to static questions from fallback_data if the LLM call fails.
    """
    try:
        messages = [
            {"role": "system", "content": get_question_prompt(profile, question_config)},
            {
                "role": "user",
                "content": (
                    f"Generate interview questions for a {profile.seniority.value} "
                    f"{profile.role} in {profile.industry}."
                ),
            },
        ]
        result = _call_with_retry(messages, QuestionsResponse, temperature=config.generation_temperature)
        return result.questions
    except Exception:
        needed = question_config.total_questions if question_config else 5
        return fallback_questions(profile, needed=needed, question_config=question_config)


def evaluate_answer(
    question: Question,
    answer: str,
    profile: UserProfile,
) -> Evaluation:
    """Evaluate a single answer.
    
    Dispatches to deterministic evaluation for objective question types
    (mcq, yes_no) and LLM-based evaluation for free-response types.
    """
    if question.question_type in (QuestionType.MCQ, QuestionType.YES_NO):
        return _evaluate_objective(question, answer)
    return _evaluate_llm(question, answer, profile)


def _evaluate_objective(question: Question, answer: str) -> Evaluation:
    """Deterministic evaluation for MCQ and Yes/No questions."""
    expected = str(question.correct_answer).strip().lower() if question.correct_answer is not None else ""
    given = answer.strip().lower()
    correct = expected == given
    if correct:
        return Evaluation(
            scores={"correctness": 10},
            strengths=["Correct answer"],
            weaknesses=[],
            grammar_correction="",
            simplified_version="",
            actionable_feedback="Correct.",
        )
    return Evaluation(
        scores={"correctness": 1},
        strengths=[],
        weaknesses=["Incorrect answer"],
        grammar_correction="",
        simplified_version="",
        actionable_feedback=f"Incorrect. The correct answer is {question.correct_answer}.",
    )


def _evaluate_llm(
    question: Question,
    answer: str,
    profile: UserProfile,
) -> Evaluation:
    """LLM-based evaluation for free-response question types.

    Passes the question type to the prompt so it returns only relevant
    dimensions. Scores are clamped to the 1-10 range before returning.
    """
    messages = [
        {
            "role": "system",
            "content": get_evaluation_prompt(
                question.text, answer, profile,
                question_type=question.question_type.value,
            ),
        },
        {
            "role": "user",
            "content": f"Evaluate this answer to: {question.text}",
        },
    ]
    result = _call_with_retry(messages, _EvaluationResponse, temperature=config.evaluation_temperature)

    # Extract dimension scores from extra fields (anything not a known field)
    KNOWN_FIELDS = {"strengths", "weaknesses", "grammar_correction", "simplified_version", "actionable_feedback"}
    scores: dict[str, int] = {}
    for key, val in result.model_dump().items():
        if key in KNOWN_FIELDS:
            continue
        if isinstance(val, (int, float)):
            scores[key] = max(1, min(10, int(val)))

    return Evaluation(
        scores=scores,
        strengths=result.strengths,
        weaknesses=result.weaknesses,
        grammar_correction=result.grammar_correction,
        simplified_version=result.simplified_version,
        actionable_feedback=result.actionable_feedback,
    )


def _format_transcript(state: SessionState) -> str:
    """Format the full interview transcript as a string for the scorecard prompt."""
    lines: list[str] = []
    for q in state.questions:
        answer = state.transcript.get(q.id)
        eval_ = state.evaluations.get(q.id)
        lines.append(f"Q: {q.text}")
        if answer is not None:
            lines.append(f"A: {answer}")
        if eval_ is not None:
            parts = [f"{k.capitalize()}: {v}/10" for k, v in eval_.scores.items()]
            lines.append("Scores — " + ", ".join(parts))
        lines.append("")
    return "\n".join(lines)


def synthesize_scorecard(state: SessionState) -> Scorecard:
    """Synthesise a final scorecard from the full session state.
    
    Raises ValueError if the session has no profile.
    """
    transcript = _format_transcript(state)
    profile = state.profile
    if profile is None:
        raise ValueError("Cannot synthesize scorecard without a profile")
    messages = [
        {
            "role": "system",
            "content": SCORECARD_PROMPT.format(
                role=profile.role,
                seniority=profile.seniority.value,
                transcript=transcript,
            ),
        },
        {
            "role": "user",
            "content": "Synthesize the final scorecard for this interview.",
        },
    ]
    result = _call_with_retry(messages, _ScorecardResponse, temperature=config.scorecard_temperature)
    return Scorecard(
        strengths=result.strengths,
        improvements=result.improvements,
        model_answer=result.model_answer,
        overall_assessment=result.overall_assessment,
        grade=result.grade,
    )
