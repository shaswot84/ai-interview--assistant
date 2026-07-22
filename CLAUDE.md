# AI Interview Assistant — Claude Project Context

## Overview
Personalised mock interview app powered by an OpenAI-compatible LLM. Built with Chainlit, Pydantic, and Plotly.

## Stack
- **Python 3.11** | **uv** (package manager)
- **Chainlit** (UI framework)
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
- `Evaluation` has `score_reasons: dict[str, str]` and `confidence: float` (0.0–1.0) in addition to `scores`
- EVALUATION_PROMPT is assembled from 5 reusable components: system prompt, general rules, rubric, feedback instructions, output schema
- `get_evaluation_prompt()` and `get_question_prompt()` both accept a `UserProfile` with optional `interviewer_style` to inject style-specific persona
- `scoring.calculate_question_score()` now accepts `question_type: str` for per-type weighted scoring; uses `TYPE_DIMENSION_WEIGHTS` dict
- `llm_client.generate_follow_up()` creates adaptive follow-up questions; falls back to "Can you go deeper on that?"
- `UserProfile` has optional `interviewer_style: InterviewerStyle` (default: DEFAULT)

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
uv run pytest tests/ -v                 # 97 tests, all green
uv run pytest tests/ --runslow          # Include performance benchmarks (needs API key)
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
| `llm_client.py` | LLM calls for questions, evaluation, scorecard |
| `providers.py` | OpenAI and Ollama client factories |
| `industry_guardrail.py` | Industry-name classification via Ollama |
| `scoring.py` | Score calculation and radar chart |
| `prompts.py` | LLM prompt templates |
| `export.py` | Markdown and PDF export |
| `timer.py` | Per-question countdown timer |
| `fallback_data.py` | Static questions when LLM is unavailable |
| `schemas.py` | Pydantic v2 data models |
