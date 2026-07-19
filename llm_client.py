import time
from typing import TypeVar

from openai import APIError, RateLimitError
from pydantic import BaseModel

from config import config
from fallback_data import fallback_questions
from prompts import EVALUATION_PROMPT, QUESTION_GEN_PROMPT, SCORECARD_PROMPT
from providers import get_openai_client
from schemas import Evaluation, Question, Scorecard, SessionState, UserProfile

T = TypeVar("T", bound=BaseModel)


class QuestionsResponse(BaseModel):
    questions: list[Question]


class _EvaluationResponse(BaseModel):
    clarity: int
    completeness: int
    relevance: int
    grammar: int
    impact: int
    grammar_correction: str
    simplified_version: str
    actionable_feedback: str


class _ScorecardResponse(BaseModel):
    strengths: list[str]
    improvements: list[str]
    model_answer: str
    overall_assessment: str
    grade: str


def _call_with_retry(
    messages: list[dict],
    response_model: type[T],
    max_retries: int = 2,
) -> T:
    client = get_openai_client()
    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=config.openai_model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.7,
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
    try:
        messages = [
            {
                "role": "system",
                "content": QUESTION_GEN_PROMPT.format(
                    role=profile.role,
                    seniority=profile.seniority.value,
                    industry=profile.industry,
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Generate interview questions for a {profile.seniority.value} "
                    f"{profile.role} in {profile.industry}."
                ),
            },
        ]
        result = _call_with_retry(messages, QuestionsResponse)
        return result.questions
    except Exception:
        return fallback_questions(profile, needed=5)


def evaluate_answer(
    question: Question,
    answer: str,
    profile: UserProfile,
) -> Evaluation:
    messages = [
        {
            "role": "system",
            "content": EVALUATION_PROMPT.format(
                question=question.text,
                answer=answer,
                role=profile.role,
                seniority=profile.seniority.value,
            ),
        },
        {
            "role": "user",
            "content": f"Evaluate this answer to: {question.text}",
        },
    ]
    result = _call_with_retry(messages, _EvaluationResponse)
    return Evaluation(
        clarity=result.clarity,
        completeness=result.completeness,
        relevance=result.relevance,
        grammar=result.grammar,
        impact=result.impact,
        grammar_correction=result.grammar_correction,
        simplified_version=result.simplified_version,
        actionable_feedback=result.actionable_feedback,
    )


def _format_transcript(state: SessionState) -> str:
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
    result = _call_with_retry(messages, _ScorecardResponse)
    return Scorecard(
        strengths=result.strengths,
        improvements=result.improvements,
        model_answer=result.model_answer,
        overall_assessment=result.overall_assessment,
        grade=result.grade,
    )
