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
- `get_openai_client()` — returns OpenAI SDK client for Groq/OpenAI (used by question gen, evaluation, scorecard)
- `get_ollama_client()` — returns OpenAI-compatible client pointed at the Ollama endpoint (used by guardrails)
- `_call_with_retry()` — up to 2 retries with exponential backoff (OpenAI client only); logs the raw Groq response at INFO level before Pydantic validation
- `validate_role(role)` — uses Ollama to classify whether a role is IT-related; falls back to `True` on any exception
- `generate_questions(profile, question_config=None)` — tries LLM with optional `QuestionConfig` for type distribution; falls back to static question bank
- `evaluate_answer(...)` — dispatches by `question.question_type`:
  - `mcq`/`yes_no` → deterministic `_evaluate_objective()`
  - `coding`/`debugging` → `_evaluate_llm()` which uses `_FEEDBACK_CODE_PROMPT` for Stage 2, producing `code_fix`/`code_review`
  - All others → `_evaluate_llm()` with `_FEEDBACK_PROMPT` producing `grammar_correction`/`simplified_version`
- `synthesize_scorecard(state)` — feeds structured `_build_evaluation_json()` to LLM as primary input with transcript as supplementary context; merges LLM synthesis with deterministic stats from `scoring.py` to produce a 17-field `Scorecard`

