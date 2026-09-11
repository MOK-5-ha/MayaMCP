# UI, Suggestion Chips & Voice Rules

This document outlines frontend architecture, Gradio components, Cartesia voice streaming, Phaser 3 gaming assets, and contextual suggestion chip guidelines for MayaMCP.

---

## 1. Contextual Suggestion Chips Architecture

- **Parallel Chip Generation**: Suggestion chips are generated in parallel with Maya's response using a background `ThreadPoolExecutor` (max 10 workers, 3-second timeout). Chip generation MUST NEVER block the response stream. All failures return empty chip sets with logging, never user-visible errors.
- **Structured Output Validation**: LLM structured outputs (e.g., suggestion chips) use Pydantic v2 schemas with field validators. Invalid outputs must log validation errors and return graceful fallback values (empty chip sets, generic greeting chips).
- **Chip State Management**: Session state includes `chip_state` dictionary with `current_chips` (SuggestionChipSet), `last_generation_time`, `generation_count`, `failure_count`, and `pending_task` (Future). Thread-safe access via session RLock. Rate limiting: max 1 generation per 2 seconds per session. Concurrency: max 10 parallel generations across all sessions.
- **Chip Generation Context Window**: `ChipGenerator` extracts last 4 conversation turns, current conversation phase (greeting, ordering, describing, payment, complete), payment status, and recent user messages (last 2) for deduplication and context-aware generation.
- **Downstream Background Task Synchronization in UI Callbacks**: When parallel background tasks (such as suggestion chip generation via `ThreadPoolExecutor`) execute concurrently with streaming responses, downstream UI follow-up callbacks (e.g. `.then(refresh_chips_after_response)`) must explicitly synchronize with in-flight background futures (`task.result(timeout=...)` with safety timeout fallbacks) before querying session state. Never assume background tasks complete before streaming response callbacks fire.
- **Cooldown Persistence Across Failed Attempts**: Rate limiting cooldowns for background generation (such as suggestion chips) must persist across failed, timed-out, or invalid generation attempts. When a background generation task fails or times out (and is not superseded by a newer sequence), record `last_generation_time = time.time()` to enforce the cooldown period and prevent rapid retry loops during outages.
- **State Dictionary Default Normalization**: When retrieving numerical timestamps, sequence IDs, or counters from session or state dictionaries where defaults initialize keys to `None` (e.g., `DEFAULT_CHIP_STATE = {"last_generation_time": None}`), never rely solely on `dict.get(key, default)`. Because the key exists with value `None`, `dict.get` returns `None` and ignores the fallback default. Always normalize using `dict.get(key) or default` or explicit `if value is not None` checks before performing arithmetic or comparisons.

---

## 2. Gradio Component State & Event Handlers

- **Gradio Event Chaining for Auto-Submissions (`.then()`)**: In Gradio UI components requiring automated submission (such as action chips or quick-actions), never use arbitrary timer delays (`setTimeout`) or uncoordinated DOM clicks in JavaScript. Timers race against input textbox state updates and submit stale or empty input. Always chain auto-submission strictly after the input population callback finishes using Gradio's native `.then()` event listener (`click_ev.then(fn=None, inputs=[submit_btn], js="...")`), ensuring the textbox state is guaranteed to be updated in the client before the submit button is clicked.
- **Gradio Store and Session State Propagation**: All Gradio event wrappers, component registration helpers, and UI refresh callbacks must explicitly accept and pass `app_state` (or the injected session store) down to `get_session_state()` and `update_*()` calls. Never rely on module-level fallback singletons in UI callbacks, as this causes session isolation failures across multi-container environments.
- **Gradio Component Input Argument Semantics**: In Gradio, passing a button component in `inputs=[btn]` passes only its displayed string `value` to callback handlers, never its HTML DOM attributes (such as `elem_id`). Action metadata, button indices, or entity IDs must be resolved via button position index closures or parsed from visible content prefixes (e.g. emoji prefixes from `ACTION_ICONS`), rather than expecting Gradio to provide DOM element attributes.
- **Intent Routing Safety**: When implementing deterministic intent routing (e.g., bypassing the LLM for hardcoded commands like tips or payments), never use simple substring checks (like `'tip' in text`) as it is prone to false positives. Always use regex word boundaries (e.g., `re.search(r'\btips?\b', text, re.IGNORECASE)`) to guarantee precise matching.

---

## 3. Cartesia Voice Synthesis & Audio Streaming

- **Lazy Streaming Pipelining**: Never materialize generators eagerly (such as `list(generator)`) when pipelining stream inputs (e.g. streaming LLM outputs to TTS). Consume them lazily (using queue-based iterators if passing items between threads) to preserve low latency.
- **Heartbeat Safety**: When reading streaming iterators that yield heartbeat/keep-alive events, ensure you yield the heartbeats immediately but continue draining the iterator in a loop until the matching content chunk is acquired, preventing payload misalignment.

---

## 4. Phaser 3 Game Canvas & Component Lifecycle

- **Phaser 3 Secondary Loader Pass**: When queuing assets dynamically from a loaded JSON manifest in `create()`, Phaser's loader queue does not automatically start unless `this.load.start()` is explicitly invoked, accompanied by a `this.load.once('complete', ...)` listener before starting downstream scenes (`BarScene`).
- **Phaser 3 Audio Cache Verification**: In Phaser 3 audio management, `this.scene.sound.get(key)` only queries already-instantiated sound objects. To verify whether an audio asset was preloaded into cache before calling `sound.add(key)`, check `this.scene.cache.audio.exists(key) || this.scene.sound.get(key) !== null`.
- **Phaser Component & Timer Teardown Safety**: Composite GameObjects (such as `MayaCharacter`) that create internal looping scene timers (e.g. `MouthFlapController`'s viseme flap timer) must implement a `destroy()` method that explicitly cancels active timers and destroys child graphics objects upon container/scene teardown.

---

## 5. Accessibility Standards (WCAG 2.1 AA)

- **WCAG 2.1 AA Color Contrast Across Gradient Endpoints**: Any CSS gradient used behind standard-sized text (<18pt regular / <14pt bold) must ensure that *all* gradient color stops independently achieve at least a 4.5:1 contrast ratio against the foreground text color to satisfy WCAG 2.1 AA compliance (e.g. using dark indigo `#4338ca`/`#312e81` or deep wine `#be185d`/`#881337` behind white `#ffffff`).
- **Touch Targets & ARIA Labels**: Each interactive element (e.g. suggestion chip) must have a minimum 44x44px touch target, support keyboard activation (Enter/Space), and maintain ARIA live region announcements for screen reader users.
