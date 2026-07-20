"""Tests for the scoring engine — weighted scores, letter grades, radar chart data."""

import pytest
from schemas import Evaluation, LetterGrade
from scoring import (
    DIMENSIONS,
    calculate_question_score,
    calculate_overall_score,
    get_letter_grade,
    prepare_radar_chart_data,
    render_radar_chart,
)


def _eval(
    clarity=5, completeness=5, relevance=5, grammar=5, impact=5,
    technical_depth=5, architecture_design=5, problem_solving=5, tradeoff_analysis=5,
) -> Evaluation:
    """Helper — build an Evaluation with the given scores and empty strings."""
    return Evaluation(
        clarity=clarity,
        completeness=completeness,
        relevance=relevance,
        grammar=grammar,
        impact=impact,
        technical_depth=technical_depth,
        architecture_design=architecture_design,
        problem_solving=problem_solving,
        tradeoff_analysis=tradeoff_analysis,
        strengths=[],
        weaknesses=[],
        grammar_correction="",
        simplified_version="",
        actionable_feedback="",
    )


class TestCalculateQuestionScore:
    """Verify weighted scoring produces correct results for edge and middle values."""

    def test_all_max_returns_100(self):
        e = _eval(clarity=10, completeness=10, relevance=10, grammar=10, impact=10,
                  technical_depth=10, architecture_design=10, problem_solving=10, tradeoff_analysis=10)
        assert calculate_question_score(e) == 100.0

    def test_all_min_returns_10(self):
        e = _eval(clarity=1, completeness=1, relevance=1, grammar=1, impact=1,
                  technical_depth=1, architecture_design=1, problem_solving=1, tradeoff_analysis=1)
        assert calculate_question_score(e) == 10.0

    def test_mid_range(self):
        e = _eval(clarity=5, completeness=5, relevance=5, grammar=5, impact=5,
                  technical_depth=5, architecture_design=5, problem_solving=5, tradeoff_analysis=5)
        assert calculate_question_score(e) == 50.0

    def test_weights_are_correct(self):
        e = _eval(clarity=10, completeness=1, relevance=1, grammar=1, impact=1,
                  technical_depth=1, architecture_design=1, problem_solving=1, tradeoff_analysis=1)
        score = calculate_question_score(e)
        assert score == pytest.approx(10 * 10 * 0.10 + 1 * 10 * 0.90, rel=0.1)


class TestCalculateOverallScore:
    """Overall score averages individual question scores."""

    def test_average_of_multiple(self):
        evals = {
            "q1": _eval(clarity=5, completeness=5, relevance=5, grammar=5, impact=5,
                        technical_depth=5, architecture_design=5, problem_solving=5, tradeoff_analysis=5),
            "q2": _eval(clarity=10, completeness=10, relevance=10, grammar=10, impact=10,
                        technical_depth=10, architecture_design=10, problem_solving=10, tradeoff_analysis=10),
        }
        assert calculate_overall_score(evals) == 75.0

    def test_zero_when_empty(self):
        assert calculate_overall_score({}) == 0.0


class TestGetLetterGrade:
    """Letter grade boundaries: A≥90, B≥80, C≥70, D≥60, F<60."""

    def test_a_grade(self):
        assert get_letter_grade(95) == LetterGrade.A

    def test_b_grade(self):
        assert get_letter_grade(85) == LetterGrade.B

    def test_c_grade(self):
        assert get_letter_grade(75) == LetterGrade.C

    def test_d_grade(self):
        assert get_letter_grade(65) == LetterGrade.D

    def test_f_grade(self):
        assert get_letter_grade(55) == LetterGrade.F

    def test_boundaries(self):
        assert get_letter_grade(90) == LetterGrade.A
        assert get_letter_grade(89.9) == LetterGrade.B
        assert get_letter_grade(80) == LetterGrade.B
        assert get_letter_grade(70) == LetterGrade.C
        assert get_letter_grade(60) == LetterGrade.D


class TestPrepareRadarChartData:
    """Radar chart data averages each dimension across all evaluations."""

    def test_returns_averages(self):
        evals = {
            "q1": _eval(clarity=10, completeness=8, relevance=6, grammar=4, impact=2,
                        technical_depth=3, architecture_design=5, problem_solving=7, tradeoff_analysis=9),
        }
        data = prepare_radar_chart_data(evals)
        assert data["clarity"] == 10.0
        assert data["completeness"] == 8.0
        assert data["relevance"] == 6.0
        assert data["grammar"] == 4.0
        assert data["impact"] == 2.0
        assert data["technical_depth"] == 3.0
        assert data["architecture_design"] == 5.0
        assert data["problem_solving"] == 7.0
        assert data["tradeoff_analysis"] == 9.0

    def test_returns_zeros_for_empty(self):
        data = prepare_radar_chart_data({})
        for d in DIMENSIONS:
            assert data[d] == 0.0


class TestRenderRadarChart:
    """render_radar_chart should return a Plotly Figure with data."""

    def test_returns_figure(self):
        data = {
            "clarity": 8.0, "completeness": 7.0, "relevance": 9.0, "grammar": 6.0, "impact": 8.0,
            "technical_depth": 7.0, "architecture_design": 8.0, "problem_solving": 9.0, "tradeoff_analysis": 6.0,
        }
        fig = render_radar_chart(data)
        assert fig.data is not None
        assert len(fig.data) > 0
