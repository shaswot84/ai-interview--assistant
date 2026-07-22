"""Scoring engine — weighted question scores, letter grades, and Plotly radar charts."""

import plotly.graph_objects as go
import plotly.io as pio

from schemas import Evaluation, LetterGrade

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
