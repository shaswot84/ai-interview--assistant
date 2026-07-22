# Architecture Decision Records

## ADR-001: OpenAI-compatible Only (no Anthropic)
**Date:** 2026-07-19
**Status:** Accepted
**Context:** Need to support multiple LLM backends while keeping complexity low.
**Decision:** Use only the OpenAI Python SDK with configurable `base_url`. Any OpenAI-compatible provider (OpenAI, Groq, DeepSeek, Together, etc.) works out of the box.
**Rationale:** Groq, DeepSeek, and virtually all popular alternatives speak the OpenAI API format. Maintaining a separate Anthropic provider doubles the integration surface for no practical benefit.
**Consequences:** Lose native Claude features (extended thinking, prompt caching). Acceptable trade-off since the app only needs basic chat completions with JSON output.

## ADR-002: Chainlit over Streamlit
**Date:** 2026-07-19
**Status:** Accepted
**Context:** Need a conversational UI framework for a multi-turn interview flow.
**Decision:** Use Chainlit.
**Rationale:** Built for conversational AI apps with native chat messages, timers, and multi-step flows. Streamlit would require building chat infrastructure from scratch.
**Consequences:** Smaller ecosystem than Streamlit; but sufficient for this project's needs.

## ADR-003: uv over pip/poetry
**Date:** 2026-07-19
**Status:** Accepted
**Context:** Need fast, reliable Python package management.
**Decision:** Use `uv`.
**Rationale:** Fast resolver, single-file lock, built-in virtualenv management, drop-in replacement for pip/venv.
**Consequences:** Requires `uv` to be installed separately; otherwise identical workflow.

## ADR-004: Weighted Scoring Formula
**Date:** 2026-07-19
**Status:** Accepted
**Context:** Need to produce a single per-question score from multiple evaluation dimensions.
**Decision:** Weighted average: clarity 0.15, completeness 0.25, relevance 0.20, grammar 0.10, impact 0.30.
**Rationale:** Impact and completeness are the strongest signals of interview performance. Grammar is least important.
**Consequences:** Tuning weights may require iteration after user testing.

## ADR-005: Server-Side Timer Enforcement
**Date:** 2026-07-19
**Status:** Accepted
**Context:** Need to enforce time limits per question in the interview.
**Decision:** Check elapsed time on each user action (submit, skip). Auto-convert submit to `timeout_skip` when expired. No client-side countdown is authoritative.
**Rationale:** Simplest correct approach — no websocket complexity, server is source of truth. Client-side timer is purely visual.
**Consequences:** Timer is accurate to within the request-response cycle, not millisecond-precise. Sufficient for MVP.

## ADR-006: Static Fallback Questions
**Date:** 2026-07-19
**Status:** Accepted
**Context:** App must work when LLM API is unavailable.
**Decision:** Hardcode ~10 questions per (seniority × industry) pair in `fallback_data.py`.
**Rationale:** Static data is always available, no network dependency, zero latency.
**Consequences:** Limited variety; questions don't adapt to the user's specific role. Acceptable for MVP.

## ADR-007: Pydantic v2 over Plain Dataclasses
**Date:** 2026-07-19
**Status:** Accepted
**Context:** Need structured validation for LLM responses and user input.
**Decision:** Use Pydantic v2 models.
**Rationale:** Built-in validation (rejects invalid seniority, out-of-bounds scores), JSON schema generation for LLM response parsing, better error messages than dataclasses.
**Consequences:** Slightly heavier than dataclasses; but validation safety is worth the cost.

## ADR-008: Seniority-Persona Prompt Injection
**Date:** 2026-07-20
**Status:** Accepted
**Context:** Generated questions must match the candidate's seniority level (junior→fundamentals, lead→org-wide architecture).
**Decision:** Inject a `SENIORITY_PERSONAS` dict block into `QUESTION_GEN_PROMPT` based on the profile's seniority tier. Each persona lists focus areas, prohibited topics, and grading philosophy.
**Rationale:** A single prompt template with conditional persona injection is simpler than maintaining N separate prompts. The persona acts as a system-level instruction that shapes question difficulty and evaluation framing.
**Consequences:** Personas must be updated manually as the app evolves. Adding new seniority tiers requires updating both the dict and the enum.

## ADR-009: Per-Operation LLM Temperature
**Date:** 2026-07-20
**Status:** Accepted
**Context:** Question generation benefits from higher creativity (diverse questions), while evaluation and scorecard synthesis need lower temperature (consistent, deterministic scoring).
**Decision:** Three separate env-configurable temperatures: `GENERATION_TEMPERATURE` (default 0.9), `EVALUATION_TEMPERATURE` (default 0.3), `SCORECARD_TEMPERATURE` (default 0.3).
**Rationale:** A single temperature across all operations would force a compromise between creative question variety and scoring consistency. Separating them lets each operation use its optimal value.
**Consequences:** More env vars to document. Users unfamiliar with LLM temperature may need guidance on reasonable ranges.

