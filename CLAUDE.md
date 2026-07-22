# AI Interview Assistant — Claude Project Context

## Overview
Personalised mock interview app powered by an OpenAI-compatible LLM. Built with Chainlit, Pydantic, and Plotly.

## Stack
- **Python 3.11** | **uv** (package manager)
- **Chainlit** (UI framework)
- **OpenAI SDK** (works with OpenAI, Groq, DeepSeek, etc.)
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

## State Machine
```
IDLE → ONBOARDING → GENERATING → INTERVIEWING → EVALUATING → FEEDBACK → COMPLETED → DEBRIEF
```

## Key Commands
```bash
uv run pytest tests/ -v           # Run all tests
uv run pytest tests/test_X.py -v  # Run a specific test file
uv run chainlit run app.py         # Start the app
uv add <package>                   # Add a dependency
uv sync                            # Sync environment
```

## Current Phase: 5 — Edge Cases, Testing & Polish

## Tests
```bash
uv run pytest tests/ -v                 # 93 tests, all green
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
