# AI Interview Assistant — Claude Project Context

## Overview
Personalised mock interview app powered by an OpenAI-compatible LLM. Built with Chainlit, Pydantic, and Plotly.

## Stack
- **Python 3.11** | **uv** (package manager)
- **Chainlit 2.11** (UI framework)
- **OpenAI SDK** (works with OpenAI, Groq, DeepSeek, Ollama, etc.)
- **Pydantic v2** (schemas/validation)
- **Plotly** (radar chart)
- **WeasyPrint** (PDF export)

## Coding Standards
- Validate all LLM responses with Pydantic models before use
- State transitions must go through `session_state.transition()` — never mutate state directly
- Use `Config.from_env()` for all configuration; never read `os.getenv` outside `config.py`
- Type-annotate all function signatures
- No bare `except:` — catch specific exceptions
- One test file per module under `tests/`
- `Evaluation.scores` is a `dict[str, int]` — dimensions are dynamic per question type (do not add fixed fields)
- Onboarding uses two separate guardrails backed by the Ollama API: `validate_role()` (IT-role classification) and `validate_industry()` (industry-name classification)
- Ollama guardrails use a two-stage parser (JSON → regex fallback) — do **not** add `response_format` for Ollama calls
- Feedback content is sent as a permanent `cl.Message`; action buttons are in a separate `AskActionMessage` — never bundle content and actions in a single `AskActionMessage`
- "End Early" button is hidden on the last question (check `is_last`) in both `_show_question()` and `_show_feedback()`
- Question generation uses 9 quality constraint blocks (includes scenario diversity guard)
- `Question.category` uses the `Competency` enum (specific competencies like `problem_solving`, `api_design`) — not the generic `QuestionCategory`
- `Evaluation` has `score_reasons: dict[str, str]`, `score_evidence: dict[str, str]`, `hiring_decision: str`, and `confidence: float` (0.0–1.0) in addition to `scores`
- Two-stage evaluation pipeline: Stage 1 (`EVALUATION_STRICT_PROMPT`) produces strict scores + evidence + hiring_decision; Stage 2 (`_FEEDBACK_PROMPT` or `_FEEDBACK_CODE_PROMPT`) produces coaching feedback using Stage 1 scores as context
- Stage 1 uses "START EVERY DIMENSION AT 1" mindset, mandatory score caps, concrete anchor rubric, evidence requirement (quote needed for score >= 8), internal consistency rules, and self-verification
- `_evaluate_llm()` orchestrates both stages; `_generate_feedback()` dispatches on `QuestionType.CODING`/`DEBUGGING` to use `_FEEDBACK_CODE_PROMPT` (returns `code_fix`/`code_review`) vs `_FEEDBACK_PROMPT` (returns `grammar_correction`/`simplified_version`); returns None on failure (graceful fallback to empty feedback)
- `get_evaluation_prompt()` and `get_question_prompt()` both accept a `UserProfile` with optional `interviewer_style` to inject style-specific persona
- `scoring.calculate_question_score()` accepts `question_type: str` for per-type weighted scoring; uses `TYPE_DIMENSION_WEIGHTS` dict
- `llm_client.generate_follow_up()` creates adaptive follow-up questions; falls back to "Can you go deeper on that?"
- `UserProfile` has optional `interviewer_style: InterviewerStyle` (default: DEFAULT)
- `Scorecard` has 17 fields: 9 LLM-generated (overall_assessment, hiring_recommendation, candidate_readiness, strongest_competencies, weakest_competencies, recurring_patterns, key_concepts_missed, learning_roadmap, learning_resources) + 8 deterministic Python-computed fields
- `synthesize_scorecard()` uses structured `_build_evaluation_json()` as primary LLM input; deterministic stats from `scoring.py` are merged into the Scorecard after the LLM call
- `scoring.py` has 6 deterministic stat functions: `compute_interview_stats`, `compute_strongest_weakest_dimensions`, `compute_question_table`, `interpret_radar_chart`, `compute_confidence_notice`, `_compute_highest_lowest`
- `_ScorecardResponse` in `llm_client.py` covers only the LLM-generated subset (9 fields); deterministic fields are filled in Python
- `_question_badge_html()` renders colored type + category badges on every question (CODING, BEHAVIORAL, MCQ, YES/NO, DEBUGGING, SYSTEM DESIGN)
- MCQ options are echoed as a permanent `cl.Message` after selection; empty MCQ options (< 2) fall back to open-ended with a log warning
- MCQ/Yes-No answers are echoed as a permanent `cl.Message` (`**Your answer:** {text}`) so the selection stays visible after `AskActionMessage` consumption
- `_FEEDBACK_CODE_PROMPT` generates `code_fix` + `code_review` for coding/debugging questions instead of `grammar_correction`/`simplified_version`; `_generate_feedback()` dispatches on `QuestionType.CODING` or `DEBUGGING`
- Coding/debugging answers get a backtick-guidance `AskUserMessage` prompt; surrounding triple-backtick fences are stripped with regex before submission
- Code/debugging questions render starter/buggy code with styled labels (`📄 Starter Code (lang)` / `🐛 Buggy Code`)
- `cl.File` for `.md` exports must set `mime="text/markdown"` explicitly — `filetype.guess()` cannot identify `.md` files, causing Chainlit frontend crash (`Cannot read properties of null (reading 'startsWith')`)
- `Evaluation` has optional `code_fix` and `code_review` fields (backward-compatible) used only for coding/debugging questions

