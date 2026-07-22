"""LLM client — handles question generation, answer evaluation, and scorecard synthesis."""

import logging
import time
from typing import TypeVar

from openai import APIError, RateLimitError
from pydantic import BaseModel

from config import config
from fallback_data import fallback_questions
from prompts import (
    FOLLOW_UP_PROMPT,
    INTERVIEWER_STYLE_PERSONAS,
    SCORECARD_PROMPT,
    get_evaluation_prompt,
    get_feedback_code_prompt,
    get_feedback_prompt,
    get_question_prompt,
    get_strict_evaluation_prompt,
)
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
    """Internal Pydantic model for the LLM's scorecard response — LLM-generated subset."""
    overall_assessment: str
    hiring_recommendation: str
    candidate_readiness: str
    strongest_competencies: list[dict]
    weakest_competencies: list[dict]
    recurring_patterns: list[str]
    key_concepts_missed: list[str]
    learning_roadmap: list[dict]
    learning_resources: list[dict]


class _FollowUpResponse(BaseModel):
    """Internal Pydantic model for follow-up question generation."""
    follow_up: str


class _StrictEvaluationResponse(BaseModel):
    """Internal Pydantic model for Stage 1 strict scoring.

    Accepts arbitrary extra fields as dimension scores, reasons, and evidence.
    """
    model_config = {"extra": "allow"}
    hiring_decision: str
    confidence: float = 1.0


class _FeedbackResponse(BaseModel):
    """Internal Pydantic model for Stage 2 feedback generation."""
    strengths: list[str]
    weaknesses: list[str]
    grammar_correction: str = ""
    simplified_version: str = ""
    code_fix: str = ""
    code_review: str = ""
    actionable_feedback: str


def _call_with_retry(
    messages: list[dict],
    response_model: type[T],
    max_retries: int = 2,
    temperature: float = 0.7,
) -> T:
    """Call the LLM with exponential backoff retry. Raises RuntimeError after exhaustion."""
    logger = logging.getLogger(__name__)
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
            logger.info("Groq raw response: %r", content)
            if content is None:
                raise ValueError("Empty response from LLM")
            return response_model.model_validate_json(content)
        except (APIError, RateLimitError, ValueError) as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"LLM call failed after {max_retries} retries") from last_error


def validate_role(role: str) -> bool:
    """Use Ollama to classify whether a given role is IT-related."""
    import json
    import logging
    import re
    logger = logging.getLogger(__name__)
    logger.info("validate_role input: %r", role)
    from providers import get_ollama_client
    client = get_ollama_client()
    system_prompt = (
        "You are a classifier that determines whether a job role is IT-related "
        "(software engineering, data science, DevOps, IT support, product management in tech, etc.). "
        "Respond with ONLY valid JSON. No other text, no explanation, no markdown formatting.\n\n"
        "The response must be exactly one of the following (without backticks):\n"
        '{"is_it_role": true}\n'
        '{"is_it_role": false}'
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Is the following job role IT-related? Role: {role}"},
    ]
    try:
        response = client.chat.completions.create(
            model=config.ollama_model,
            messages=messages,
            temperature=0,
        )
        content = response.choices[0].message.content
        logger.info("Ollama raw response for role: %r", content)
        if content is None:
            return True
        try:
            data = json.loads(content)
            return bool(data["is_it_role"])
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        m = re.search(r'"is_it_role"\s*:\s*(true|false)', content, re.IGNORECASE)
        if m:
            return m.group(1).lower() == "true"
        logger.error("Failed to parse boolean for role from: %r", content)
        return True
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


