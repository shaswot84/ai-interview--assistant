# Progress

## Current Phase: 5 — Edge Cases, Testing & Polish
**Status:** Completed

### Completed (Phase 0)
- [x] 2026-07-19: Scaffolded project with `uv init`
- [x] 2026-07-19: Installed all dependencies
- [x] 2026-07-19: Created `.env.example` with all config vars
- [x] 2026-07-19: Built `tests/test_phase0_smoke.py` — key existence + API round-trip
- [x] 2026-07-19: Removed Anthropic support; OpenAI-compatible only
- [x] 2026-07-19: Added `config.py` with `Config.from_env()`
- [x] 2026-07-19: Created complete documentation suite

### Completed (Phase 1)
- [x] 2026-07-19: Implemented `schemas.py` — UserProfile, Question, Evaluation, Scorecard, SessionState with Pydantic v2 validation
- [x] 2026-07-19: Built `timer.py` — `get_timer_limit()`, `check_elapsed_time()`, `is_timed_out()`
- [x] 2026-07-19: Built `session_state.py` — `VALID_TRANSITIONS` dict, `transition()` with timer auto-skip, `InvalidTransitionError`
- [x] 2026-07-19: Wrote 34 tests across `test_timer.py`, `test_state_machine.py`, `test_schemas.py` — all green

### Completed (Phase 2)
- [x] 2026-07-19: Implemented `prompts.py` — QUESTION_GEN_PROMPT, EVALUATION_PROMPT, SCORECARD_PROMPT with format placeholders
- [x] 2026-07-19: Built `fallback_data.py` — 40 static questions across 4 seniority levels (Junior, Mid, Senior, Lead); 3 tech + 2 behavioural per call
- [x] 2026-07-19: Built `llm_client.py` — `_call_with_retry()` (2 retries, exponential backoff), `generate_questions()` (LLM → fallback), `evaluate_answer()`, `synthesize_scorecard()` with `_format_transcript()`
- [x] 2026-07-19: Wrote tests: `test_providers.py` (2 tests), `test_llm_client.py` (7 tests) — all green

### Completed (Phase 3)
- [x] 2026-07-19: Built `scoring.py` — `calculate_question_score()` (weighted), `calculate_overall_score()`, `get_letter_grade()` (A≥90, B≥80, C≥70, D≥60, F<60), `prepare_radar_chart_data()`, `render_radar_chart()` (Plotly)
- [x] 2026-07-19: Built `export.py` — `generate_markdown_transcript()` (full Q&A), `generate_pdf()` (WeasyPrint HTML→PDF)
- [x] 2026-07-19: Built `app.py` — Chainlit UI with onboarding flow, question/answer cycle, skip/end-early actions, feedback display with scores, scorecard with radar chart, PDF/Markdown export, restart
- [x] 2026-07-19: Wrote tests: `test_scoring.py` (15 tests), `test_export.py` (7 tests) — all green

### Completed (Phase 4)
- [x] 2026-07-19: Added `INJECTION_GUARD` to `EVALUATION_PROMPT` — explicit instruction to ignore manipulation attempts within answers
- [x] 2026-07-19: Added score clamping in `llm_client.py:evaluate_answer()` — clamps all 5 dimensions to 1-10 range before creating Evaluation
- [x] 2026-07-19: Removed redundant `if is_timed_out` branch in `app.py:_handle_answer()` — already handled inside `transition()`
- [x] 2026-07-19: Added empty-value validation for onboarding fields in `app.py:on_message()` — rejects blank entries
- [x] 2026-07-19: Created `tests/conftest.py` with shared fixtures: `sample_profile`, `sample_questions`, `sample_evaluation`, `sample_state`
- [x] 2026-07-19: Wrote `test_edge_cases.py` (11 tests): injection clamping, guard prompt, legitimate scores unchanged, malformed JSON retries, null content retries, API error retries, fallback on LLM failure, zero evaluations → 0 score, zero score → grade F, synthesize without profile, fallback question ratio
- [x] 2026-07-19: Updated `docs/TESTING.md` — conftest fixtures, new edge case test entries

