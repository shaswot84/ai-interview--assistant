from datetime import datetime, timedelta, timezone

import pytest

from schemas import SessionState
from timer import check_elapsed_time, get_timer_limit, is_timed_out


class TestCheckElapsedTime:
    def test_zero_when_no_start(self):
        state = SessionState()
        assert check_elapsed_time(state) == 0.0

    def test_returns_positive_seconds_when_started(self):
        state = SessionState(
            question_started_at=datetime.now(timezone.utc) - timedelta(seconds=5)
        )
        elapsed = check_elapsed_time(state)
        assert 4.0 <= elapsed <= 6.0


class TestIsTimedOut:
    def test_false_within_limit(self):
        state = SessionState(
            question_started_at=datetime.now(timezone.utc) - timedelta(seconds=1)
        )
        assert is_timed_out(state) is False

    def test_true_over_limit(self):
        limit = get_timer_limit()
        state = SessionState(
            question_started_at=datetime.now(timezone.utc) - timedelta(seconds=limit + 10)
        )
        assert is_timed_out(state) is True

    def test_false_when_no_start(self):
        state = SessionState()
        assert is_timed_out(state) is False


class TestGetTimerLimit:
    def test_returns_positive_int(self):
        limit = get_timer_limit()
        assert isinstance(limit, int)
        assert limit > 0
