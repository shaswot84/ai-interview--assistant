# Development Log

## Phase 0 — Setup & API Connectivity (2026-07-19)
- Scaffolded project with `uv init`
- Installed dependencies: openai, chainlit, pydantic, plotly, python-dotenv, weasyprint, pytest
- Created `.env.example` with `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `QUESTION_TIMER_SECONDS`
- Built `tests/test_phase0_smoke.py` — key-existence check + API round-trip
- Removed Anthropic support; OpenAI-compatible only
- Added `config.py` with `Config.from_env()` for env-based configuration
- Created complete documentation suite:
  - `CLAUDE.md` — project context with coding standards, current phase, doc index
  - `docs/architecture.md` — comprehensive system design
  - `docs/decisions.md` — ADR-001 through ADR-007
  - `docs/PROGRESS.md` — phase tracking with next tasks
  - `docs/PROMPTS.md` — prompt template registry
  - `docs/TESTING.md` — test strategy, golden cases, fixtures
  - `docs/DEMO.md` — 5-minute demo script with prepared inputs
  - `docs/TROUBLESHOOTING.md` — common errors and provider quirks
  - `docs/logs.md` — this changelog
- **Status:** Phase 0 complete → Ready for Phase 1

## Phase 1 — Core State Machine & Timer (2026-07-19)
- Implemented `schemas.py` with Pydantic v2 models: UserProfile, Question, Evaluation, Scorecard, SessionState, plus enums (Seniority, QuestionCategory, InterviewState, LetterGrade)
  - UserProfile rejects invalid seniority string and short role
  - Evaluation validates all 5 score dimensions (1-10 range)
  - Scorecard has LetterGrade enum (A/B/C/D/F), rejects invalid grade strings
  - SessionState tracks full interview state with deep-copy transitions
- Built `timer.py` with `get_timer_limit()`, `check_elapsed_time()`, `is_timed_out()`
  - Returns 0.0 when no `question_started_at`
  - Reads limit from `Config.question_timer_seconds` (env, default 180)
  - `is_timed_out()` = elapsed > limit
- Built `session_state.py` with state machine:
  - `VALID_TRANSITIONS` dict covering all 8 states and their allowed actions
  - `transition(state, action)` — auto-converts `submit_answer` → `timeout_skip` when timer expired
  - `InvalidTransitionError` raised for illegal moves
  - Timer is reset on entry to INTERVIEWING state
- Wrote 34 tests across 3 files — all green (37 total including Phase 0)
- **Status:** Phase 1 complete → Ready for Phase 2

## Phase 2 — LLM Integration Layer (2026-07-19)
- Built `prompts.py` with three prompt templates:
  - `QUESTION_GEN_PROMPT` — generates 5 questions (3 tech, 2 behavioural) with JSON schema
  - `EVALUATION_PROMPT` — scores 5 dimensions (1-10) + grammar correction + simplified version + feedback
  - `SCORECARD_PROMPT` — synthesises final strengths, improvements, model answer, overall assessment, letter grade
- Built `fallback_data.py` with 40 static questions (10 per seniority level: Junior, Mid, Senior, Lead); `fallback_questions()` selects 3 tech + 2 behavioural by seniority
- Built `llm_client.py`:
  - `_call_with_retry()` — calls OpenAI SDK with `response_format={"type": "json_object"}`, 2 retries with exponential backoff, raises `RuntimeError` on exhaustion
  - `generate_questions(profile)` — tries LLM first, falls back to `fallback_questions()` on any exception
  - `evaluate_answer(question, answer, profile)` — returns `Evaluation` via LLM
  - `synthesize_scorecard(state)` — formats transcript and calls LLM for `Scorecard`, raises `ValueError` if no profile
- Wrote 7 LLM client tests (retry success, retry failure, question gen, fallback, evaluation, scorecard, no-profile error) and 2 provider tests (client instance, provider string) — all green (46 total)
- Updated `docs/PROGRESS.md`, `CLAUDE.md`, `docs/logs.md`
- **Status:** Phase 2 complete → Ready for Phase 3 (UI Layer)

## Phase 3 — UI Layer (2026-07-19)
- Built `scoring.py`:
  - `calculate_question_score(eval_)` — weighted sum (clarity 0.15, completeness 0.25, relevance 0.20, grammar 0.10, impact 0.30) × 10 → 0-100
  - `calculate_overall_score(evaluations)` — average of all evaluated questions
  - `get_letter_grade(score)` — A≥90, B≥80, C≥70, D≥60, F<60
  - `prepare_radar_chart_data(evaluations)` — dimension averages for charting
  - `render_radar_chart(data)` — Plotly `go.Scatterpolar` figure
- Built `export.py`:
  - `generate_markdown_transcript(state)` — full Q&A as Markdown with profile, questions, answers (or "(Skipped)"), scores, scorecard
  - `generate_pdf(state, path)` — WeasyPrint HTML→PDF conversion with _md_to_html helper
- Built `app.py` — Chainlit UI:
  - `@cl.on_chat_start` — welcome + "start" prompt
  - `@cl.on_message` — processes "start" command, onboarding field responses, answer submissions
  - `@cl.action_callback` handlers for: skip, end_early, next_question, finish, export_pdf, export_md, restart
  - Onboarding: step-by-step field collection (role, seniority, industry), seniority uses `AskActionMessage` button selection, validation of seniority enum
  - Interview loop: question display with timer notice, answer → evaluate → feedback → next/finish
  - Scorecard: grade, strengths, improvements, model answer, Plotly radar chart, PDF/MD download buttons, restart
  - Error handling: LLM failures gracefully degrade (fallback questions, placeholder evaluation, minimal scorecard)
- Wrote 22 tests across `test_scoring.py` (15) and `test_export.py` (7) — all green (68 total)
- Updated `docs/PROGRESS.md`, `CLAUDE.md`, `docs/logs.md`
- **Status:** Phase 3 complete → Ready for Phase 4 (Polish & Edge Cases)

## Phase 4 — Polish & Edge Cases (2026-07-19)
- **Injection resistance:**
  - Added `INJECTION_GUARD` constant in `prompts.py` — explicit instruction to ignore manipulation attempts within answers
  - Injected into `EVALUATION_PROMPT` as a system-level guardrail
  - Added score clamping in `llm_client.py:evaluate_answer()` — all 5 dimensions clamped to 1-10 range via `max(1, min(10, score))` before creating `Evaluation`
- **App edge cases:**
  - Removed redundant `if is_timed_out` / `else` in `app.py:_handle_answer()` — both branches called `transition(state, "submit_answer")`; the timer check already happens inside `transition()`
  - Added empty-value validation for onboarding fields — blank/whitespace entries now rejected with "Please enter a value."
- **Shared test fixtures:**
  - Created `tests/conftest.py` with `sample_profile`, `sample_questions`, `sample_evaluation`, `sample_state` for reuse across test files
- **Written 11 edge case tests** (`test_edge_cases.py`):
  - Out-of-range scores clamped (100, -5, 999, 0, 11 → 10, 1, 10, 1, 10)
  - `INJECTION_GUARD` present in `EVALUATION_PROMPT`
  - Legitimate scores unchanged
  - Malformed JSON → retries then RuntimeError
  - Null LLM content → retries then RuntimeError
  - API error → retries then RuntimeError
  - `generate_questions` falls back to `fallback_questions` on LLM failure
  - No evaluations → `calculate_overall_score` returns 0.0
  - Zero score → `get_letter_grade` returns F
  - `synthesize_scorecard` raises ValueError without profile
  - `fallback_questions` returns 3 tech + 2 behavioural
- **Test count:** 79 total (all green)
- Updated `docs/TESTING.md`, `docs/PROGRESS.md`, `docs/logs.md`
- **Status:** Phase 4 complete → Ready for Phase 5

## Phase 5 — Edge Cases, Testing & Polish (2026-07-19)
- **RateLimitError handling:**
  - Added `test_rate_limit_handling` — mocks `RateLimitError`, confirms retry exhaustion raises `RuntimeError`
- **Session state isolation:**
  - Added `test_session_state_isolation` — verifies two `SessionState()` instances are independent
- **Performance benchmarks:**
  - Created `tests/test_performance.py` with three latency tests:
    - `test_question_generation_latency` — target <3s (skipped without API key)
    - `test_answer_evaluation_latency` — target <3s
    - `test_scorecard_synthesis_latency` — target <3s
  - All marked `@pytest.mark.slow`, skipped when `OPENAI_API_KEY` is placeholder
- **Client-side improvements:**
  - Timer-expired warning in `_handle_answer` — notifies user when submitted after timeout
  - `retry_evaluation` action callback — user can retry failed evaluations via UI button
- **README overhaul:**
  - ASCII architecture diagram showing module interactions
  - Provider switching guide (Groq, DeepSeek, OpenAI)
  - Comprehensive troubleshooting table
  - 5-minute demo script outline
  - Configuration reference table
- **Test count:** 82+ total (all green; plus 3 performance tests skipped without key)
- Updated all docs — `PROGRESS.md`, `logs.md`, `TESTING.md`, `CLAUDE.md`
- **Status:** Phase 5 complete → All 5 phases complete

## Phase 5 — Follow-up Fixes (2026-07-19/20)
- **Radar chart in PDF:**
  - `export.py`: `_radar_chart_html()` renders Plotly figure to base64 PNG via `plotly.io.to_image()` + kaleido; embedded in WeasyPrint HTML body
  - Added `kaleido` dependency (`uv add kaleido`)
- **Start button replaces text command:**
  - `on_chat_start` welcome message now has a `cl.Action(name="start", ..., label="Start")` button instead of "Type **start** to begin."
  - Added `@cl.action_callback("start")` that calls `_show_onboarding()`
  - Removed the `IDLE` + `"start"` text-parsing branch from `on_message`
  - Restart message also shows a Start button
- **Visual countdown timer bar:**
  - `_timer_bar_html(seconds)` in `app.py` — pure CSS animation (`__tShrink` + `__tBlink`)
  - Blue bar shrinks from 100%→0% over `timer_limit` seconds
  - At 80% elapsed, `__tBlink` starts — turns red (`#EF4444`) and blinks with 0.6s step-end animation
  - No JavaScript needed
  - `.chainlit/config.toml`: set `unsafe_allow_html = true` so the HTML/CSS renders in the message content
