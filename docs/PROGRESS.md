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
- [x] 2026-07-19: Built `fallback_data.py` — 40 static questions across 4 seniority levels; 3 tech + 2 behavioural per call
- [x] 2026-07-19: Built `llm_client.py` — `_call_with_retry()` (2 retries, exponential backoff), `generate_questions()` (LLM → fallback), `evaluate_answer()`, `synthesize_scorecard()` with `_format_transcript()`
- [x] 2026-07-19: Wrote tests: `test_providers.py` (2 tests), `test_llm_client.py` (7 tests) — all green

### Completed (Phase 3)
- [x] 2026-07-19: Built `scoring.py` — `calculate_question_score()` (weighted), `calculate_overall_score()`, `get_letter_grade()`, `prepare_radar_chart_data()`, `render_radar_chart()` (Plotly)
- [x] 2026-07-19: Built `export.py` — `generate_markdown_transcript()` (full Q&A), `generate_pdf()` (WeasyPrint HTML→PDF)
- [x] 2026-07-19: Built `app.py` — Chainlit UI with onboarding flow, question/answer cycle, skip/end-early actions, feedback display with scores, scorecard with radar chart, PDF/Markdown export, restart
- [x] 2026-07-19: Wrote tests: `test_scoring.py` (15 tests), `test_export.py` (7 tests) — all green

### Completed (Phase 4)
- [x] 2026-07-19: Added `INJECTION_GUARD` to `EVALUATION_PROMPT`
- [x] 2026-07-19: Added score clamping — all dimensions clamped to 1-10
- [x] 2026-07-19: Removed redundant `if is_timed_out` branch — handled inside `transition()`
- [x] 2026-07-19: Added empty-value validation for onboarding fields
- [x] 2026-07-19: Created `tests/conftest.py` with shared fixtures
- [x] 2026-07-19: Wrote `test_edge_cases.py` (11 tests): injection, clamping, retry, fallback, score boundaries

### Completed (Phase 5 — Core)
- [x] 2026-07-19: Added `test_rate_limit_handling` — `RateLimitError` triggers retry logic
- [x] 2026-07-19: Added `test_session_state_isolation` — independent `SessionState()` instances
- [x] 2026-07-19: Created `tests/test_performance.py` — latency benchmarks
- [x] 2026-07-19: Added `retry_evaluation` action callback
- [x] 2026-07-19: Added timer-expired warning in `_handle_answer`
- [x] 2026-07-19: Updated `README.md` — architecture diagram, provider guide, troubleshooting table
- [x] 2026-07-19: Seniority onboarding uses `AskActionMessage` with 4 buttons

### Completed (Phase 5 — Follow-up)
- [x] 2026-07-19: Radar chart included in PDF export via plotly + kaleido base64 PNG
- [x] 2026-07-19: Welcome screen uses **Start button** instead of text command
- [x] 2026-07-19: Visual countdown timer bar — CSS-animated, blue→red+blink at 80%
- [x] 2026-07-19: Blocking LLM call offloaded to `asyncio.to_thread`
- [x] 2026-07-19: `.chainlit/config.toml` — `unsafe_allow_html = true`
- [x] 2026-07-20: Added `SENIORITY_PERSONAS` dict — per-level focus areas injected into question gen
- [x] 2026-07-20: Per-operation LLM temperatures — `GENERATION_TEMPERATURE` (0.9), `EVALUATION_TEMPERATURE` (0.3), `SCORECARD_TEMPERATURE` (0.3)
- [x] 2026-07-20: Added `difficulty` and `expected_keywords` to `Question` schema
- [x] 2026-07-20: Added `BEHAVIORAL` alias to `QuestionCategory` enum

### Completed (Phase 5 — Question Type System)
- [x] 2026-07-21: Added `QuestionType` enum (7 types) and `QuestionConfig` model
- [x] 2026-07-21: Extended `Question` with optional type-specific fields
- [x] 2026-07-21: Dynamic question generation via `{distribution_instructions}` placeholder
- [x] 2026-07-21: Updated `get_question_prompt()` and `generate_questions()` for config-driven mode
- [x] 2026-07-21: Chainlit settings panel with sliders for per-type percentages
- [x] 2026-07-21: Gated config flow — profile → settings → generate
- [x] 2026-07-21: IT role validation via Ollama (`validate_role()`)
- [x] 2026-07-21: Fallback data accepts `QuestionConfig` for type distribution