### 3a. Industry Guardrail (`industry_guardrail.py`)
- `validate_industry(input_text)` — uses Ollama at `temperature=0` to classify whether user input is a valid industry name
- Does **not** pass `response_format` (Ollama's OpenAI-compatible endpoint does not support it) — instead uses a two-stage parser: strict `json.loads` first, then a regex search for `"is_valid": true|false` as fallback
- Logs the raw Ollama response at INFO level before parsing; logs the parsed boolean result
- Returns only a boolean; never exposes model reasoning
- Raises `RuntimeError` on API failure so the onboarding loop can show a friendly retry message

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
- `_FEEDBACK_CODE_PROMPT` — Stage 2 prompt for coding/debugging questions, produces `code_fix` (corrected code with comments) and `code_review` instead of `grammar_correction`/`simplified_version`
- `SCORECARD_PROMPT` — structured-data prompt with 9 task sections (overall_assessment, hiring_recommendation, candidate_readiness, strongest/weakest_competencies, recurring_patterns, key_concepts_missed, learning_roadmap, learning_resources); uses `{evaluation_json}` as primary input and `{transcript}` as supplementary

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
- **Deterministic stats (6 functions, no LLM):**
  - `compute_interview_stats(state)` → dict (total/answered/skipped, overall_score, letter_grade, highest/lowest_score, avg_confidence, type_distribution, dimension_averages)
  - `compute_strongest_weakest_dimensions(state)` → (top-3, bottom-3) dimension names
  - `compute_question_table(state)` → list of per-question `{id, text, category, score, hiring_decision, confidence, performance_label}`
  - `interpret_radar_chart(state)` → text summary (strongest/weakest areas, spread analysis)
  - `compute_confidence_notice(state)` → warning string if any evaluation had confidence < 0.7

### 7. Export (`export.py`)
- `generate_markdown_transcript(state)` — full Q&A as Markdown
- `generate_scorecard_markdown(state)` — standalone Markdown assessment for export
- `generate_pdf(state, path)` — convert Markdown to PDF via WeasyPrint

### 8. Fallback (`fallback_data.py`)
- 10 questions per seniority level (Junior, Mid, Senior, Lead)
- `fallback_questions(profile, needed, question_config=None)` — returns questions distributed by type when API fails; default fallback is 3 technical + 2 behavioural

### 9. Schemas (`schemas.py`)
Pydantic v2 models:
- `UserProfile` — role, seniority, industry, interview_type (hardcoded to "technical")
- `Question` — id, text, category, question_type (open_ended|behavioral|mcq|yes_no|coding|debugging|system_design), difficulty, expected_keywords, plus optional fields: options, correct_answer, starter_code, language, evaluation_type, buggy_code, expected_fix, evaluation_focus
- `QuestionConfig` — total_questions (default 5), distribution (map of QuestionType to percentage), with `counts()` method
- `Evaluation` — `scores: dict[str, int]` (dynamic dimensions per question type, each validated 1-10); plus strengths, weaknesses, grammar_correction, simplified_version, code_fix (optional), code_review (optional), actionable_feedback, score_reasons, score_evidence, hiring_decision, confidence
- `Scorecard` — 17-field model: 9 LLM-generated (overall_assessment, hiring_recommendation, candidate_readiness, strongest_competencies, weakest_competencies, recurring_patterns, key_concepts_missed, learning_roadmap, learning_resources) + 8 deterministic (overall_score, grade, question_table, dimension_averages, stats, radar_interpretation, confidence_notice)
- `SessionState` — current state, profile, questions, transcript, evaluations, scorecard

### 10. UI (`app.py`)
Chainlit callbacks mapped to state machine actions:
- `Submit` → `evaluate_answer()` → show Feedback
- `Skip` → transition to EVALUATING → FEEDBACK (no evaluation)
- `End Early` → jump to COMPLETED → scorecard
- `Next Question` → advance index, show next question
- `Finish` → trigger scorecard → DEBRIEF
- `Export` → download PDF transcript or Markdown assessment
- `Restart` → reset session
- `Config Done` → trigger question generation with current `QuestionConfig`

**Interactive question rendering (`_show_question`):**
- Questions are displayed as a two-part message:
  1. A permanent `cl.Message` with the question text, type/category badges (via `_question_badge_html()`), countdown timer bar, and formatted code (if applicable) — this message stays visible regardless of button interaction
  2. A separate `cl.AskActionMessage` containing only the action/answer buttons — blocks the UI thread until the user clicks, preventing Chainlit from disabling buttons
- **MCQ** — When `question_type == QuestionType.MCQ` and `options` has ≥ 2 entries, renders clickable option buttons via the `AskActionMessage`. If options are empty or insufficient (< 2), falls back to open-ended with a log warning. The selected option is echoed as a permanent `cl.Message` before submission.
- **Yes/No** — When `question_type == QuestionType.YES_NO`, renders **Yes** and **No** buttons via the `AskActionMessage`. The selected answer is echoed as a permanent `cl.Message`.
- **Open-ended, behavioral, system design** — Renders the question with "Answer" button (triggers `AskUserMessage` with plain text prompt), plus Skip and End Early buttons.
- **Coding** — Renders starter code with a styled "📄 Starter Code (lang)" label above a fenced code block. Clicking "Answer" shows a backtick-guidance prompt asking the user to wrap code in triple backticks; submitted code has surrounding fence markers stripped via regex.
- **Debugging** — Renders buggy code with a "🐛 Buggy Code" label. Same backtick-guidance prompt and fence-stripping as coding.
- All question types display the type/category badge (`_question_badge_html()`), the countdown timer bar, and Skip control. The "End Early" button is hidden on the last question (checked via `is_last`).

**Feedback (`_show_feedback`):**
- Feedback content (scores, coaching) is sent as a permanent `cl.Message` so it persists across the entire session — navigating to the next question does not remove it.
- **Type-aware content:** For coding/debugging questions, shows `code_review` (textual review) and `code_fix` (corrected code in a fenced block) instead of `grammar_correction`/`simplified_version`.
- Action buttons (Next Question / Finish / End Early / Retry) are sent in a separate `AskActionMessage("")` that can be consumed without affecting the visible feedback content.
- "End Early" is hidden when `is_last` is true — only "Finish" is offered on the last question.
- Accepts an optional `eval_failed` parameter to display error-state feedback with a retry option.
- Retry calls `_handle_retry()` helper which re-runs `evaluate_answer()` in a thread.

**Answer handling (`_handle_answer`):**
- Stores the answer in the transcript, transitions state, evaluates via `asyncio.to_thread(evaluate_answer, ...)`.
- Timer-expired warning shown when answer is submitted after timeout.
- For coding/debugging answers, surrounding triple-backtick fences are stripped before storage.

**Onboarding flow:** role (IT-validated via Ollama `validate_role()`) → seniority (4-button picker) → industry (validated via Ollama `validate_industry()`) → **question config** (gated settings panel with total count + per-type percentage sliders → "Generate Questions" button) → question generation → interview.

**Settings panel** — `_build_question_settings()` returns a `cl.ChatSettings` with `NumberInput` (total questions, 1-20) and `Slider` widgets for 6 question types (Technical Open-ended, Behavioral STAR, MCQ, Coding, Debugging, System Design). Percentages are normalized to sum to 100%. Changes are captured by `@cl.on_settings_update` and stored as `QuestionConfig` in the user session.

**IT role validation** — `validate_role()` queries Ollama to classify whether the entered role is IT-related; loops until a valid IT role is provided.

**Industry guardrail** — `validate_industry()` queries Ollama to classify whether the entered industry name is valid; loops until a valid industry is provided, with a friendly retry on API failure.

**Export notes:**
- `cl.File` for `.md` export explicitly sets `mime="text/markdown"` — `filetype.guess()` cannot identify plain text formats like `.md`, and the Chainlit frontend crashes with `Cannot read properties of null (reading 'startsWith')` when `mime` is `None`.
- PDF export works without explicit mime because `filetype.guess()` correctly identifies `.pdf` as `application/pdf`.

Synchronous LLM calls (`generate_questions`, `evaluate_answer`) are offloaded with `await asyncio.to_thread(...)` to prevent blocking the Chainlit event loop (which would freeze the chat input on "Stop task").
