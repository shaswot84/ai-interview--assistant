from datetime import datetime, timezone

import chainlit as cl

from export import generate_markdown_transcript, generate_pdf
from llm_client import evaluate_answer, generate_questions, synthesize_scorecard
from schemas import InterviewState, Seniority, SessionState, UserProfile
from scoring import get_letter_grade, prepare_radar_chart_data, render_radar_chart
from session_state import transition
from timer import get_timer_limit, is_timed_out

ONBOARDING_FIELDS = ["role", "seniority", "industry", "interview_type"]
ONBOARDING_PROMPTS = [
    "What is your target **role**? (e.g. Backend Engineer)",
    "What is your **seniority level**? (Junior / Mid / Senior / Lead)",
    "What **industry** do you work in? (e.g. FinTech)",
    "**Interview type**? (technical / behavioural)",
]


def _get_state() -> SessionState:
    return cl.user_session.get("state", SessionState())


def _set_state(state: SessionState) -> None:
    cl.user_session.set("state", state)


@cl.action_callback("skip")
async def on_skip(action: cl.Action):
    state = _get_state()
    state = transition(state, "skip")
    state = transition(state, "evaluation_done")
    _set_state(state)
    await _show_feedback(state)


@cl.action_callback("end_early")
async def on_end_early(action: cl.Action):
    state = _get_state()
    state = transition(state, "end_early")
    _set_state(state)
    await _handle_completed(state)


@cl.action_callback("next_question")
async def on_next_question(action: cl.Action):
    state = _get_state()
    state = transition(state, "next_question")
    _set_state(state)
    await _show_question(state)


@cl.action_callback("finish")
async def on_finish(action: cl.Action):
    state = _get_state()
    state = transition(state, "finish")
    _set_state(state)
    await _handle_completed(state)


@cl.action_callback("export_pdf")
async def on_export_pdf(action: cl.Action):
    state = _get_state()
    path = f"/tmp/interview_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.pdf"
    generate_pdf(state, path)
    await cl.File(path, name="interview_transcript.pdf", display="inline").send()


@cl.action_callback("export_md")
async def on_export_md(action: cl.Action):
    state = _get_state()
    md = generate_markdown_transcript(state)
    path = f"/tmp/interview_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
    with open(path, "w") as f:
        f.write(md)
    await cl.File(path, name="interview_transcript.md", display="inline").send()


@cl.action_callback("retry_evaluation")
async def on_retry_evaluation(action: cl.Action):
    state = _get_state()
    q = state.questions[state.current_question_index]
    answer = state.transcript.get(q.id, "")
    msg = cl.Message(content="Re-evaluating your answer...")
    await msg.send()
    try:
        eval_ = evaluate_answer(q, answer, state.profile)
        state.evaluations[q.id] = eval_
    except Exception:
        from schemas import Evaluation
        eval_ = Evaluation(
            clarity=5, completeness=5, relevance=5, grammar=5, impact=5,
            grammar_correction="", simplified_version="",
            actionable_feedback="Evaluation unavailable due to an error.",
        )
        state.evaluations[q.id] = eval_
    state = transition(state, "evaluation_done")
    _set_state(state)
    await _show_feedback(state)


@cl.action_callback("restart")
async def on_restart(action: cl.Action):
    _set_state(SessionState())
    await cl.Message(
        content="Interview session reset. Type **start** to begin again."
    ).send()


async def _show_onboarding():
    cl.user_session.set("onboarding_idx", 0)
    cl.user_session.set("profile_data", {})
    msg = cl.Message(
        content="Let's set up your interview profile. I'll ask a few questions.",
        actions=[cl.Action(name="cancel", value="cancel", label="Cancel")],
    )
    await msg.send()
    await _ask_next_field()


async def _ask_next_field():
    idx = cl.user_session.get("onboarding_idx", 0)
    if idx < len(ONBOARDING_FIELDS):
        await cl.Message(content=ONBOARDING_PROMPTS[idx]).send()
        cl.user_session.set("onboarding_idx", idx + 1)
    else:
        await _finalize_onboarding()


