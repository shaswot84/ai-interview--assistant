# Bug Log

## 2026-07-19

### 1. `cl.Action` missing `payload` field

**File:** `app.py` (all `cl.Action(...)` calls)  
**Symptom:** `ValidationError: payload Field required` on startup  
**Root cause:** Chainlit 2.x requires a `payload: Dict` field in `Action`. The old 1.x API used `value=` instead.  
**Fix:** Replaced `value="xxx"` with `payload={}` in every `cl.Action(...)` call. 

---

### 2. State never transitioned to `ONBOARDING`

**File:** `app.py:111` — `_show_onboarding()`  
**Symptom:** After typing "start", the onboarding prompt appeared, but any answer showed "Type start to begin your interview." — infinite loop.  
**Root cause:** `_show_onboarding()` never called `transition(state, "start")`, so `state.current_state` remained `IDLE`. Every subsequent message matched the `IDLE` branch.  
**Fix:** Added `transition(state, "start")` at the top of `_show_onboarding()`.

---

### 3. Duplicate `"start"` transition in `_finalize_onboarding`

**File:** `app.py:155` — `_finalize_onboarding()`  
**Symptom:** `InvalidTransitionError: No valid transition from ONBOARDING with action 'start'` after completing onboarding.  
**Root cause:** After fix #2, the state was already `ONBOARDING`, but `_finalize_onboarding` still called `transition(state, "start")` (valid only from `IDLE`).  
**Fix:** Removed the stale `transition(state, "start")` call — only `transition(state, "submit_profile")` is needed.

---

### 4. `current_question_index` never incremented

**File:** `app.py:46` — `on_next_question` callback  
**Symptom:** After viewing feedback for question N and clicking "Next Question", question N was shown again.  
**Root cause:** `transition(state, "next_question")` changes the state to `INTERVIEWING` and resets the timer, but never increments `current_question_index`.  
**Fix:** Added `state.current_question_index += 1` before `transition(state, "next_question")`.

---

### 5. Invalid transition in `on_retry_evaluation`

**File:** `app.py:80` — `on_retry_evaluation` callback  
**Symptom:** Evaluation retry failed silently (exception logged, no user feedback).  
**Root cause:** The callback called `transition(state, "evaluation_done")`, but the state was already at `FEEDBACK` — this action is only valid from `EVALUATING`.  
**Fix:** Removed the stale `transition(state, "evaluation_done")` call.

---

### 6. `Plotly.send()` missing `for_id` in Chainlit 2.x

**File:** `app.py:329` — `_show_scorecard()`
**Symptom:** `Element.send() missing 1 required positional argument: 'for_id'` when displaying the radar chart.
**Root cause:** Chainlit 2.x `Element.send()` requires `for_id: str`. The old pattern `await cl.Plotly(...).send()` no longer works — elements must be attached to a `Message` via the `elements` parameter, which auto-sends them with the correct `for_id`.
**Fix:** Changed `await cl.Plotly(...).send()` to `await cl.Message(content=..., elements=[cl.Plotly(...)]).send()`.

---

### 7. `cl.File()` positional arg mismatch in Chainlit 2.x

**File:** `app.py:62` — `on_export_pdf`, `on_export_md`
**Symptom:** `Value error, Must provide url, path or content to instantiate element` when exporting.
**Root cause:** The first positional arg to `cl.File(path, ...)` maps to `thread_id` (the first dataclass field), not `path`. Also `File.send()` needs `for_id` like other elements.
**Fix:** Use `cl.File(path=path, name=...)` as keyword args, and wrap in `cl.Message(content="", elements=[...]).send()`.

---

### 8. Onboarding `ONBOARDING` state never exited after `_ask_next_field`

**File:** `app.py:124` — `_ask_next_field()`
**Symptom:** Onboarding fields were collected via plain messages and `on_message`, but the state machine was never reached for free-text fields after switching to blocking `AskUserMessage`/`AskActionMessage`.
**Root cause:** Mixing blocking asks (`AskUserMessage`) with async `on_message`-based input caused the `ONBOARDING` branch in `on_message` to intercept responses.
**Fix:** Replaced the entire onboarding flow — `_ask_next_field` now uses `AskUserMessage` (role, industry) and `AskActionMessage` (seniority with 4 buttons). Removed the `ONBOARDING` case from `on_message` entirely.

---

## 2026-07-20

### 9. HTML/CSS timer bar rendered as literal text

**File:** `.chainlit/config.toml:27`, `app.py:20-30` (`_timer_bar_html`)
**Symptom:** The `<div>` and `<style>` tags in the timer bar were displayed as escaped code text instead of rendering as a visual bar.
**Root cause:** Chainlit 2.x defaults `unsafe_allow_html = false`, which escapes all HTML in message content. CSS `<style>` tags and inline HTML were passed through as literal text.
**Fix:** Set `unsafe_allow_html = true` in `.chainlit/config.toml`. HTML in `Message(content=...)` is now processed by the browser's DOM.

---

### 10. Chat input freezes on "Generating interview questions..."

**File:** `app.py:203-206` — `_handle_generating()`
**Symptom:** After the "Generating interview questions..." message is sent, the chat input stays stuck on "Stop task" and the user cannot type.
**Root cause:** `generate_questions()` is a synchronous function that makes a blocking HTTP call (OpenAI SDK). When called directly inside an async Chainlit handler, it blocks the entire event loop, so the UI never receives the "task done" signal.
**Fix:** Wrapped the call with `await asyncio.to_thread(generate_questions, state.profile)` — runs the blocking call in a thread pool, freeing the event loop to update the UI.

