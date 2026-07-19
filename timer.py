from datetime import datetime, timezone

from config import config
from schemas import SessionState


def get_timer_limit() -> int:
    return config.question_timer_seconds


def check_elapsed_time(state: SessionState) -> float:
    if state.question_started_at is None:
        return 0.0
    return (datetime.now(timezone.utc) - state.question_started_at).total_seconds()


def is_timed_out(state: SessionState) -> bool:
    return check_elapsed_time(state) > get_timer_limit()