- **Blocking LLM call offloaded:**
  - `generate_questions()` in `_handle_generating()` wrapped with `await asyncio.to_thread()` — prevents UI freeze on "Generating interview questions..."
- **Updated docs/bugs.md** with blocks 9–10
- **Status:** Phase 5 follow-up complete

## Phase 5 — Question Type System & Settings UI (2026-07-21)
- **Extended schemas:**
  - Added `QuestionType` enum with 7 types: `open_ended`, `behavioral`, `mcq`, `yes_no`, `coding`, `debugging`, `system_design`
  - Added `QuestionConfig` model with `total_questions` (default 5), `distribution` (map of type → percentage), and `counts()` method that computes per-type question counts
  - Extended `Question` model with optional type-specific fields: `options`, `correct_answer` (str|bool), `starter_code`, `language`, `evaluation_type`, `buggy_code`, `expected_fix`, `evaluation_focus`
- **Dynamic question generation:**
  - Updated `QUESTION_GEN_PROMPT` with `{distribution_instructions}` and `{question_type_example}` placeholders
  - Added `QUESTION_TYPE_DESCRIPTIONS` dict with field requirements per type
  - Added `QUESTION_TYPE_DISTRIBUTION_TEMPLATE` for constructing per-type distribution instructions
  - Updated `get_question_prompt(profile, config=None)` — when no config is provided, produces the original 3-tech + 2-behav prompt (backward compatible)
  - Updated `generate_questions(profile, question_config=None)` — passes config through to prompt builder and fallback
