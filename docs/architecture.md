# Architecture

## Overview
Single-page Chainlit app driven by a server-side state machine. Each state maps to a UI screen. LLM calls go through an OpenAI-compatible client with retry logic and a static fallback question bank.

## System Flow
```
┌──────────┐    ┌────────────┐    ┌───────────┐    ┌────────────┐
│  User    │───▶│ Chainlit   │───▶│  State    │───▶│  LLM       │
│  Input   │    │  UI        │    │  Machine  │    │  Client    │
└──────────┘    └────────────┘    └───────────┘    └─────┬──────┘
                                                         │
                                              ┌──────────▼──────────┐
                                              │  OpenAI SDK          │
                                              │  (Groq/DeepSeek/etc) │
                                              └──────────┬──────────┘
                                                         │
                                    ┌────────────────────▼──────────────┐
                                    │  Fallback Data (on API failure)   │
                                    └───────────────────────────────────┘

                    ┌──────────┐    ┌───────────────┐    ┌────────────┐
                    │  Timer   │───▶│  Scoring      │───▶│  Export    │
                    │  (auto)  │    │  Engine       │    │  PDF/MD   │
                    └──────────┘    └───────────────┘    └────────────┘
```

## State Machine
```
                        ┌──────────────────────────────────────┐
                        │                                      │
                        ▼                                      │
  IDLE ──▶ ONBOARDING ──▶ GENERATING ──▶ INTERVIEWING ──▶ EVALUATING ──▶ FEEDBACK
                                                                          │     │
                                                          last question ──┘     │ next question
                                                                                ▼
                                                                          COMPLETED ──▶ DEBRIEF
```

### Transition Rules
| From | Action | To | Guard |
|------|--------|----|-------|
| IDLE | start | ONBOARDING | Always |
| ONBOARDING | submit_profile | GENERATING | Profile valid |
| GENERATING | questions_ready | INTERVIEWING | Questions generated |
| INTERVIEWING | submit_answer | EVALUATING | Answer non-empty, timer OK |
| INTERVIEWING | timeout_skip | EVALUATING | Timer expired |
| INTERVIEWING | skip | EVALUATING | Always |
| EVALUATING | evaluation_done | FEEDBACK | Evaluation stored |
| FEEDBACK | next_question | INTERVIEWING | More questions remain |
| FEEDBACK | end_early | COMPLETED | Always |
| FEEDBACK | finish | COMPLETED | Last question done |
| COMPLETED | show_debrief | DEBRIEF | Scorecard generated |

## Components

### 1. Config Layer (`config.py`)
Env-based configuration loaded once at startup via `Config.from_env()`. Provides API keys, model name, base URL, timer setting, and per-operation LLM temperatures.

**Chainlit config** (`.chainlit/config.toml`): UI-level settings including `unsafe_allow_html = true` (needed to render HTML/CSS elements like the countdown timer bar in message content).

### 2. State Machine (`session_state.py`)
- `SessionState` dataclass holding current state, profile, questions, answers, evaluations
- `transition(state, action)` — guarded transitions with `InvalidTransitionError`
- Timer check on `INTERVIEWING` state: auto-skip if expired

### 3. LLM Integration (`llm_client.py` + `providers.py`)
- `get_openai_client()` — returns configured OpenAI SDK client
- `_call_with_retry()` — up to 2 retries with exponential backoff
- `validate_role(role)` — LLM classifies whether a role is IT-related
- `generate_questions(profile, question_config=None)` — tries LLM with optional `QuestionConfig` for type distribution; falls back to static question bank
- `evaluate_answer(...)` — dispatches by `question.question_type`: `mcq`/`yes_no` → deterministic `_evaluate_objective()`, all others → `_evaluate_llm()` with `INJECTION_GUARD` and score clamping (1-10)
- `synthesize_scorecard(state)` — returns `Scorecard` from full transcript

### 4. Prompts (`prompts.py`)
- `SENIORITY_PERSONAS` — per-level focus areas dict (junior/mid/senior/lead) injected into the question gen prompt
- `QUESTION_GEN_PROMPT` — template with `{distribution_instructions}` and `{question_type_example}` placeholders for dynamic type distribution
- `QUESTION_TYPE_DESCRIPTIONS` — field requirements per question type (open_ended, behavioral, mcq, yes_no, coding, debugging, system_design)
- `QUESTION_TYPE_DISTRIBUTION_TEMPLATE` — generates per-type distribution instructions for the LLM
- `get_question_prompt(profile, config=None)` — builds the question gen system prompt; when `config` is provided, includes type-distribution block instead of the default 3-tech/2-behav ratio
- `INJECTION_GUARD` — system-level instruction to ignore score-manipulation attempts in answer text
- `QUESTION_TYPE_GUIDANCE` — per-type evaluation guidance dict (open_ended, behavioral, coding, debugging, system_design)
- `TYPE_DIMENSIONS` — per-type dimension sets with descriptions (e.g., open_ended has clarity/completeness/relevance/correctness/technical_depth/problem_solving/tradeoff_analysis; coding has correctness/solution_quality/technical_depth/problem_solving)
- `TYPE_OUTPUT_FIELDS` — per-type JSON template injected into the EVALUATION_PROMPT's RETURN FORMAT section
- `EVALUATION_PROMPT` — unified template with `question_type`, `question_type_guidance`, `type_dimensions`, and `type_output_fields` placeholders; dimensions are dynamic per type
- `SCORECARD_PROMPT` — strengths, improvements, model answer