---

## 2026-07-21

### 11. `EVALUATION_PROMPT` `str.format()` `KeyError`

**File:** `prompts.py:429` — `EVALUATION_PROMPT`
**Symptom:** `KeyError: '\n  "clarity"'` when calling `get_evaluation_prompt()`.
**Root cause:** The JSON template at the end of `EVALUATION_PROMPT` used unescaped `{` and `}` characters. Python's `str.format()` interpreted them as format placeholders.
**Fix:** Escaped the literal braces as `{{` and `}}` in the JSON template. The `QUESTION_GEN_PROMPT` already had this correct.

---

### 12. Settings panel showed at wrong time — never gated

**File:** `app.py` — `_run_interview_core()`
**Symptom:** The question-configuration `cl.ChatSettings` was `send()` during the seniority step, but the flow proceeded to question generation immediately after the seniority button click — the user had no time to open and adjust the panel, so config always stayed at defaults.
**Root cause:** The `settings.send()` was placed before the seniority `AskActionMessage`, and there was no blocking action between config display and generation.
**Fix:** Removed the premature `settings.send()` from the seniority step. Added a gated configuration step after the full profile is assembled: `_build_question_settings().send()` + `AskActionMessage("Generate Questions")` that blocks until the user confirms.

---

### 13. `_get_state()` function definition lost during edit

**File:** `app.py:63-70`
**Symptom:** `NameError: name '_get_state' is not defined` on startup.
**Root cause:** When `_get_question_config()` was inserted, the `def _get_state()` line was accidentally deleted, leaving only its docstring and body orphaned.
**Fix:** Restored the `def _get_state()` function definition above its docstring.

---

### 14. `cl.Action` syntax error — unclosed brace

**File:** `app.py:413` — seniority action buttons
**Symptom:** `SyntaxError` when running the app.
**Root cause:** Typo: `"Lead")` instead of `"Lead"}` in the payload dict.
**Fix:** Changed `payload={"value": "Lead")` to `payload={"value": "Lead"}`.

---

## 2026-07-21

### 15. Feedback "Next Question" / "End Early" buttons disabled after answering

**File:** `app.py:379-384` — `_show_feedback()`, `app.py:297` — `_show_question()`
**Symptom:** After answering a question, the feedback message's "Next Question" and "End Early" action buttons appear disabled (unclickable).
**Root cause:** The `end_early` action name was reused on both the question message (`_show_question`, line 297) and the feedback message (`_show_feedback`, line 384). Chainlit disables actions across messages with duplicate names, causing the feedback's `end_early` (and potentially adjacent actions) to be non-functional.
**Fix:** Renamed feedback-specific actions to unique names: `_feedback_next` (instead of `next_question`), `_feedback_finish` (instead of `finish`), and `_feedback_end_early` (instead of `end_early`). Added corresponding callbacks `on_feedback_next`, `on_feedback_finish`, `on_feedback_end_early` that replicate the original transition logic.

---

### 16. All action buttons disabled after any answer interaction

**File:** `app.py` — `_show_question()`, `_show_feedback()`
**Symptom:** After clicking any button (MCQ option, Skip, etc.), all subsequent action buttons on both question and feedback messages become disabled and unclickable.
**Root cause:** Chainlit's built-in mechanism disables `cl.Action` buttons once the conversation progresses past the message that owns them. With the previous approach (separate `cl.Message` + registered `@cl.action_callback` handlers), any new message from the assistant would cause all prior action buttons to become invalid. The feedback action name rename (bug #15) only fixed duplicate-name collisions within the same message, not the cross-message disable behavior.
**Fix:** Replaced all question and feedback action buttons with `cl.AskActionMessage` — a blocking action message that prevents the UI thread from progressing until the user clicks a button. This bypasses Chainlit's automatic disable mechanism because the conversation cannot advance past the AskActionMessage until an action is taken. Question content is sent as a permanent `cl.Message` (remains visible), then a separate `AskActionMessage` carries only the interactive buttons. Feedback also uses `AskActionMessage` with inline handling (no `@cl.action_callback` registration needed).

---

## 2026-07-23

### 17. Export Assessment crashes: `Cannot read properties of null (reading 'startsWith')`

**File:** `app.py:238` — `on_export_md()`
**Symptom:** Clicking "Export Assessment" on the scorecard shows a JavaScript error and the file is not sent.
**Root cause:** `cl.File` doesn't set `mime` by default. `filetype.guess()` correctly identifies `.pdf` files (setting `application/pdf`), but returns `None` for `.md` files (plain text). The Chainlit frontend does `element.mime.startsWith(...)` without a null guard — when `mime` is `None`, it crashes.
**Fix:** Added `mime="text/markdown"` to the `cl.File` call for assessment export. The PDF export at `app.py:226` already worked because `filetype` identifies `.pdf` natively.
**Commit:** `455b406`

---

### 18. MCQ with empty options renders blank buttons

**File:** `app.py:356-393` — `_show_question()` MCQ branch
**Symptom:** An MCQ question with `options=[]` or a single option shows a blank "Choose your answer:" prompt with no clickable choices — the user is stuck.
**Root cause:** The MCQ branch iterated `q.options` unconditionally to build action buttons. With fewer than 2 options, no buttons were rendered and the `AskActionMessage` had no way to proceed.
**Fix:** Added a guard: if `len(q.options) < 2`, log a warning and fall through to the open-ended handler (AskUserMessage with text input). This is safe because the LLM-generated fallback path won't deadlock the user.
**Commit:** `89dc215`