async def _finalize_onboarding():
    data = cl.user_session.get("profile_data", {})
    seniority_str = data.get("seniority", "").capitalize()
    try:
        seniority = Seniority(seniority_str)
    except ValueError:
        await cl.Message(
            content=f"Invalid seniority '{seniority_str}'. Please try again with Junior, Mid, Senior, or Lead."
        ).send()
        cl.user_session.set("onboarding_idx", 1)
        await _ask_next_field()
        return

    profile = UserProfile(
        role=data.get("role", ""),
        seniority=seniority,
        industry=data.get("industry", ""),
        interview_type=data.get("interview_type", ""),
    )
    state = _get_state()
    state.profile = profile
    state = transition(state, "start")
    state = transition(state, "submit_profile")
    _set_state(state)
    await _handle_generating(state)


async def _handle_generating(state: SessionState):
    msg = cl.Message(content="Generating interview questions...")
    await msg.send()
    questions = generate_questions(state.profile)
    state.questions = questions
    state = transition(state, "questions_ready")
    _set_state(state)
    await _show_question(state)


async def _show_question(state: SessionState):
    if state.current_question_index >= len(state.questions):
        state = transition(state, "finish")
        _set_state(state)
        await _handle_completed(state)
        return

    q = state.questions[state.current_question_index]
    total = len(state.questions)
    idx = state.current_question_index + 1
    timer_limit = get_timer_limit()
    actions = [
        cl.Action(name="skip", value="skip", label="Skip"),
        cl.Action(name="end_early", value="end_early", label="End Early"),
    ]
    await cl.Message(
        content=f"### Question {idx}/{total}\n\n**{q.text}**\n\n*(You have {timer_limit} seconds to answer)*",
        actions=actions,
    ).send()


async def _handle_answer(state: SessionState, answer: str):
    q = state.questions[state.current_question_index]
    state.transcript[q.id] = answer

    if is_timed_out(state):
        await cl.Message(
            content="⏰ **Timer has expired.** Your answer was logged but skipped for evaluation."
        ).send()

    state = transition(state, "submit_answer")
    _set_state(state)

    msg = cl.Message(content="Evaluating your answer...")
    await msg.send()
    eval_failed = False
    try:
        eval_ = evaluate_answer(q, answer, state.profile)
        state.evaluations[q.id] = eval_
    except Exception:
        from schemas import Evaluation
        eval_ = Evaluation(
            clarity=5, completeness=5, relevance=5, grammar=5, impact=5,
            grammar_correction="", simplified_version="",
            actionable_feedback="Evaluation unavailable due to an error.",
        )
        state.evaluations[q.id] = eval_
        eval_failed = True

    state = transition(state, "evaluation_done")
    _set_state(state)
    if eval_failed:
        await cl.Message(
            content="Evaluation encountered an error. You can try again below.",
            actions=[cl.Action(name="retry_evaluation", value="retry", label="Retry Evaluation")],
        ).send()
    await _show_feedback(state)


async def _show_feedback(state: SessionState):
    q = state.questions[state.current_question_index]
    eval_ = state.evaluations.get(q.id)
    is_last = state.current_question_index >= len(state.questions) - 1

    if eval_ is None:
        content = f"**Question skipped.**\n\n_{q.text}_"
        actions = []
        if is_last:
            actions.append(cl.Action(name="finish", value="finish", label="Finish"))
        else:
            actions.append(cl.Action(name="next_question", value="next_question", label="Next Question"))
        actions.append(cl.Action(name="end_early", value="end_early", label="End Early"))
        await cl.Message(content=content, actions=actions).send()
        return

    from scoring import calculate_question_score
    total = calculate_question_score(eval_)
    content = (
        f"### Feedback\n\n"
        f"**Question:** {q.text}\n\n"
        f"**Overall Score:** {total}/100\n\n"
        f"| Dimension | Score |\n"
        f"|-----------|-------|\n"
        f"| Clarity | {eval_.clarity}/10 |\n"
        f"| Completeness | {eval_.completeness}/10 |\n"
        f"| Relevance | {eval_.relevance}/10 |\n"
        f"| Grammar | {eval_.grammar}/10 |\n"
        f"| Impact | {eval_.impact}/10 |\n\n"
    )
    if eval_.actionable_feedback:
        content += f"**Actionable Feedback:** {eval_.actionable_feedback}\n\n"
    if eval_.grammar_correction:
        content += f"**Grammar Correction:** {eval_.grammar_correction}\n\n"
    if eval_.simplified_version:
        content += f"**Simplified Version:** {eval_.simplified_version}"

    actions = []
    if is_last:
        actions.append(cl.Action(name="finish", value="finish", label="Finish"))
    else:
        actions.append(cl.Action(name="next_question", value="next_question", label="Next Question"))
    actions.append(cl.Action(name="end_early", value="end_early", label="End Early"))

    await cl.Message(content=content, actions=actions).send()


