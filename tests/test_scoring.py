"""Tests for the scoring engine — weighted scores, letter grades, radar chart data."""

import pytest
from schemas import Evaluation, LetterGrade
from scoring import (
    calculate_question_score,
    calculate_overall_score,
    get_letter_grade,
    prepare_radar_chart_data,
    render_radar_chart,
)


def _eval(scores: dict[str, int]) -> Evaluation:
    """Helper — build an Evaluation with the given scores and empty strings."""
    return Evaluation(
        scores=scores,
        strengths=[],
        weaknesses=[],
        grammar_correction="",
        simplified_version="",
        actionable_feedback="",
    )


class TestCalculateQuestionScore:
    """Verify scoring produces correct results for edge and middle values."""

    def test_all_max_returns_100(self):
        e = _eval({"clarity": 10, "correctness": 10, "depth": 10})
        assert calculate_question_score(e) == 100.0

    def test_all_min_returns_10(self):
        e = _eval({"clarity": 1, "correctness": 1, "depth": 1})
        assert calculate_question_score(e) == 10.0

    def test_mid_range(self):
        e = _eval({"clarity": 5, "correctness": 5, "depth": 5})
        assert calculate_question_score(e) == 50.0

    def test_single_dimension(self):
        e = _eval({"correctness": 7})
        assert calculate_question_score(e) == 70.0

    def test_empty_scores(self):
        e = _eval({})
        assert calculate_question_score(e) == 0.0


class TestCalculateOverallScore:
    """Overall score averages individual question scores."""

    def test_average_of_multiple(self):
        evals = {
            "q1": _eval({"clarity": 5, "correctness": 5}),
            "q2": _eval({"clarity": 10, "correctness": 10}),
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
            "q1": _eval({"clarity": 10, "correctness": 8, "depth": 5}),
        }
        data = prepare_radar_chart_data(evals)
        assert data["clarity"] == 10.0
        assert data["correctness"] == 8.0
        assert data["depth"] == 5.0

    def test_merges_different_dimension_sets(self):
        evals = {
            "q1": _eval({"clarity": 8, "correctness": 7}),
            "q2": _eval({"correctness": 6, "solution_quality": 9}),
        }
        data = prepare_radar_chart_data(evals)
        assert data["clarity"] == 8.0
        assert data["correctness"] == 6.5
        assert data["solution_quality"] == 9.0

    def test_returns_empty_for_empty(self):
        data = prepare_radar_chart_data({})
        assert data == {}


class TestRenderRadarChart:
    """render_radar_chart should return a Plotly Figure with data."""

    def test_returns_figure(self):
        data = {"clarity": 8.0, "correctness": 7.0, "depth": 9.0}
        fig = render_radar_chart(data)
        assert fig.data is not None
        assert len(fig.data) > 0

    def test_empty_data_does_not_crash(self):
        fig = render_radar_chart({})
        assert fig.data is not None