## ADR-010: Configurable Question Types with Distribution
**Date:** 2026-07-21
**Status:** Accepted
**Context:** The default 3-technical + 2-behavioural question mix was rigid. Users need to customize the question types and their ratios.
**Decision:** Add a `QuestionType` enum (7 types: open_ended, behavioral, mcq, yes_no, coding, debugging, system_design), `QuestionConfig` model with `total_questions` and `distribution` (map of type to percentage), and a settings panel (`cl.ChatSettings`) gated after profile collection.
**Rationale:** A config-driven approach avoids per-type hardcoding in the prompt builder. The LLM prompt dynamically describes the requested distribution rather than enumerating types. The settings panel is gated (shown after profile, before generation) so the user has time to configure.
**Consequences:** The `QUESTION_GEN_PROMPT` now has two modes: default (backward-compatible 3+2) and config-driven (dynamic type mix). Fallback data maps unknown types to technical questions. Percentage sliders are normalized to sum to 100%.

## ADR-011: LLM-Based Role Validation
**Date:** 2026-07-21
**Status:** Accepted
**Context:** Need to ensure the user enters an IT-related role for the interview.
**Decision:** Use the LLM to classify the role as IT-related or not. A `validate_role()` function sends a classification prompt with temperature 0.
**Rationale:** Keyword-based matching is fragile and misses edge cases. LLM classification handles variations (e.g., "site reliability engineer") without maintaining an exhaustive keyword list.
**Consequences:** Slow path (one LLM call per attempt); falls back to `True` (allow) if the API call fails.

## ADR-012: Dynamic Per-Type Evaluation Dimensions
**Date:** 2026-07-22
**Status:** Accepted
**Context:** The original evaluator returned the same 9 dimensions (clarity, completeness, relevance, grammar, impact, technical_depth, architecture_design, problem_solving, tradeoff_analysis) for every question type. This made no sense for MCQ (a simple correct/incorrect check), coding questions (no "architecture_design" or "grammar"), or Yes/No questions.
**Decision:** Replace the fixed 9-field `Evaluation` schema with `scores: dict[str, int]` — each question type defines its own set of relevant dimensions. MCQ/Yes/No use deterministic `_evaluate_objective()` returning just `correctness`. LLM-evaluated types (open_ended, behavioral, coding, debugging, system_design) each have their own dimension set defined in `TYPE_DIMENSIONS`. The LLM prompt lists only the relevant dimensions for that type.
**Rationale:** Dynamic dimensions eliminate nonsensical scores (e.g. "architecture_design: 10" for "Is Python dynamically typed?"). Each question type is evaluated on criteria that actually measure what the question is designed to assess. Deterministic evaluation for objective types removes LLM cost and latency.
**Consequences:** Scoring is now equal-weighted (average of present dimensions × 10) rather than using per-dimension weights. Radar chart dynamically adapts to whatever dimension keys appear across evaluations. Backward compatibility is broken — any code reading `eval_.clarity` must now use `eval_.scores["clarity"]`. All consumers updated in the same commit.

## ADR-013: Ollama-Based Onboarding Guardrails
**Date:** 2026-07-22
**Status:** Accepted
**Context:** Two onboarding fields (role, industry) need lightweight classification. A whitelist is too brittle for role validation (infinite possible IT roles), and the industry question doesn't need LLM-level reasoning. However, using the main LLM provider (Groq) for both incurs API costs/quota and couples onboarding to the main provider.
**Decision:** Use a separate Ollama endpoint for both `validate_role()` and `validate_industry()`. The Ollama client (`get_ollama_client()` in `providers.py`) is an OpenAI-compatible client configured via `OLLAMA_API_KEY`, `OLLAMA_BASE_URL`, and `OLLAMA_MODEL`. Both guardrails call Ollama with `temperature=0` and `response_format=json_object`, returning only a boolean.
**Rationale:** Ollama can run locally (zero cost, zero quota) or via a hosted OpenAI-compatible endpoint. Decoupling onboarding classifiers from the main LLM provider avoids rate-limit contention and lets each provider be configured independently.
**Consequences:** Two separate LLM endpoints to maintain. If Ollama is unreachable, `validate_role()` falls back to `True` (allow) and `validate_industry()` raises `RuntimeError` (caught by the onboarding loop for a retry prompt).