### 5. Timer (`timer.py`)
- `get_timer_limit()` — reads `QUESTION_TIMER_SECONDS` (env), default `180`
- `check_elapsed_time(state)` — seconds since `question_started_at`
- `is_timed_out(state)` — `elapsed > limit`
- **Visual countdown bar** (injected into each question message via `app.py:_timer_bar_html()`): pure-CSS animation shrinking from 100%→0% width in blue (`#3B82F6`); turns red (`#EF4444`) with a blink effect when 80% of the timer has elapsed

### 6. Scoring (`scoring.py`)
- `calculate_question_score(eval)` → equal-weighted average of all present dimension scores × 10 → 0-100
- `calculate_overall_score(transcript)` → average of non-skipped
- `get_letter_grade(score)` → A≥90, B≥80, C≥70, D≥60, F<60
- `prepare_radar_chart_data(transcript)` — collects all unique dimension keys across evaluations, averages per key (divided by count of evaluations containing that key, not total evaluations)
- `render_radar_chart(data)` → Plotly figure (dynamically adapts labels to whatever keys exist in data)

### 7. Export (`export.py`)
- `generate_markdown_transcript(state)` — full Q&A as Markdown
- `generate_pdf(state, path)` — convert Markdown to PDF via WeasyPrint

### 8. Fallback (`fallback_data.py`)
- 10 questions per seniority level (Junior, Mid, Senior, Lead)
- `fallback_questions(profile, needed, question_config=None)` — returns questions distributed by type when API fails; default fallback is 3 technical + 2 behavioural

### 9. Schemas (`schemas.py`)
Pydantic v2 models:
- `UserProfile` — role, seniority, industry, interview_type (hardcoded to "technical")
- `Question` — id, text, category, question_type (open_ended|behavioral|mcq|yes_no|coding|debugging|system_design), difficulty, expected_keywords, plus optional fields: options, correct_answer, starter_code, language, evaluation_type, buggy_code, expected_fix, evaluation_focus
- `QuestionConfig` — total_questions (default 5), distribution (map of QuestionType to percentage), with `counts()` method
- `Evaluation` — `scores: dict[str, int]` (dynamic dimensions per question type, each validated 1-10); plus strengths, weaknesses, grammar_correction, simplified_version, actionable_feedback
- `Scorecard` — per-question scores, overall, letter grade, radar data
- `SessionState` — current state, profile, questions, transcript, evaluations, scorecard

### 10. UI (`app.py`)
Chainlit callbacks mapped to state machine actions:
- `Submit` → `evaluate_answer()` → show Feedback
- `Skip` → transition to EVALUATING → FEEDBACK (no evaluation)
- `End Early` → jump to COMPLETED → scorecard
- `Next Question` → advance index, show next question
- `Finish` → trigger scorecard → DEBRIEF
- `Export` → download PDF or Markdown transcript
- `Restart` → reset session
- `Config Done` → trigger question generation with current `QuestionConfig`

**Interactive question rendering (`_show_question`):**
- Questions are displayed as a two-part message:
  1. A permanent `cl.Message` with the question text, timer bar, and formatted code (if applicable) — this message stays visible regardless of button interaction
  2. A separate `cl.AskActionMessage` containing only the action/answer buttons — blocks the UI thread until the user clicks, preventing Chainlit from disabling buttons
- **MCQ** — When `question_type == QuestionType.MCQ` and `options` is populated, renders 4 clickable option buttons via the `AskActionMessage`. The selected option value is submitted as the answer.
- **Yes/No** — When `question_type == QuestionType.YES_NO`, renders **Yes** and **No** buttons via the `AskActionMessage`.
- **Open-ended, behavioral, system design** — Renders the question as plain text with "Answer" button (triggers `AskUserMessage`), plus Skip and End Early buttons.
- **Coding** — When `question_type == QuestionType.CODING` with `starter_code`, renders the starter code in a fenced Markdown code block with syntax highlighting (` ```{language} `) in the permanent message.
- **Debugging** — When `question_type == QuestionType.DEBUGGING` with `buggy_code`, renders the buggy code in a fenced code block in the permanent message.
- All question types display the countdown timer bar and Skip/End Early controls.

**Feedback (`_show_feedback`):**
- Uses `cl.AskActionMessage` with inline action handling (rather than registering separate `@cl.action_callback` handlers) — this ensures all feedback buttons remain clickable.
- Accepts an optional `eval_failed` parameter to display error-state feedback with a retry option.
- Retry calls `_handle_retry()` helper which re-runs `evaluate_answer()` in a thread.

**Onboarding flow:** role (IT-validated via LLM) → seniority (4-button picker) → industry → **question config** (gated settings panel with total count + per-type percentage sliders → "Generate Questions" button) → question generation → interview.

**Settings panel** — `_build_question_settings()` returns a `cl.ChatSettings` with `NumberInput` (total questions, 1-20) and `Slider` widgets for 6 question types (Technical Open-ended, Behavioral STAR, MCQ, Coding, Debugging, System Design). Percentages are normalized to sum to 100%. Changes are captured by `@cl.on_settings_update` and stored as `QuestionConfig` in the user session.

**IT role validation** — `validate_role()` queries the LLM to classify whether the entered role is IT-related; loops until a valid IT role is provided.

Synchronous LLM calls (`generate_questions`, `evaluate_answer`) are offloaded with `await asyncio.to_thread(...)` to prevent blocking the Chainlit event loop (which would freeze the chat input on "Stop task").