async def _handle_completed(state: SessionState):
    msg = cl.Message(content="Generating your final scorecard...")
    await msg.send()
    try:
        sc = synthesize_scorecard(state)
        state.scorecard = sc
    except Exception:
        from schemas import Scorecard
        sc = Scorecard(
            strengths=["Interview completed"],
            improvements=[],
            model_answer="",
            overall_assessment="Scorecard generation was unavailable.",
            grade=get_letter_grade(0),
        )
        state.scorecard = sc

    state = transition(state, "show_debrief")
    _set_state(state)

    await _show_scorecard(state)


async def _show_scorecard(state: SessionState):
    sc = state.scorecard
    if sc is None:
        return

    overall = sc.overall_assessment
    content = (
        f"# 🏆 Interview Complete\n\n"
        f"**Final Grade:** {sc.grade.value}\n\n"
        f"**Overall Assessment:** {overall}\n\n"
    )
    if sc.strengths:
        content += "### Strengths\n"
        for s in sc.strengths:
            content += f"- {s}\n"
        content += "\n"
    if sc.improvements:
        content += "### Areas for Improvement\n"
        for s in sc.improvements:
            content += f"- {s}\n"
        content += "\n"
    if sc.model_answer:
        content += "### Model Answer Summary\n"
        content += f"{sc.model_answer}\n\n"

    evaluations = state.evaluations
    if evaluations:
        radar_data = prepare_radar_chart_data(evaluations)
        fig = render_radar_chart(radar_data)
        await cl.Message(content=content).send()
        await cl.Plotly(name="radar_chart", figure=fig, display="inline").send()
    else:
        await cl.Message(content=content).send()

    actions = [
        cl.Action(name="export_pdf", value="export_pdf", label="Download PDF"),
        cl.Action(name="export_md", value="export_md", label="Download Markdown"),
        cl.Action(name="restart", value="restart", label="Start New Interview"),
    ]
    await cl.Message(content="What would you like to do next?", actions=actions).send()


@cl.on_chat_start
async def on_chat_start():
    _set_state(SessionState())
    await cl.Message(
        content="👋 Welcome to **AI Interview Assistant**!\n\n"
        "I'll conduct a personalised mock interview and provide detailed feedback.\n\n"
        "Type **start** to begin."
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    state = _get_state()
    text = message.content.strip()

    if state.current_state == InterviewState.IDLE:
        if text.lower() == "start":
            await _show_onboarding()
        else:
            await cl.Message(content="Type **start** to begin your interview.").send()

    elif state.current_state == InterviewState.ONBOARDING:
        idx = cl.user_session.get("onboarding_idx", 0)
        if not text:
            await cl.Message(content="Please enter a value.").send()
            await _ask_next_field()
            return
        data = cl.user_session.get("profile_data", {})
        field = ONBOARDING_FIELDS[idx - 1]
        data[field] = text
        cl.user_session.set("profile_data", data)
        await _ask_next_field()

    elif state.current_state == InterviewState.INTERVIEWING:
        if not text:
            await cl.Message(content="Please enter your answer.").send()
            return
        await _handle_answer(state, text)
