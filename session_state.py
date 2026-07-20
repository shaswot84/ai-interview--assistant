"""State machine — guards all session state transitions with a whitelist of valid moves."""

from __future__ import annotations

from datetime import datetime, timezone

from schemas import InterviewState, SessionState
from timer import is_timed_out


class InvalidTransitionError(ValueError):
    """Raised when an action is not allowed from the current state."""


VALID_TRANSITIONS: dict[InterviewState, list[tuple[str, InterviewState]]] = {
    InterviewState.IDLE: [("start", InterviewState.ONBOARDING)],
    InterviewState.ONBOARDING: [("submit_profile", InterviewState.GENERATING)],
    InterviewState.GENERATING: [("questions_ready", InterviewState.INTERVIEWING)],
    InterviewState.INTERVIEWING: [
        ("submit_answer", InterviewState.EVALUATING),
        ("skip", InterviewState.EVALUATING),
        ("timeout_skip", InterviewState.EVALUATING),
        ("end_early", InterviewState.COMPLETED),
    ],
    InterviewState.EVALUATING: [("evaluation_done", InterviewState.FEEDBACK)],
    InterviewState.FEEDBACK: [
        ("next_question", InterviewState.INTERVIEWING),
        ("finish", InterviewState.COMPLETED),
        ("end_early", InterviewState.COMPLETED),
    ],
    InterviewState.COMPLETED: [("show_debrief", InterviewState.DEBRIEF)],
    InterviewState.DEBRIEF: [],
}


def transition(state: SessionState, action: str) -> SessionState:
    """Return a deep-copied SessionState after applying `action`.
    
    Automatically converts `submit_answer` to `timeout_skip` if the question
    timer has expired. Raises InvalidTransitionError if the action is not
    listed in VALID_TRANSITIONS for the current state.
    """
    if (
        state.current_state == InterviewState.INTERVIEWING
        and action == "submit_answer"
        and is_timed_out(state)
    ):
        action = "timeout_skip"

    allowed = VALID_TRANSITIONS.get(state.current_state, [])
    for act, next_state in allowed:
        if act == action:
            new_state = state.model_copy(deep=True)
            new_state.current_state = next_state
            if next_state == InterviewState.INTERVIEWING:
                new_state.question_started_at = datetime.now(timezone.utc)
            return new_state

    raise InvalidTransitionError(
        f"No valid transition from {state.current_state} with action '{action}'"
    )