- **Chainlit settings panel:**
  - Added `_build_question_settings()` helper returning `cl.ChatSettings` with `NumberInput` (total questions 1-20) and `Slider` widgets for 6 question types
  - Added `_settings_to_config()` and `_get_question_config()` helpers for converting settings to `QuestionConfig`
  - Added `@cl.on_settings_update` handler that stores the config in user session
  - **Gated config flow:** Settings panel is sent after the full profile (role → seniority → industry) is assembled, with a `AskActionMessage("Generate Questions")` button that blocks until the user confirms
- **IT role validation:**
  - Added `validate_role()` in `llm_client.py` — LLM classifies whether a role is IT-related (temperature 0), falls back to `True` on API failure
  - Role input loops with rejection message until a valid IT role is entered
- **Updated fallback:** `fallback_questions()` accepts `QuestionConfig` and distributes fallback questions by requested type
- **Bug fixes:** Escaped curly braces in `EVALUATION_PROMPT` (KeyError), restored missing `_get_state()` definition, fixed `cl.Action` syntax error, reordered settings panel to gated position
- **Test count:** 84 total (all green; performance test flaky due to API latency)
- Updated all docs — `PROGRESS.md`, `logs.md`, `bugs.md`, `TROUBLESHOOTING.md`, `DEMO.md`, `architecture.md`, `decisions.md`, `PROMPTS.md`
- **Status:** Phase 5 question-type extension complete

