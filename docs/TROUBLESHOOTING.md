# Troubleshooting

## Common Errors

### `openai.AuthenticationError: Incorrect API key`
- Check `OPENAI_API_KEY` in `.env` is correct
- Verify the key works with the provider (OpenAI, Groq, DeepSeek, etc.)
- If using Groq, ensure `OPENAI_BASE_URL=https://api.groq.com/openai/v1` is set

### `openai.NotFoundError: The model does not exist`
- Check `OPENAI_MODEL` matches a model available at your provider
- Groq example: `llama-3.3-70b-versatile`
- OpenAI example: `gpt-4o-mini`
- DeepSeek example: `deepseek-chat`

### Tests fail: `AssertionError: OPENAI_API_KEY is not set or is placeholder`
- Copy `.env.example` to `.env` and fill in your real API key
- Or check `.env` exists in the project root directory

### `ModuleNotFoundError: No module named '...'`
- Run `uv sync` to install all dependencies from lockfile
- Or `uv add <package>` to add a new dependency

### Chainlit app won't start
- Run `uv run chainlit run app.py` from the project root
- Ensure all imports in `app.py` are valid (placeholder files may have no content yet)

### HTML/CSS in message content is shown as raw code instead of rendering
- Set `unsafe_allow_html = true` in `.chainlit/config.toml` under `[features]`
- Run `chainlit run app.py` — the config is loaded automatically from the `.chainlit` directory

### Chat input stuck on "Stop task" after a message is sent
- A synchronous blocking call (e.g. `generate_questions()`, `evaluate_answer()`) is running in the async handler
- Wrap the call with `await asyncio.to_thread(your_sync_fn, arg1, arg2)` to offload it to a thread pool
- Example: `questions = await asyncio.to_thread(generate_questions, state.profile)`

## Provider Quirks

### Groq
- Base URL: `https://api.groq.com/openai/v1`
- Models: `llama-3.3-70b-versatile`, `mixtral-8x7b-32768`, `gemma2-9b-it`
- Free tier: rate-limited but functional
- Key format: `gsk_...`

### DeepSeek
- Base URL: `https://api.deepseek.com`
- Models: `deepseek-chat`, `deepseek-coder`
- Key format: `sk-...`

### OpenAI
- Base URL: not required (default)
- Models: `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`
- Key format: `sk-...`

### Settings panel doesn't appear / config changes not reflected
- The settings panel (gear icon in the message bar) is sent **after** you fill in role, seniority, and industry — during the "⚙️ Configure your interview" step
- Adjust the sliders, then click **Generate Questions** to proceed
- If settings don't take effect, verify `@cl.on_settings_update` is not raising errors (check terminal logs)
- The config normalises percentages to sum to 100%, so individual slider values are proportional, not absolute

### Role validation keeps rejecting my input
- The LLM classifies the role; if it's clearly IT-related (e.g. "site reliability engineer", "backend developer"), the classification should pass
- If the API call fails, `validate_role()` falls back to `True` (allow) — so failures should not block the flow
- Try being more specific: "Backend Engineer" instead of just "Engineer"

### Industry validation keeps rejecting my input
- The Ollama classifier (`validate_industry()`) checks whether the input is a recognised industry name
- Acceptable examples: FinTech, Healthcare, Education, Retail, Manufacturing, E-commerce
- Rejected examples: job titles ("Backend Engineer"), random text ("banana", "I like pizza"), numbers
- If the Ollama API is unreachable, the app shows "Industry validation is temporarily unavailable. Please try again." — check `OLLAMA_BASE_URL` and `OLLAMA_API_KEY` in `.env`
- If the API call succeeds (HTTP 200) but the error persists, the model probably returned non-JSON text. Check the app logs for the raw Ollama response — the `_parse_boolean_response()` function tries strict JSON first, then a regex fallback; if both fail, a `RuntimeError` is raised.

### `KeyError: '\n  "clarity"'` or similar format errors
- The `EVALUATION_PROMPT` contains literal JSON braces `{`/`}` that must be escaped as `{{`/`}}` for Python's `str.format()`
- Check that all non-placeholder braces in prompt templates are doubled
- `QUESTION_GEN_PROMPT` already uses `{{`/`}}` — follow that pattern when editing other prompts

### Ollama
- Base URL: `http://localhost:11434/v1` (local) or a hosted OpenAI-compatible endpoint
- Models: `llama3.2:3b`, `llama3.1:8b`, `mistral`, `gemma4:31b-cloud`, etc.
- API key: configurable via `OLLAMA_API_KEY`; local Ollama may accept any non-empty string
- Key format: depends on the endpoint provider
- **Known limitation:** Ollama's `/v1/chat/completions` endpoint does **not** support the `response_format={"type": "json_object"}` parameter. The guardrails (`validate_role`, `validate_industry`) omit this parameter and instead use a two-stage parser (strict JSON → regex fallback) to handle models that return freeform text around the JSON object.

## Debugging Tips
- Set `QUESTION_TIMER_SECONDS=9999` during development to prevent timeouts
- Check the Chainlit debug panel (usually available in the UI)
- Run tests with `-v` (verbose) to see detailed failure info
- For LLM issues, test the API key directly: `uv run python -c "from openai import OpenAI; client=OpenAI(); print(client.chat.completions.create(model='gpt-4o-mini', messages=[{'role':'user','content':'hi'}], max_tokens=5).choices[0].message.content)"`