### Completed (Phase 5)
- [x] 2026-07-19: Added `test_rate_limit_handling` — `RateLimitError` triggers retry logic
- [x] 2026-07-19: Added `test_session_state_isolation` — independent `SessionState()` instances
- [x] 2026-07-19: Created `tests/test_performance.py` — latency benchmarks for question gen (<3s), evaluation (<3s), scorecard (<3s)
- [x] 2026-07-19: Added `retry_evaluation` action callback — allows retrying failed evaluations
- [x] 2026-07-19: Added timer-expired warning in `_handle_answer` — alerts user when answer is skipped
- [x] 2026-07-19: Updated `README.md` — architecture diagram (ASCII), provider switching guide, troubleshooting table, demo script outline
- [x] 2026-07-19: Updated all docs — PROGRAMS.md, logs.md, TESTING.md, CLAUDE.md
- [x] 2026-07-19: Seniority onboarding uses `AskActionMessage` with 4 buttons (Junior/Mid/Senior/Lead) instead of free-text input

### Completed (Phase 5 — Follow-up)
- [x] 2026-07-19: Radar chart included in PDF export — Plotly figure rendered to base64 PNG via kaleido
- [x] 2026-07-19: Welcome screen uses **Start button** instead of "Type **start** to begin" — `on_chat_start` sends a `cl.Action` button; `IDLE` branch in `on_message` removed
- [x] 2026-07-19: Visual countdown timer bar per question — CSS-animated bar shrinks from 100%→0% in blue, turns red+blinks at 80% elapsed
- [x] 2026-07-19: Blocks previously hidden are listed in `docs/bugs.md`; blocking LLM call offloaded to `asyncio.to_thread` so the chat input does not freeze on "Generating interview questions..."
- [x] 2026-07-19: New dotfile `.chainlit/config.toml` — `unsafe_allow_html = true` to let HTML/CSS timer bar render
- [x] 2026-07-19: Updated `docs/logs.md`, `docs/bugs.md`, `docs/TROUBLESHOOTING.md`, `docs/architecture.md`, `docs/DEMO.md`
- [x] 2026-07-20: Added `SENIORITY_PERSONAS` dict — per-level focus areas injected into question gen prompt; `get_question_prompt()` builder
- [x] 2026-07-20: Made LLM temperature per-operation configurable — `GENERATION_TEMPERATURE` (0.9), `EVALUATION_TEMPERATURE` (0.3), `SCORECARD_TEMPERATURE` (0.3) via `.env`
- [x] 2026-07-20: Added `difficulty` and `expected_keywords` fields to `Question` schema
- [x] 2026-07-20: Added `BEHAVIORAL` alias to `QuestionCategory` enum
- [x] 2026-07-20: Updated docs — architecture.md, decisions.md, PROMPTS.md, PROGRESS.md
- [x] 2026-07-21: Added `QuestionType` enum (7 types) and `QuestionConfig` model with distribution — schemas.py
- [x] 2026-07-21: Extended `Question` schema with optional type-specific fields (options, correct_answer, starter_code, language, buggy_code, evaluation_focus, etc.)
- [x] 2026-07-21: Updated `QUESTION_GEN_PROMPT` to accept `{distribution_instructions}` — generates dynamic question type mix instead of fixed 3+2
- [x] 2026-07-21: Updated `get_question_prompt(profile, config)` — builds distribution instructions when config is provided
- [x] 2026-07-21: Updated `generate_questions(profile, question_config)` — passes config through to prompt builder and fallback
- [x] 2026-07-21: Added `_build_question_settings()` helper and `@cl.on_settings_update` — Chainlit settings panel with sliders for each question type percentage
- [x] 2026-07-21: Gated config flow: profile collected first, then settings panel sent, then "Generate Questions" button blocks until user confirms
- [x] 2026-07-21: Added IT role validation via LLM (`validate_role()`) — loops until valid IT role entered
- [x] 2026-07-21: Updated `fallback_data.py` `fallback_questions()` to accept `QuestionConfig` and distribute fallback questions by type
- [x] 2026-07-21: Added interactive answer buttons for MCQ (4 options) and Yes/No (2 buttons) via `cl.AskActionMessage` in `_show_question()`
- [x] 2026-07-21: Coding and debugging questions render starter/buggy code in formatted Markdown code blocks
- [x] 2026-07-21: Renamed feedback action names (`_feedback_next`, `_feedback_finish`, `_feedback_end_early`) to avoid cross-message action name conflicts with question message actions
- [x] 2026-07-22: Refactored question display — permanent `cl.Message` for content + separate `cl.AskActionMessage` for buttons, so question stays visible when "Answer" is clicked
- [x] 2026-07-22: Converted feedback from `cl.Message` + action callbacks to `cl.AskActionMessage` with inline handling, preventing button disable after answering
- [x] 2026-07-22: Added `_handle_retry()` helper for re-running failed evaluations; `_show_feedback()` accepts `eval_failed` parameter

### Blocked
- None