### Completed (Phase 5 — Interactive UI)
- [x] 2026-07-21: Interactive MCQ buttons (4 options) and Yes/No buttons via `AskActionMessage`
- [x] 2026-07-21: Coding/debugging starter/buggy code in formatted Markdown code blocks
- [x] 2026-07-21: Renamed feedback actions to `_feedback_*` to avoid name conflicts
- [x] 2026-07-22: Split question display into permanent `cl.Message` + separate `AskActionMessage`
- [x] 2026-07-22: Converted feedback to `AskActionMessage` with inline handling
- [x] 2026-07-22: Added `_handle_retry()` for re-running failed evaluations

### Completed (Phase 5 — Evaluation & Scoring)
- [x] 2026-07-22: Deterministic evaluation dispatch — `mcq`/`yes_no` → `_evaluate_objective()`, others → `_evaluate_llm()`
- [x] 2026-07-22: `_evaluate_objective()` compares answer vs `correct_answer` case-insensitively
- [x] 2026-07-22: `Evaluation.scores` refactored to `dict[str, int]` — dimensions are dynamic per type
- [x] 2026-07-22: Removed `grammar`, `impact`, `architecture_design`; added `correctness`, `solution_quality`
- [x] 2026-07-22: Per-type dimension sets in `TYPE_DIMENSIONS`; per-type output format in `TYPE_OUTPUT_FIELDS`
- [x] 2026-07-22: Equal-weighted scoring (average of present dimensions × 10)
- [x] 2026-07-22: `prepare_radar_chart_data()` dynamically collects all unique dimension keys
- [x] 2026-07-22: Feedback UI and exports iterate `eval_.scores.items()`

### Completed (Phase 5 — Guardrails & Robustness)
- [x] 2026-07-22: Ollama API config (`OLLAMA_API_KEY`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`)
- [x] 2026-07-22: `get_ollama_client()` in `providers.py`
- [x] 2026-07-22: `validate_role()` migrated from Groq/OpenAI to Ollama
- [x] 2026-07-22: `industry_guardrail.py` with `validate_industry()`
- [x] 2026-07-22: Feedback persistence fix — permanent `cl.Message` + separate `AskActionMessage`
- [x] 2026-07-22: "End Early" hidden on last question in all three type paths
- [x] 2026-07-22: Removed `response_format` from Ollama guardrails; added `_parse_boolean_response()` regex fallback
- [x] 2026-07-22: Groq raw response logging at INFO level
- [x] 2026-07-22: Removed dead `_RoleValidationResponse` class

### Completed (Phase 5 — Scorecard Redesign)
- [x] 2026-07-23: 6 deterministic stat functions in `scoring.py`
- [x] 2026-07-23: `Scorecard` expanded from 5 to 17 fields (9 LLM + 8 deterministic)
- [x] 2026-07-23: Structured-data `SCORECARD_PROMPT` with 9 sections
- [x] 2026-07-23: `_build_evaluation_json()` in `llm_client.py`
- [x] 2026-07-23: `_show_scorecard()` rewritten with 14 sections
- [x] 2026-07-23: Export buttons renamed, `generate_scorecard_markdown()` added, timestamped filenames
- [x] 2026-07-23: Tests updated for new Scorecard model; performance thresholds recalibrated
- [x] 2026-07-23: 108 tests total (all green; 3 performance benchmarks)

### Completed (Phase 5 — UI Polish & Code Feedback)
- [x] 2026-07-23: MCQ/Yes-No answer echoed as permanent `cl.Message`
- [x] 2026-07-23: Empty MCQ guard — falls back to open-ended with log warning
- [x] 2026-07-23: `_question_badge_html()` — colored type + category badges on all questions
- [x] 2026-07-23: Enhanced code rendering with "📄 Starter Code" / "🐛 Buggy Code" labels
- [x] 2026-07-23: Backtick-guidance prompt for coding/debugging answers
- [x] 2026-07-23: Triple-backtick fence stripping via regex on submission
- [x] 2026-07-23: `_FEEDBACK_CODE_PROMPT` — generates `code_fix`/`code_review` for coding/debugging
- [x] 2026-07-23: `_generate_feedback()` dispatches on `QuestionType.CODING`/`DEBUGGING`
- [x] 2026-07-23: `_show_feedback()` renders code review/fix vs grammar/simplified based on type
- [x] 2026-07-23: Optional `code_fix`/`code_review` fields added to `Evaluation` schema

### Completed (Phase 5 — Export Crash Fix)
- [x] 2026-07-23: Export Assessment crash fixed — `mime="text/markdown"` on `cl.File` for `.md` files
- [x] 2026-07-23: Root cause documented: `filetype.guess()` returns `None` for `.md` → Chainlit frontend crashes

### Blocked
- None

### Next
- [ ] Code editor (Monaco) for coding/debugging questions instead of `AskUserMessage` text input
- [ ] Open-ended/BEHAVIORAL/SYSTEM_DESIGN multi-line text input with larger text box
- [ ] Follow-up question support in the interview flow
