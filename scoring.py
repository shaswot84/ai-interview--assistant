"""Scoring engine — weighted question scores, letter grades, and Plotly radar charts."""

import plotly.graph_objects as go
import plotly.io as pio

from schemas import Evaluation, LetterGrade


def calculate_question_score(eval_: Evaluation) -> float:
    """Compute an overall score (0–100) from the average of all dimension scores."""
    dims = eval_.scores
    if not dims:
        return 0.0
    avg = sum(dims.values()) / len(dims)
    return round(avg * 10, 1)


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
