"""Scoring engine — weighted question scores, letter grades, Plotly radar charts, and deterministic stats."""

import plotly.graph_objects as go
import plotly.io as pio

from schemas import Evaluation, LetterGrade, Question, SessionState

TYPE_DIMENSION_WEIGHTS: dict[str, dict[str, float]] = {
    "open_ended": {
        "clarity": 0.15,
        "completeness": 0.20,
        "relevance": 0.15,
        "correctness": 0.20,
        "technical_depth": 0.15,
        "problem_solving": 0.10,
        "tradeoff_analysis": 0.05,
    },
    "behavioral": {
        "clarity": 0.15,
        "completeness": 0.20,
        "relevance": 0.10,
        "problem_solving": 0.15,
        "ownership": 0.15,
        "reflection": 0.10,
        "measurable_impact": 0.10,
        "lessons_learned": 0.05,
    },
    "coding": {
        "correctness": 0.35,
        "solution_quality": 0.25,
        "technical_depth": 0.20,
        "problem_solving": 0.20,
    },
    "debugging": {
        "correctness": 0.30,
        "solution_quality": 0.25,
        "technical_depth": 0.25,
        "problem_solving": 0.20,
    },
    "system_design": {
        "correctness": 0.25,
        "solution_quality": 0.20,
        "tradeoff_analysis": 0.30,
        "technical_depth": 0.15,
        "problem_solving": 0.10,
    },
}


def calculate_question_score(eval_: Evaluation, question_type: str = "open_ended") -> int:
    """Compute an overall score (0–100) from weighted dimension scores for the question type."""
    dims = eval_.scores
    if not dims:
        return 0
    weights = TYPE_DIMENSION_WEIGHTS.get(question_type, {})
    total = 0.0
    weight_sum = 0.0
    for dim, score in dims.items():
        weight = weights.get(dim, 1.0)
        total += score * weight
        weight_sum += weight
    if weight_sum == 0:
        return 0
    return int(round((total / weight_sum) * 10))


def calculate_overall_score(evaluations: dict[str, Evaluation]) -> float:
    """Return the mean question score across all evaluated questions."""
    if not evaluations:
        return 0.0
    scores = [calculate_question_score(e) for e in evaluations.values()]
    return round(sum(scores) / len(scores), 1)


def get_letter_grade(score: float) -> LetterGrade:
    """Convert a numeric score to a letter grade (A ≥ 90, B ≥ 80, …)."""
    if score >= 90:
        return LetterGrade.A
    if score >= 80:
        return LetterGrade.B
    if score >= 70:
        return LetterGrade.C
    if score >= 60:
        return LetterGrade.D
    return LetterGrade.F


def prepare_radar_chart_data(evaluations: dict[str, Evaluation]) -> dict[str, float]:
    """Average each dimension across all evaluations for the radar chart.

    Collects all unique dimension keys across evaluations so the chart
    dynamically adapts per question type. Each dimension is averaged
    only over the evaluations that contain it.
    """
    if not evaluations:
        return {}
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for e in evaluations.values():
        for k, v in e.scores.items():
            totals[k] = totals.get(k, 0.0) + v
            counts[k] = counts.get(k, 0) + 1
    return {
        k: round(totals[k] / counts[k], 1)
        for k in sorted(totals)
        if counts[k] > 0
    }


def render_radar_chart(data: dict[str, float]) -> go.Figure:
    """Render a Plotly polar radar chart from averaged dimension scores."""
    if not data:
        labels = [""]
        values = [0]
    else:
        labels = [k.capitalize() for k in data]
        values = list(data.values())
    fig = go.Figure(
        data=go.Scatterpolar(
            r=values + [values[0]],
            theta=labels + [labels[0]],
            fill="toself",
            line_color="#3B82F6",
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10]),
        ),
        showlegend=False,
        title="Performance by Dimension",
        height=400,
        width=600,
        margin=dict(l=40, r=40, t=40, b=40),
    )
    return fig


# ── Deterministic scorecard stats (Phase 1) ──────────────────────────


def _compute_highest_lowest(evaluations: dict[str, Evaluation]) -> tuple[int, int]:
    """Return (highest, lowest) per-question scores (0-100)."""
    if not evaluations:
        return 0, 0
    scores = [calculate_question_score(e) for e in evaluations.values()]
    return max(scores), min(scores)


