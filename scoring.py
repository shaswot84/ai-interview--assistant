"""Scoring engine — weighted question scores, letter grades, and Plotly radar charts."""

import plotly.graph_objects as go
import plotly.io as pio

from schemas import Evaluation, LetterGrade

# Weight distribution for the five evaluation dimensions
WEIGHTS = {
    "clarity": 0.15,
    "completeness": 0.25,
    "relevance": 0.20,
    "grammar": 0.10,
    "impact": 0.30,
}

# Ordered list of dimension keys (used for radar chart labels)
DIMENSIONS = ["clarity", "completeness", "relevance", "grammar", "impact"]


def calculate_question_score(eval_: Evaluation) -> float:
    """Compute a weighted score (0–100) for a single evaluation."""
    score = (
        eval_.clarity * WEIGHTS["clarity"]
        + eval_.completeness * WEIGHTS["completeness"]
        + eval_.relevance * WEIGHTS["relevance"]
        + eval_.grammar * WEIGHTS["grammar"]
        + eval_.impact * WEIGHTS["impact"]
    )
    return round(score * 10, 1)


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
    """Average each dimension across all evaluations for the radar chart."""
    if not evaluations:
        return {d: 0.0 for d in DIMENSIONS}
    totals = {d: 0.0 for d in DIMENSIONS}
    for e in evaluations.values():
        totals["clarity"] += e.clarity
        totals["completeness"] += e.completeness
        totals["relevance"] += e.relevance
        totals["grammar"] += e.grammar
        totals["impact"] += e.impact
    n = len(evaluations)
    return {d: round(totals[d] / n, 1) for d in DIMENSIONS}


def render_radar_chart(data: dict[str, float]) -> go.Figure:
    """Render a Plotly polar radar chart from averaged dimension scores."""
    labels = [d.capitalize() for d in DIMENSIONS]
    values = [data.get(d, 0) for d in DIMENSIONS]
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
