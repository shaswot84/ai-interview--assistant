"""LLM client — handles question generation, answer evaluation, and scorecard synthesis."""

import time
from typing import TypeVar

from openai import APIError, RateLimitError
from pydantic import BaseModel

from config import config
from fallback_data import fallback_questions
from prompts import SCORECARD_PROMPT, get_evaluation_prompt, get_question_prompt
from providers import get_openai_client
from schemas import Evaluation, Question, Scorecard, SessionState, UserProfile

T = TypeVar("T", bound=BaseModel)


class QuestionsResponse(BaseModel):
    """Pydantic model for the LLM's question-generation response."""
    questions: list[Question]


class _EvaluationResponse(BaseModel):
    """Internal Pydantic model for the LLM's evaluation response (raw scores)."""
    clarity: int
    completeness: int
    relevance: int
    grammar: int
    impact: int
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


def generate_questions(profile: UserProfile) -> list[Question]:
    """Generate 5 interview questions (3 technical, 2 behavioural) for the given profile.
    
    Falls back to static questions from fallback_data if the LLM call fails.
    """
    try:
        messages = [
            {"role": "system", "content": get_question_prompt(profile)},
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
        return fallback_questions(profile, needed=5)


def evaluate_answer(
    question: Question,
    answer: str,
    profile: UserProfile,
) -> Evaluation:
    """Evaluate a single answer across five dimensions and return an Evaluation.
    
    Scores are clamped to the 1-10 range before returning.
    """
    messages = [
        {
            "role": "system",
            "content": get_evaluation_prompt(question.text, answer, profile),
        },
        {
            "role": "user",
            "content": f"Evaluate this answer to: {question.text}",
        },
    ]
    result = _call_with_retry(messages, _EvaluationResponse, temperature=config.evaluation_temperature)
    return Evaluation(
        clarity=max(1, min(10, result.clarity)),
        completeness=max(1, min(10, result.completeness)),
        relevance=max(1, min(10, result.relevance)),
        grammar=max(1, min(10, result.grammar)),
        impact=max(1, min(10, result.impact)),
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
            lines.append(
                f"Scores — Clarity: {eval_.clarity}/10, "
                f"Completeness: {eval_.completeness}/10, "
                f"Relevance: {eval_.relevance}/10, "
                f"Grammar: {eval_.grammar}/10, "
                f"Impact: {eval_.impact}/10"
            )
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