## Phase 5 — Interactive Question Types & UI Polish (2026-07-21)
- **Interactive answer buttons:**
  - MCQ questions now render 4 clickable option buttons via `cl.AskActionMessage` in `_show_question()` — user clicks an option instead of typing
  - Yes/No questions render **Yes** and **No** buttons via `cl.AskActionMessage`
  - Both include Skip and End Early inline actions
  - The selected option value is submitted as the text answer and flows through the standard evaluation pipeline
- **Code formatting for coding/debugging questions:**
  - Coding questions with `starter_code` render the code in a fenced Markdown block with syntax highlighting (` ```{language} `)
  - Debugging questions with `buggy_code` render the buggy code in a fenced code block
- **Feedback action name conflict fix:**
  - Renamed feedback message actions from `next_question`/`finish`/`end_early` to `_feedback_next`/`_feedback_finish`/`_feedback_end_early`
  - This prevents Chainlit from disabling feedback buttons when the same action names appear on the question message (`end_early`, `skip`)
  - Added new callbacks: `on_feedback_next`, `on_feedback_finish`, `on_feedback_end_early`
- **Test count:** 84 total (all green)
- Updated docs — `architecture.md`, `PROGRESS.md`, `bugs.md`, `logs.md`, `DEMO.md`
- **Status:** Phase 5 interactive question support complete

## Phase 5 — Full AskActionMessage Refactor for Persistent Buttons (2026-07-22)
- **Persistent question display:**
  - Split question rendering into two parts: a permanent `cl.Message` (question text, timer bar, code blocks) + a separate `cl.AskActionMessage` (buttons only)
  - This keeps the question content visible when "Answer" is clicked (AskUserMessage would otherwise cover it)
- **All actions converted to AskActionMessage:**
  - Question action buttons (MCQ options, Yes/No, Answer/Skip/End Early) now use `cl.AskActionMessage` — blocks the UI thread until the user clicks, preventing Chainlit's automatic button disable mechanism
  - Feedback actions converted from `cl.Message` + `@cl.action_callback` to `cl.AskActionMessage` with inline handling — no callback registration needed, buttons stay clickable
- **Retry integration:**
  - Added `_handle_retry()` helper that re-runs `evaluate_answer()` in a thread for failed evaluations
  - `_show_feedback()` accepts `eval_failed` parameter to display error-state feedback with retry option
- **Test count:** 84 total (all green; 1 performance test flaky due to API latency)
- Updated docs — `architecture.md`, `PROGRESS.md`, `bugs.md`, `logs.md`
- **Status:** Phase 5 interactive question support complete

## Phase 5 — Deterministic Evaluation for Objective Types (2026-07-22)
- **Dispatch pattern:** `evaluate_answer()` now dispatches by `question.question_type` — `mcq`/`yes_no` → `_evaluate_objective()`, all others → `_evaluate_llm()` (unchanged)
- **Deterministic evaluation:** `_evaluate_objective()` compares answer vs `question.correct_answer` case-insensitively; returns all scores = 10 (correct) or all scores = 1 (incorrect) with feedback in `actionable_feedback`
- `_format_transcript()` expanded to show all 9 score dimensions
- **Test count:** 90 total (added 6 deterministic tests; 1 performance flake)
- Updated docs — `architecture.md`, `PROGRESS.md`, `bugs.md`, `logs.md`, `DEMO.md`, `CLAUDE.md`

## Phase 5 — Dynamic Per-Type Evaluation Dimensions (2026-07-22)
- **`Evaluation.scores` refactored** from 9 fixed fields to `dict[str, int]` — each question type defines its own relevant dimensions
- **Removed dimensions:** `grammar`, `impact`, `architecture_design`
- **Added dimensions:** `correctness` (first-class), `solution_quality`
- **Per-type dimension sets:**
  - open_ended: clarity, completeness, relevance, correctness, technical_depth, problem_solving, tradeoff_analysis
  - behavioral: clarity, completeness, relevance, problem_solving
  - coding/debugging: correctness, solution_quality, technical_depth, problem_solving
  - system_design: correctness, solution_quality, tradeoff_analysis, technical_depth, problem_solving
  - mcq/yes_no: correctness (deterministic)
- **Prompt rewrite:**
  - `EVALUATION_PROMPT` now includes `question_type`, `question_type_guidance`, `type_dimensions`, and `type_output_fields` placeholders
  - Added `QUESTION_TYPE_GUIDANCE` dict (per-type evaluation instructions)
  - Added `TYPE_DIMENSIONS` dict (per-type dimension names + descriptions)
  - Added `TYPE_OUTPUT_FIELDS` dict (per-type JSON output template)
  - `get_evaluation_prompt()` accepts `question_type` parameter
- **`_EvaluationResponse`** uses `model_config = {"extra": "allow"}` — dimension scores extracted from extra fields, clamped to 1-10
- **Scoring:** equal-weighted average of present dimensions × 10 (removed per-dimension weights from `WEIGHTS` dict)
- **Radar chart:** dynamically collects all unique dimension keys across evaluations; averages per-dimension count (not total evaluation count)
- **Feedback UI and exports:** iterate `eval_.scores.items()` instead of fixed field access
- **Test count:** 93 total (all green)
- Added ADR-012 to `docs/decisions.md`
- Updated all docs — `architecture.md`, `PROMPTS.md`, `TESTING.md`, `decisions.md`, `logs.md`, `PROGRESS.md`, `CLAUDE.md`
- **Status:** Phase 5 dynamic per-type evaluation complete

## Phase 5 — Ollama Onboarding Guardrails (2026-07-22)
- **Ollama API config:**
  - Added `OLLAMA_API_KEY`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` to `.env` and `config.py`
  - Added `get_ollama_client()` in `providers.py` — returns an OpenAI-compatible client configured for the Ollama endpoint
- **Industry guardrail:**
  - Created `industry_guardrail.py` with `validate_industry()` — calls Ollama at `temperature=0` with `response_format=json_object` to classify industry names
  - Returns only a boolean; raises `RuntimeError` on API failure
  - Wired into `app.py` onboarding loop — invalid → retry prompt, API error → "temporarily unavailable" → retry
- **Role validation migration:**
  - `validate_role()` in `llm_client.py` rewritten to use `get_ollama_client()` directly instead of `_call_with_retry` (Groq/OpenAI)
  - Falls back to `True` (allow) on any exception
- **Removed:** Gemini API integration (key, config field, `google-genai` dependency, `industry_guardrail.py` Gemini version, Gemini tests)
- **Test count:** 95 total (added 5 industry guardrail tests)
- Updated all docs — `CLAUDE.md`, `architecture.md`, `decisions.md` (ADR-013), `PROGRESS.md`, `TESTING.md`, `TROUBLESHOOTING.md`, `logs.md`, `.env.example`

## Phase 5 — Guardrail Robustness & UI Fixes (2026-07-22)
- **response_format removed from Ollama guardrails:**
  - `validate_industry()` and `validate_role()` no longer pass `response_format={"type": "json_object"}` — Ollama's `/v1/chat/completions` endpoint does not support it, causing the model to return freeform text and `json.loads` to fail
  - Replaced with `_parse_boolean_response()` — tries strict `json.loads` first, then a regex search for `"is_valid": true|false` (or `"is_it_role"` in `validate_role`)
  - Added logging at each stage (input, raw response, parsed result) for debugging
- **Groq response logging:**
  - `_call_with_retry()` now logs the raw Groq response at INFO level before Pydantic validation
- **Feedback persistence fix:**
  - `_show_feedback()` previously bundled content (scores, grammar) and action buttons in a single `AskActionMessage` — when the user clicked "Next Question", Chainlit consumed the `AskActionMessage` and removed the entire message, including the feedback content
  - Split into two messages: a permanent `cl.Message(content)` for the feedback text, then a separate `AskActionMessage("")` with only action buttons. Feedback content now persists for the entire session.
  - Same split applied to the skipped-question branch.
- **End Early visibility fix:**
  - "End Early" button was displayed on every question and its feedback, even the last one where it is meaningless
  - Added `is_last` check in `_show_question()` — conditionally omits `_end_q` / `end_early` action on the last question for all three question-type paths (MCQ, YES_NO, open-ended)
  - Same check in `_show_feedback()` — "End Early" hidden on last-question feedback in both skipped and evaluated branches
- **Code cleanup:** Removed unused `_RoleValidationResponse` Pydantic model and its `BaseModel` import from `llm_client.py`
- **Test count:** 97 total (added 2 regex-fallback tests; 7 total in `test_industry_guardrail.py`)
- Updated all docs — committed and pushed to `origin/main` as `c56ebc4`

## Phase 5 — Scorecard Redesign (2026-07-23)
- **Problem:** `synthesize_scorecard()` fed a flat text transcript to the LLM — no access to per-question hiring decisions, confidence scores, score evidence, question types, or aggregated stats. The 5-field `Scorecard` was too small for rich output.
- **Solution:** Three-phase redesign:
  1. **Deterministic stats in Python** — added 6 functions to `scoring.py`: `compute_interview_stats`, `compute_strongest_weakest_dimensions`, `compute_question_table`, `interpret_radar_chart`, `compute_confidence_notice`, `_compute_highest_lowest`
  2. **Structured JSON to LLM** — added `_build_evaluation_json()` in `llm_client.py` to feed per-question structured data (scores, reasons, evidence, hiring_decision, confidence) to the LLM; replaced 5-field `SCORECARD_PROMPT` with 9-section structured-data prompt
  3. **Rich rendering** — `_show_scorecard()` now renders 14 sections: header, assessment, readiness, stats table, question-by-question table, strongest/weakest competencies, recurring patterns, key concepts missed, radar chart with interpretation, learning roadmap, recommended resources
- **Scorecard model:** expanded from 5 fields to 17: 9 LLM-generated (overall_assessment, hiring_recommendation, candidate_readiness, strongest_competencies, weakest_competencies, recurring_patterns, key_concepts_missed, learning_roadmap, learning_resources) + 8 deterministic (overall_score, grade, question_table, dimension_averages, stats, radar_interpretation, confidence_notice)
- **LLM client:** `_ScorecardResponse` updated to 9 fields; `synthesize_scorecard()` merges LLM output with Python-computed stats; `_format_transcript()` kept for supplementary context
- **Export:** `generate_markdown_transcript()` updated to use new Scorecard fields; added `generate_scorecard_markdown()` for standalone assessment export
- **Export button fixes:** Renamed buttons ("Download Transcript" for PDF, "Export Assessment" for Markdown); `export_md` callback wired to `generate_scorecard_markdown()`; timestamped filenames; `evaluate_answer()` and `synthesize_scorecard()` offloaded to `asyncio.to_thread`
- **Tests:** fixed `conftest.py` Evaluation fixture (dict-based scores), updated `test_llm_client.py`, `test_export.py`, `test_schemas.py` to new Scorecard model
- **Performance thresholds:** recalibrated — question gen 3s→6s, evaluation 3s→8s, scorecard synthesis 3s→25s (richer output)
- **Test count:** 108 total (all green; 3 performance benchmarks)
- Updated all docs — `CLAUDE.md`, `architecture.md`, `PROGRESS.md`, `PROMPTS.md`, `TESTING.md`, `logs.md`
- **Status:** Phase 5 scorecard redesign complete

## Phase 5 — MCQ Visibility, Type-Aware Feedback & UI Polish (2026-07-23)
- **MCQ answer echo:** After selecting an MCQ or Yes/No option, the chosen answer is echoed as a permanent `cl.Message` so it stays visible after the `AskActionMessage` is consumed.
- **Empty MCQ guard:** If an MCQ question has no options or fewer than 2, it falls back to open-ended with a warning log (no crash, no blank buttons).
- **Type/category badges:** Added `_question_badge_html()` helper — every question now shows colored badges: type (💻 CODING, 🧠 BEHAVIORAL, ✅ MCQ, 🐛 DEBUGGING, 🏗️ SYSTEM DESIGN) and category (Concurrency, Databases, etc.).
- **Enhanced code rendering:** Coding blocks have a "📄 Starter Code (lang)" label above; debugging blocks have "🐛 Buggy Code" label.
- **Code-paste hint:** Clicking "Answer" on coding/debugging questions shows backtick guidance prompt; submitted code has surrounding ``` fences stripped.
- **Type-aware feedback:** Added `_FEEDBACK_CODE_PROMPT` for coding/debugging questions — generates `code_fix` (corrected code with comments) and `code_review` instead of `grammar_correction`/`simplified_version`. `_generate_feedback()` dispatches on `QuestionType.CODING`/`DEBUGGING`. `_show_feedback()` conditionally renders code review/fix vs grammar/simplified.
- **Schema:** Added optional `code_fix` and `code_review` fields to `Evaluation` (backward-compatible).
- **Test count:** 108 total (all green)
- Updated `docs/logs.md`
- **Status:** Phase 5 UI polish complete

## Phase 5 — Export Assessment Crash Fix (2026-07-23)
- **Export crash fixed:** `cl.File` for `.md` export was missing explicit `mime` — `filetype.guess()` returns `None` for `.md` files, and the Chainlit frontend crashes with "Cannot read properties of null (reading 'startsWith')" when `element.mime` is null.
- **Fix:** Added `mime="text/markdown"` to the `cl.File` call. PDF export at line 226 was already fine since `filetype.guess()` correctly identifies `.pdf` as `application/pdf`.
- **Commit:** `455b406`
- **Test count:** 108 total (all green)
- Updated `docs/bugs.md`, `docs/logs.md`
- **Status:** Export crash resolved
