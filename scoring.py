import plotly.graph_objects as go
import plotly.io as pio

from schemas import Evaluation, LetterGrade

WEIGHTS = {
    "clarity": 0.15,
    "completeness": 0.25,
    "relevance": 0.20,
    "grammar": 0.10,
    "impact": 0.30,
}

DIMENSIONS = ["clarity", "completeness", "relevance", "grammar", "impact"]


def calculate_question_score(eval_: Evaluation) -> float:
    score = (
        eval_.clarity * WEIGHTS["clarity"]
        + eval_.completeness * WEIGHTS["completeness"]
        + eval_.relevance * WEIGHTS["relevance"]
        + eval_.grammar * WEIGHTS["grammar"]
        + eval_.impact * WEIGHTS["impact"]
    )
    return round(score * 10, 1)


def calculate_overall_score(evaluations: dict[str, Evaluation]) -> float:
    if not evaluations:
        return 0.0
    scores = [calculate_question_score(e) for e in evaluations.values()]
    return round(sum(scores) / len(scores), 1)


def get_letter_grade(score: float) -> LetterGrade:
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