def _evaluate_llm_strict(
    question: Question,
    answer: str,
    profile: UserProfile,
) -> tuple[dict[str, int], dict[str, str], dict[str, str], str, float]:
    """Stage 1 — Strict scoring. Returns (scores, score_reasons, score_evidence, hiring_decision, confidence)."""
    messages = [
        {
            "role": "system",
            "content": get_strict_evaluation_prompt(
                question.text, answer, profile,
                question_type=question.question_type.value,
            ),
        },
        {
            "role": "user",
            "content": f"Evaluate this answer to: {question.text}",
        },
    ]
    result = _call_with_retry(messages, _StrictEvaluationResponse, temperature=config.evaluation_temperature)

    KNOWN_FIELDS = {"hiring_decision", "confidence"}
    scores: dict[str, int] = {}
    score_reasons: dict[str, str] = {}
    score_evidence: dict[str, str] = {}
    confidence: float = 1.0

    for key, val in result.model_dump().items():
        if key in KNOWN_FIELDS:
            if key == "confidence" and isinstance(val, (int, float)):
                confidence = max(0.0, min(1.0, float(val)))
            continue
        if key.endswith("_evidence") and isinstance(val, str):
            score_evidence[key] = val
        elif key.endswith("_reason") and isinstance(val, str):
            score_reasons[key] = val
        elif isinstance(val, (int, float)):
            scores[key] = max(1, min(10, int(val)))

    return scores, score_reasons, score_evidence, result.hiring_decision, confidence


def _generate_feedback(
    question: Question,
    scores_json: str,
) -> _FeedbackResponse | None:
    """Stage 2 — Feedback generation. Dispatches code-specific prompt for coding/debugging."""
    is_code = question.question_type in (QuestionType.CODING, QuestionType.DEBUGGING)
    prompt = get_feedback_code_prompt(scores_json) if is_code else get_feedback_prompt(scores_json)
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": f"Generate feedback for this answer to: {question.text}",
        },
    ]
    try:
        return _call_with_retry(messages, _FeedbackResponse, temperature=config.evaluation_temperature)
    except Exception:
        return None


def _evaluate_llm(
    question: Question,
    answer: str,
    profile: UserProfile,
) -> Evaluation:
    """Two-stage LLM evaluation for free-response question types.

    Stage 1 — Strict scoring with mandatory score caps, evidence requirements,
    and hiring decision. Returns scores, reasons, evidence, and confidence.
    Stage 2 — Helpful feedback generation (strengths, weaknesses, grammar,
    simplified version, actionable feedback). Uses Stage 1 scores as context.
    """
    scores, score_reasons, score_evidence, hiring_decision, confidence = _evaluate_llm_strict(
        question, answer, profile,
    )

    # Build Stage 1 JSON summary for the feedback prompt
    stage1_lines = []
    for dim in scores:
        score_str = f'"{dim}": {scores[dim]}'
        reason_key = f"{dim}_reason"
        evidence_key = f"{dim}_evidence"
        score_str += f', "{reason_key}": "{score_reasons.get(reason_key, "")}"'
        score_str += f', "{evidence_key}": "{score_evidence.get(evidence_key, "")}"'
        stage1_lines.append("  " + score_str)
    stage1_json = "{\n" + "\n".join(stage1_lines) + f'\n  "hiring_decision": "{hiring_decision}",\n  "confidence": {confidence}\n}}'

    feedback = _generate_feedback(question, stage1_json)

    return Evaluation(
        scores=scores,
        score_reasons=score_reasons,
        score_evidence=score_evidence,
        hiring_decision=hiring_decision,
        confidence=confidence,
        strengths=feedback.strengths if feedback else [],
        weaknesses=feedback.weaknesses if feedback else [],
        grammar_correction=feedback.grammar_correction if feedback else "",
        simplified_version=feedback.simplified_version if feedback else "",
        code_fix=feedback.code_fix if feedback else "",
        code_review=feedback.code_review if feedback else "",
        actionable_feedback=feedback.actionable_feedback if feedback else "Coaching unavailable.",
    )


