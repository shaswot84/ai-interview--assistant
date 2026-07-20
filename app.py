import asyncio
from datetime import datetime, timezone

import chainlit as cl

from export import generate_markdown_transcript, generate_pdf
from llm_client import evaluate_answer, generate_questions, synthesize_scorecard
from schemas import InterviewState, Seniority, SessionState, UserProfile
from scoring import get_letter_grade, prepare_radar_chart_data, render_radar_chart
from session_state import transition
from timer import get_timer_limit, is_timed_out

ONBOARDING_FIELDS = ["role", "seniority", "industry"]
ONBOARDING_PROMPTS = [
    "What is your target **role**? (e.g. Backend Engineer)",
    "What is your **seniority level**? (Junior / Mid / Senior / Lead)",
    "What **industry** do you work in? (e.g. FinTech)",
]


def _timer_bar_html(seconds: int) -> str:
    blink_delay = seconds * 0.8
    return f"""<div style="margin:8px 0;">
  <div style="background:#e5e7eb;border-radius:6px;overflow:hidden;height:14px;">
    <div style="height:100%;border-radius:6px;background:#3B82F6;width:100%;animation:__tShrink {seconds}s linear forwards,__tBlink 0.6s step-end {blink_delay}s infinite;"></div>
  </div>
</div>
<style>
@keyframes __tShrink{{to{{width:0%}}}}
@keyframes __tBlink{{0%,100%{{background:#EF4444;opacity:1}}50%{{opacity:0.15}}}}
</style>"""


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
    state.current_question_index += 1
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
    await cl.Message(content="", elements=[cl.File(path=path, name="interview_transcript.pdf")]).send()


@cl.action_callback("export_md")
async def on_export_md(action: cl.Action):
    state = _get_state()
    md = generate_markdown_transcript(state)
    path = f"/tmp/interview_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
    with open(path, "w") as f:
        f.write(md)
    await cl.Message(content="", elements=[cl.File(path=path, name="interview_transcript.md")]).send()


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
    _set_state(state)
    await _show_feedback(state)


@cl.action_callback("restart")
async def on_restart(action: cl.Action):
    _set_state(SessionState())
    await cl.Message(content="Starting a new interview session...").send()
    await _run_interview_core()


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
        cl.Action(name="skip", payload={}, label="Skip"),
        cl.Action(name="end_early", payload={}, label="End Early"),
    ]
    timer_bar = _timer_bar_html(timer_limit)
    await cl.Message(
        content=f"### Question {idx}/{total}\n\n**{q.text}**\n\n{timer_bar}",
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
        eval_ = await asyncio.to_thread(evaluate_answer, q, answer, state.profile)
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
            actions=[cl.Action(name="retry_evaluation", payload={}, label="Retry Evaluation")],
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
            actions.append(cl.Action(name="finish", payload={}, label="Finish"))
        else:
            actions.append(cl.Action(name="next_question", payload={}, label="Next Question"))
        actions.append(cl.Action(name="end_early", payload={}, label="End Early"))
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
        actions.append(cl.Action(name="finish", payload={}, label="Finish"))
    else:
        actions.append(cl.Action(name="next_question", payload={}, label="Next Question"))
    actions.append(cl.Action(name="end_early", payload={}, label="End Early"))

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
        await cl.Message(content=content, elements=[cl.Plotly(name="radar_chart", figure=fig)]).send()
    else:
        await cl.Message(content=content).send()

    actions = [
        cl.Action(name="export_pdf", payload={}, label="Download PDF"),
        cl.Action(name="export_md", payload={}, label="Download Markdown"),
        cl.Action(name="restart", payload={}, label="Start New Interview"),
    ]
    await cl.Message(content="What would you like to do next?", actions=actions).send()


@cl.on_chat_start
async def on_chat_start():
    _set_state(SessionState())
    await cl.Message(
        content="👋 Welcome to **AI Interview Assistant**!\n\n"
        "I'll conduct a personalised mock interview and provide detailed feedback.\n\n"
        "Let's start by setting up your profile.",
    ).send()
    await _run_interview_core()


async def _run_interview_core():
    state = _get_state()
    state = transition(state, "start")
    _set_state(state)

    data: dict[str, str] = {}
    for idx, field in enumerate(ONBOARDING_FIELDS):
        if field == "seniority":
            res = await cl.AskActionMessage(
                content="What is your **seniority level**?",
                actions=[
                    cl.Action(name="seniority", payload={"value": "Junior"}, label="Junior"),
                    cl.Action(name="seniority", payload={"value": "Mid"}, label="Mid"),
                    cl.Action(name="seniority", payload={"value": "Senior"}, label="Senior"),
                    cl.Action(name="seniority", payload={"value": "Lead"}, label="Lead"),
                ],
            ).send()
            data[field] = res["payload"]["value"] if res else ""
        else:
            res = await cl.AskUserMessage(content=ONBOARDING_PROMPTS[idx]).send()
            if res:
                val = res["output"].strip()
                if not val:
                    await cl.Message(content="Please enter a value.").send()
                    return
                data[field] = val
            else:
                data[field] = ""

    try:
        seniority = Seniority(data.get("seniority", ""))
    except ValueError:
        await cl.Message(content="Invalid seniority. Please try again.").send()
        return

    profile = UserProfile(
        role=data.get("role", ""),
        seniority=seniority,
        industry=data.get("industry", ""),
        interview_type="technical",
    )
    state = _get_state()
    state.profile = profile
    state = transition(state, "submit_profile")
    _set_state(state)

    msg = cl.Message(content="Generating interview questions...")
    await msg.send()
    try:
        questions = await asyncio.to_thread(generate_questions, profile)
        state.questions = questions
        state = transition(state, "questions_ready")
        _set_state(state)
        await _show_question(state)
    except Exception:
        await cl.Message(content="Failed to generate questions. Please try again.").send()


@cl.on_message
async def on_message(message: cl.Message):
    state = _get_state()
    text = message.content.strip()

    if state.current_state == InterviewState.IDLE:
        await cl.Message(
            content="Setting up your interview profile... please wait."
        ).send()

    elif state.current_state == InterviewState.INTERVIEWING:
        if not text:
            await cl.Message(content="Please enter your answer.").send()
            return
        await _handle_answer(state, text)