## State Machine
```
IDLE → ONBOARDING → GENERATING → INTERVIEWING → EVALUATING → FEEDBACK → COMPLETED → DEBRIEF
```

## Key Commands
```bash
uv run pytest tests/ -v                 # Run all tests
uv run pytest tests/test_X.py -v        # Run a specific test file
uv run chainlit run app.py               # Start the app
uv add <package>                         # Add a dependency
uv sync                                  # Sync environment
uv run python -c "..."                   # Quick script
```

## Current Phase: 5 — Edge Cases, Testing & Polish

## Tests
```bash
uv run pytest tests/ -v                 # 108 tests, all green
uv run pytest tests/ -m slow            # Include performance benchmarks (needs API key)
```

## Documentation Index
| File | Purpose |
|------|---------|
| `docs/architecture.md` | System design, components, data flow |
| `docs/decisions.md` | Architecture Decision Records |
| `docs/PROGRESS.md` | Phase tracking, completed/in progress/next |
| `docs/PROMPTS.md` | LLM prompt templates |
| `docs/TESTING.md` | Test strategy and coverage |
| `docs/DEMO.md` | Demo script with timing |
| `docs/TROUBLESHOOTING.md` | Common errors and solutions |
| `docs/logs.md` | Development changelog |
| `docs/bugs.md` | Bug log (discovered and fixed) |

## Environment Variables (`.env`)
- `LLM_PROVIDER=openai` — only `openai` is supported
- `OPENAI_API_KEY` — any OpenAI-compatible key
- `OPENAI_BASE_URL` — optional, for custom endpoints
- `OPENAI_MODEL` — optional, model name (default: `gpt-4o-mini`)
- `QUESTION_TIMER_SECONDS` — answer timeout (default: 180)
- `OLLAMA_API_KEY` — API key for the Ollama endpoint
- `OLLAMA_BASE_URL` — optional, Ollama endpoint URL (default: `http://localhost:11434/v1`)
- `OLLAMA_MODEL` — optional, Ollama model name (default: `llama3.2:3b`)

## Key Modules
| Module | Purpose |
|--------|---------|
| `config.py` | Env-based configuration |
| `session_state.py` | State machine with guarded transitions |
| `llm_client.py` | LLM calls for questions, evaluation, scorecard (structured-data pipeline) |
| `providers.py` | OpenAI and Ollama client factories |
| `industry_guardrail.py` | Industry-name classification via Ollama |
| `scoring.py` | Score calculation, radar chart, and deterministic stats (6 new functions) |
| `prompts.py` | LLM prompt templates |
| `export.py` | Markdown and PDF export |
| `timer.py` | Per-question countdown timer |
| `fallback_data.py` | Static questions when LLM is unavailable |
| `schemas.py` | Pydantic v2 data models |
