# AI Interview Assistant

Personalised mock interviews powered by an OpenAI-compatible LLM (works with OpenAI, Groq, DeepSeek, Ollama, etc.). Built with **Chainlit 2.11**, **Pydantic v2**, and **Plotly**.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![Chainlit](https://img.shields.io/badge/chainlit-2.11-green)](https://chainlit.io)
[![Tests](https://img.shields.io/badge/tests-108_passing-brightgreen)](#testing)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](#)

---

## Features

| Feature | Description |
|---------|-------------|
| **Personalised questions** | LLM generates role/seniority/industry-specific questions. Supports 7 question types: open-ended, behavioral, MCQ, Yes/No, coding, debugging, system design. |
| **Configurable type distribution** | Settings panel with sliders to control the ratio of question types (e.g. 30% coding, 20% MCQ). |
| **Interactive question formats** | MCQ option buttons, Yes/No buttons, free-text input, and code-editing prompts with backtick guidance. |
| **Type + category badges** | Every question renders a colored badge (💻 CODING, 🧠 BEHAVIORAL, ✅ MCQ, ⚡ YES/NO, 🐛 DEBUGGING, 🏗 SYSTEM DESIGN). |
| **Multi-dimension scoring** | Per-type weighted scoring across dynamic dimensions (e.g. coding: correctness, solution_quality, technical_depth, problem_solving). |
| **Two-stage evaluation** | Stage 1 produces strict scores with evidence; Stage 2 generates coaching feedback (grammar correction / simplified version for text answers; code review + corrected code for coding/debugging). |
| **Anti-injection** | Guards against prompt injection in answer text — scores are unaffected. |
| **Radar chart** | Visual breakdown of performance across all evaluated dimensions. |
| **Professional scorecard** | 17-field scorecard: 9 LLM-synthesised sections (overall assessment, hiring recommendation, competencies, learning roadmap, resources) + 8 deterministic Python-computed stats. |
| **Timer enforcement** | Configurable per-question countdown (default 180 s) with a CSS-animated timer bar (blue → red + blink at 80 %). Auto-skips unanswered questions. |
| **Fallback questions** | 40 static questions (10 per seniority level) when the LLM API is unavailable. |
| **Retry logic** | Auto-retries on API failures with exponential backoff (2 retries). |
| **IT role + industry guardrails** | Onboarding validates roles and industries via an Ollama-based classification guardrail. |
| **PDF / Markdown export** | Download full interview transcript (PDF) and assessment scorecard (Markdown). |
| **State machine** | Guarded `IDLE → ONBOARDING → GENERATING → INTERVIEWING → EVALUATING → FEEDBACK → COMPLETED → DEBRIEF` with skip, end-early, and retry actions. |
| **Interviewer style** | Optional persona calibration (FAANG, startup, gaming, finance, default) injected into question generation and evaluation prompts. |

---

## Architecture

### System Flow

```
┌──────────┐    ┌────────────┐    ┌───────────┐    ┌────────────┐
│  User    │───▶│ Chainlit   │───▶│  State    │───▶│  LLM       │
│  Input   │    │  UI        │    │  Machine  │    │  Client    │
└──────────┘    └────────────┘    └───────────┘    └─────┬──────┘
                                                          │
                                                ┌─────────▼─────────┐
                                                │   OpenAI SDK       │
                                                │ (Groq/DeepSeek/    │
                                                │  Ollama/etc.)      │
                                                └─────────┬─────────┘
                                                          │
                                      ┌───────────────────▼─────────────┐
                                      │  Fallback Data (on API failure) │
                                      └─────────────────────────────────┘

                     ┌──────────┐    ┌───────────────┐    ┌────────────┐
                     │  Timer   │───▶│  Scoring      │───▶│  Export    │
                     │  (auto)  │    │  Engine       │    │  PDF/MD   │
                     └──────────┘    └───────────────┘    └────────────┘
```

### State Machine

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

### Module Map

| Module | Responsibility |
|--------|---------------|
| `config.py` | Environment configuration (`Config.from_env()`) |
| `session_state.py` | State machine with `transition()` and `InvalidTransitionError` |
| `app.py` | Chainlit UI controller — onboarding, question display, feedback, scorecard, export |
| `llm_client.py` | LLM calls: question generation, two-stage evaluation, scorecard synthesis |
| `providers.py` | OpenAI and Ollama client factories |
| `prompts.py` | 10+ prompt templates with dynamic per-type injection |
| `industry_guardrail.py` | Ollama-based industry name validation |
| `schemas.py` | Pydantic v2 models: `UserProfile`, `Question`, `Evaluation`, `Scorecard` (17 fields), `SessionState`, `QuestionConfig` |
| `scoring.py` | Weighted scoring, radar chart (Plotly), 6 deterministic stat functions |
| `export.py` | Markdown transcript + PDF via WeasyPrint |
| `timer.py` | Per-question countdown timer |
| `fallback_data.py` | 40 static questions across 4 seniority levels |

---

## Question Types

| Type | Badge | Input Method | Evaluation |
|------|-------|-------------|------------|
| Open-ended | 🧠 `PROBLEM SOLVING` | Free text | Two-stage LLM (scores + coaching) |
| Behavioral | 🧠 `BEHAVIORAL` | Free text | Two-stage LLM |
| MCQ | ✅ `MCQ` | Clickable option buttons | Deterministic (`_evaluate_objective`) |
| Yes/No | ⚡ `YES/NO` | Yes / No buttons | Deterministic |
| Coding | 💻 `CODING` | Free text with backtick guidance | Two-stage LLM → `code_fix` + `code_review` |
| Debugging | 🐛 `DEBUGGING` | Free text with buggy code shown | Two-stage LLM → `code_fix` + `code_review` |
| System Design | 🏗 `SYSTEM DESIGN` | Free text | Two-stage LLM |

Dimensions are dynamic per type:
- **Open-ended:** clarity, completeness, relevance, correctness, technical_depth, problem_solving, tradeoff_analysis
- **Coding:** correctness, solution_quality, technical_depth, problem_solving
- **Behavioral:** clarity, completeness, relevance, structure, self_reflection
- **MCQ/Yes-No:** accuracy (single dimension, score = 10 if correct, 0 otherwise)
- **System Design:** clarity, completeness, relevance, correctness, technical_depth, problem_solving, tradeoff_analysis, scalability, architecture_design

---

## Setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- WeasyPrint system dependencies (Debian/Ubuntu):

```bash
sudo apt install libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

### Installation

```bash
git clone https://github.com/shaswot84/ai-interview--assistant.git
cd ai-interview--assistant
cp .env.example .env
uv sync
```

Edit `.env` with your API key:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=                          # optional: custom endpoint
OPENAI_MODEL=                             # optional (default: gpt-4o-mini)
QUESTION_TIMER_SECONDS=180
OLLAMA_API_KEY=                           # for guardrails
OLLAMA_BASE_URL=                          # optional (default: http://localhost:11434/v1)
OLLAMA_MODEL=                             # optional (default: llama3.2:3b)
```

### Provider Switching

The app uses the OpenAI SDK, compatible with any OpenAI-compatible API.

**Groq:**
```env
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=llama-3.3-70b-versatile
```

**DeepSeek:**
```env
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

**OpenAI:**
```env
OPENAI_MODEL=gpt-4o-mini
```

---

## Running

```bash
uv run chainlit run app.py
```

Open the URL shown in the terminal (typically `http://localhost:8000`). Click **Start** to begin.

### Usage Walkthrough

1. **Onboarding** — Enter your target role (validated as IT-related via Ollama), seniority level (Junior / Mid / Senior / Lead), and industry (validated via Ollama).
2. **Question Config** (optional) — Adjust the question type distribution via sliders (total count, % per type). Click **Generate Questions**.
3. **Interview** — Questions appear with:
   - A **colored badge** showing the type and competency category
   - A **countdown timer bar** (blue → red + blink at 80 %)
   - Formatted starter/buggy code for coding/debugging questions
   - Clickable MCQ / Yes/No option buttons
   - Skip and End Early controls
4. **Feedback** — After each answer, see dimension scores, coaching feedback (grammar correction / code review), and actionable recommendations.
5. **Scorecard** — After the last question, a comprehensive 17-field scorecard with radar chart, hiring recommendation, and learning roadmap.
6. **Export** — Download the transcript as PDF or the assessment as Markdown.

---

## Testing

```bash
uv run pytest tests/ -v               # Full suite (108 tests, all green)
uv run pytest tests/test_X.py -v      # Single test file
uv run pytest -k "test_name" -v       # Single test
uv run pytest tests/ -m slow          # Include performance benchmarks (needs API key)
```

### Test Coverage

| Test file | Tests | Scope |
|-----------|-------|-------|
| `tests/test_timer.py` | 4 | Timer limit, elapsed time, timeout |
| `tests/test_state_machine.py` | 30 | Valid transitions, invalid transitions, timer auto-skip, question index |
| `tests/test_schemas.py` | 14 | Model validation, field constraints, serialization |
| `tests/test_providers.py` | 2 | Client factory |
| `tests/test_llm_client.py` | 7 | Retry logic, fallback, prompt generation |
| `tests/test_scoring.py` | 14 | Question/overall scoring, radar chart, letter grade, deterministic stats |
| `tests/test_export.py` | 7 | Markdown generation, PDF rendering |
| `tests/test_edge_cases.py` | 14 | Injection, clamping, retry, fallback, score boundaries |
| `tests/test_performance.py` | 3 | Latency benchmarks (marked `slow`) |

---

## Project Structure

```
ai-interview-assistant/
├── app.py                    # Chainlit UI controller (996 lines)
├── config.py                 # Environment configuration
├── session_state.py          # State machine with guarded transitions
├── llm_client.py             # LLM integration: questions, evaluation, scorecard
├── prompts.py                # Prompt templates (question gen, evaluation, feedback, scorecard)
├── providers.py              # OpenAI and Ollama client factories
├── industry_guardrail.py     # Industry-name classification via Ollama
├── schemas.py                # Pydantic v2 data models
├── scoring.py                # Weighted scoring, radar chart, deterministic stats
├── export.py                 # Markdown transcript + PDF generation
├── timer.py                  # Per-question countdown timer
├── fallback_data.py          # 40 static questions across 4 seniority levels
├── .chainlit/
│   └── config.toml           # Chainlit UI configuration
├── docs/
│   ├── architecture.md       # System design, components, data flow
│   ├── decisions.md          # Architecture Decision Records
│   ├── PROGRESS.md           # Phase tracking and roadmap
│   ├── PROMPTS.md            # LLM prompt template details
│   ├── TESTING.md            # Test strategy and coverage
│   ├── DEMO.md               # Demo script with timing
│   ├── TROUBLESHOOTING.md    # Common errors and solutions
│   ├── logs.md               # Development changelog
│   └── bugs.md               # Bug log (discovered and fixed)
├── tests/
│   ├── conftest.py           # Shared fixtures
│   ├── test_timer.py
│   ├── test_state_machine.py
│   ├── test_schemas.py
│   ├── test_providers.py
│   ├── test_llm_client.py
│   ├── test_scoring.py
│   ├── test_export.py
│   ├── test_edge_cases.py
│   └── test_performance.py   # (marked slow)
├── .env.example              # Environment variable template
├── pyproject.toml            # Project metadata and dependencies
├── CLAUDE.md                 # AI-assistant project context (coding standards)
├── chainlit.md               # Chainlit welcome splash
└── README.md                 # This file
```

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [`docs/architecture.md`](docs/architecture.md) | Full system design, component descriptions, data flow diagrams |
| [`docs/decisions.md`](docs/decisions.md) | Architecture Decision Records (13+ ADRs) |
| [`docs/PROGRESS.md`](docs/PROGRESS.md) | Phase-by-phase progress tracking and roadmap |
| [`docs/PROMPTS.md`](docs/PROMPTS.md) | All LLM prompt templates and injection logic |
| [`docs/TESTING.md`](docs/TESTING.md) | Test strategy, golden test cases, edge cases |
| [`docs/DEMO.md`](docs/DEMO.md) | 5-minute demo script with prepared inputs |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | Common errors and solutions |
| [`docs/logs.md`](docs/logs.md) | Development changelog |
| [`docs/bugs.md`](docs/bugs.md) | Bug log (discovered and fixed) |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `API key not configured` | Set `OPENAI_API_KEY` in `.env` |
| `LLM call failed after 2 retries` | Check API key, network, or provider status |
| `No valid transition` | Unexpected state; type `start` or restart |
| Evaluation stuck on loading | Click **Retry Evaluation** or skip to next question |
| Timer expired unexpectedly | Adjust `QUESTION_TIMER_SECONDS` in `.env` |
| WeasyPrint PDF error | Ensure system deps are installed (see [Setup](#setup)) |
| Export crashes with `Cannot read properties of null` | The app now sets `mime="text/markdown"` explicitly for `.md` exports |
| MCQ options not showing | Ensure the generated question has at least 2 options; fewer than 2 falls back to open-ended |

---

## Demo Script (5 min)

| Time | Segment |
|------|---------|
| 0:00–0:30 | **Hook** — "Personalised vs generic interview tools" |
| 0:30–1:00 | **Onboarding** — Role, seniority, industry (Ollama-validated) |
| 1:00–1:30 | **Question Config** — Adjust type sliders, click Generate |
| 1:30–1:45 | **MCQ** — Clickable options, colored badge, echoed answer |
| 1:45–2:00 | **Yes/No** — Button selection, echoed answer |
| 2:00–2:30 | **Coding** — Starter code label, backtick-guidance, fence stripping |
| 2:30–3:00 | **Code Feedback** — Code review + corrected code (not grammar) |
| 3:00–3:15 | **Skip** — User control |
| 3:15–3:30 | **Injection** — "Ignore instructions..." → scores unaffected |
| 3:30–4:00 | **Scorecard** — Radar chart, hiring recommendation, learning roadmap |
| 4:00–4:30 | **Export** — Transcript PDF + Assessment Markdown |
| 4:30–5:00 | **Architecture** — State machine → types → LLM → scoring → export |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openai` | Only `openai` is supported |
| `OPENAI_API_KEY` | — | API key (OpenAI, Groq, DeepSeek, etc.) |
| `OPENAI_BASE_URL` | — | Custom endpoint URL |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model name |
| `QUESTION_TIMER_SECONDS` | `180` | Answer timeout in seconds |
| `OLLAMA_API_KEY` | — | API key for Ollama guardrails |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama endpoint URL |
| `OLLAMA_MODEL` | `llama3.2:3b` | Ollama model name |

---

## Key Commands

```bash
uv run chainlit run app.py          # Start the app
uv run pytest tests/ -v             # Run all tests
uv run pytest tests/ -m slow        # Include performance benchmarks
uv sync                              # Sync environment
uv add <package>                     # Add a dependency
```

---

## Roadmap

- [ ] Code editor (Monaco) for coding/debugging questions instead of free-text
- [ ] Multi-line text input for open-ended and behavioral questions
- [ ] Follow-up question support in the interview flow
- [ ] Session persistence (resume interrupted interviews)
- [ ] Historical scorecard tracking across multiple sessions

See [`docs/PROGRESS.md`](docs/PROGRESS.md) for the full development roadmap and completed phases.