def compute_interview_stats(state: SessionState) -> dict:
    """Compute deterministic interview statistics from evaluations and questions.

    Returns a dict with:
      - total_questions, answered, skipped
      - overall_score, letter_grade
      - highest_score, lowest_score
      - avg_confidence
      - type_distribution
      - dimension_averages
    """
    total = len(state.questions)
    answered = sum(1 for qid in state.transcript if state.transcript.get(qid) is not None)
    skipped = total - answered

    evals = state.evaluations
    overall = calculate_overall_score(evals)
    grade = get_letter_grade(overall)
    highest, lowest = _compute_highest_lowest(evals)

    confidences = [e.confidence for e in evals.values() if e.confidence > 0]
    avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

    type_dist: dict[str, int] = {}
    for q in state.questions:
        qt = q.question_type.value
        type_dist[qt] = type_dist.get(qt, 0) + 1

    dim_avgs = prepare_radar_chart_data(evals)

    return {
        "total_questions": total,
        "answered": answered,
        "skipped": skipped,
        "overall_score": overall,
        "letter_grade": grade.value,
        "highest_score": highest,
        "lowest_score": lowest,
        "avg_confidence": avg_confidence,
        "type_distribution": type_dist,
        "dimension_averages": dim_avgs,
    }


def compute_strongest_weakest_dimensions(state: SessionState) -> tuple[list[str], list[str]]:
    """Return the top-3 and bottom-3 dimensions across all evaluations by average score.

    Returns (strongest, weakest) where each is a list of dimension names, ordered.
    """
    dim_avgs = prepare_radar_chart_data(state.evaluations)
    if not dim_avgs:
        return [], []
    sorted_dims = sorted(dim_avgs, key=lambda d: dim_avgs[d], reverse=True)
    strongest = sorted_dims[:3]
    weakest = sorted_dims[-3:][::-1] if len(sorted_dims) >= 3 else sorted_dims[::-1]
    return strongest, weakest


def compute_question_table(state: SessionState) -> list[dict]:
    """Build a per-question summary for the scorecard table.

    Each entry: {id, text, category, score, hiring_decision, confidence, performance_label}
    """
    rows: list[dict] = []
    for q in state.questions:
        answer = state.transcript.get(q.id)
        eval_ = state.evaluations.get(q.id)
        if answer is not None and eval_ is not None:
            score = calculate_question_score(eval_)
            if score >= 85:
                label = "Excellent"
            elif score >= 75:
                label = "Strong"
            elif score >= 60:
                label = "Adequate"
            elif score >= 40:
                label = "Weak"
            else:
                label = "Poor"
            rows.append({
                "id": q.id,
                "text": q.text,
                "category": q.category.value,
                "score": score,
                "hiring_decision": eval_.hiring_decision,
                "confidence": eval_.confidence,
                "performance_label": label,
            })
        elif answer is not None:
            rows.append({
                "id": q.id,
                "text": q.text,
                "category": q.category.value,
                "score": 0,
                "hiring_decision": "",
                "confidence": 0.0,
                "performance_label": "N/A (skipped evaluation)",
            })
        else:
            rows.append({
                "id": q.id,
                "text": q.text,
                "category": q.category.value,
                "score": 0,
                "hiring_decision": "Skipped",
                "confidence": 0.0,
                "performance_label": "Skipped",
            })
    return rows


def interpret_radar_chart(state: SessionState) -> str:
    """Generate a short text interpretation of the radar chart.

    Deterministic, no LLM.
    """
    dim_avgs = prepare_radar_chart_data(state.evaluations)
    if not dim_avgs:
        return "No evaluation data available for radar interpretation."

    highest_dim = max(dim_avgs, key=lambda d: dim_avgs[d])
    lowest_dim = min(dim_avgs, key=lambda d: dim_avgs[d])
    highest_val = dim_avgs[highest_dim]
    lowest_val = dim_avgs[lowest_dim]
    spread = highest_val - lowest_val

    parts = [
        f"Strongest area: **{highest_dim}** ({highest_val}/10).",
        f"Weakest area: **{lowest_dim}** ({lowest_val}/10).",
    ]
    if spread > 4:
        parts.append("⚠️ Significant imbalance between strongest and weakest areas.")
    elif spread <= 2:
        parts.append("Consistent performance across all areas.")
    parts.append(f"Improving **{lowest_dim}** would most impact overall performance.")
    return " ".join(parts)


def compute_confidence_notice(state: SessionState) -> str:
    """Return a confidence warning if any evaluation had low confidence."""
    for eval_ in state.evaluations.values():
        if eval_.confidence < 0.7:
            return "⚠️ Some answers were ambiguous, so parts of this evaluation have moderate confidence."
    return ""