def _build_evaluation_json(state: SessionState) -> str:
    """Build a structured JSON summary of all evaluations for the scorecard prompt."""
    import json
    questions_data = []
    for q in state.questions:
        answer = state.transcript.get(q.id)
        eval_ = state.evaluations.get(q.id)
        entry = {
            "id": q.id,
            "text": q.text,
            "category": q.category.value,
            "question_type": q.question_type.value,
        }
        if answer is not None:
            entry["answer"] = answer
        else:
            entry["skipped"] = True
        if eval_ is not None:
            entry["scores"] = eval_.scores
            entry["score_reasons"] = eval_.score_reasons
            entry["score_evidence"] = eval_.score_evidence
            entry["hiring_decision"] = eval_.hiring_decision
            entry["confidence"] = eval_.confidence
        questions_data.append(entry)
    return json.dumps({"questions": questions_data}, indent=2)


def _format_transcript(state: SessionState) -> str:
    """Format the full interview transcript as a string for supplementary context."""
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

    Uses structured evaluation JSON as primary LLM input with transcript as
    supplementary context. Merges LLM-generated synthesis with deterministic
    stats computed in Python.

    Raises ValueError if the session has no profile.
    """
    from scoring import (
        calculate_overall_score,
        compute_confidence_notice,
        compute_interview_stats,
        compute_question_table,
        get_letter_grade,
        interpret_radar_chart,
        prepare_radar_chart_data,
    )

    evaluation_json = _build_evaluation_json(state)
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
                industry=profile.industry,
                evaluation_json=evaluation_json,
                transcript=transcript,
            ),
        },
        {
            "role": "user",
            "content": "Synthesize the final scorecard for this interview.",
        },
    ]
    result = _call_with_retry(messages, _ScorecardResponse, temperature=config.scorecard_temperature)

    # Compute deterministic stats in Python
    evals = state.evaluations
    overall = calculate_overall_score(evals)
    grade = get_letter_grade(overall)

    return Scorecard(
        overall_assessment=result.overall_assessment,
        hiring_recommendation=result.hiring_recommendation,
        candidate_readiness=result.candidate_readiness,
        strongest_competencies=result.strongest_competencies,
        weakest_competencies=result.weakest_competencies,
        recurring_patterns=result.recurring_patterns,
        key_concepts_missed=result.key_concepts_missed,
        learning_roadmap=result.learning_roadmap,
        learning_resources=result.learning_resources,
        overall_score=overall,
        grade=grade,
        question_table=compute_question_table(state),
        dimension_averages=prepare_radar_chart_data(evals),
        stats=compute_interview_stats(state),
        radar_interpretation=interpret_radar_chart(state),
        confidence_notice=compute_confidence_notice(state),
    )


def generate_follow_up(
    question: Question,
    answer: str,
    evaluation: Evaluation,
    profile: UserProfile,
) -> str:
    """Generate one adaptive follow-up question based on the candidate's answer."""
    if not question.text or not answer:
        raise ValueError("Question and answer are required to generate a follow-up.")  # noqa: TRY003

    style_key = profile.interviewer_style.value if hasattr(profile, 'interviewer_style') else "default"
    interviewer_persona = INTERVIEWER_STYLE_PERSONAS.get(style_key, INTERVIEWER_STYLE_PERSONAS["default"])

    eval_summary = "\n".join(
        f"{dim}: {score}" for dim, score in evaluation.scores.items()
    )
    if evaluation.weaknesses:
        eval_summary += "\nWeaknesses: " + ", ".join(evaluation.weaknesses)
    if evaluation.actionable_feedback:
        eval_summary += f"\nFeedback: {evaluation.actionable_feedback}"

    follow_up_prompt = FOLLOW_UP_PROMPT.format(interviewer_style_persona=interviewer_persona)

    messages = [
        {"role": "system", "content": follow_up_prompt},
        {
            "role": "user",
            "content": (
                f"Original question:\n{question.text}\n\n"
                f"Candidate's answer:\n{answer}\n\n"
                f"Evaluation summary:\n{eval_summary}"
            ),
        },
    ]
    try:
        result = _call_with_retry(messages, _FollowUpResponse, temperature=config.evaluation_temperature)
        return result.follow_up
    except Exception:
        return "Can you go deeper on that?"
