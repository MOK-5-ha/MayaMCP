# UI, Suggestion Chips & Voice Rules

This document outlines frontend architecture, Cartesia voice streaming, Phaser 4 gaming assets, and contextual suggestion chip guidelines for MayaMCP.

---

## 1. Contextual Suggestion Chips Architecture

- **Parallel Chip Generation**: Suggestion chips are generated in parallel with Maya's response using a background `ThreadPoolExecutor` (max 10 workers, 3-second timeout). Chip generation MUST NEVER block the response stream. All failures return empty chip sets with logging, never user-visible errors.
- **Structured Output Validation**: LLM structured outputs (e.g., suggestion chips) use Pydantic v2 schemas with field validators. Invalid outputs must log validation errors and return graceful fallback values (empty chip sets, generic greeting chips).
- **Chip State Management**: Session state includes `chip_state` dictionary with `current_chips` (SuggestionChipSet), `last_generation_time`, `generation_count`, `failure_count`, and `pending_task` (Future). Thread-safe access via session RLock. Rate limiting: max 1 generation per 2 seconds per session. Concurrency: max 10 parallel generations across all sessions.
- **Claim Invalidates Stale Chips**: `claim_chip_generation_seq()` must set `chip_state["current_chips"] = None` under the session lock when claiming a new sequence. Stored chips always belong to the latest claimed generation — without this, pollers accept the previous turn's set while the new one is still in flight and stop polling early.
- **Chip Generation Context Window**: `ChipGenerator` extracts last 4 conversation turns, current conversation phase (greeting, ordering, describing, payment, complete), payment status, and recent user messages (last 2) for deduplication and context-aware generation.
- **Post-Stream Chip Delivery via REST Polling**: Suggestion chips are delivered exclusively via `GET /api/v1/chips` polling after the SSE `complete` event. Never extend the SSE stream with chip payloads and never wait on `pending_task` futures — they are in-process only and invalid across multi-container Modal deployments. The SPA polls on a bounded window (500ms interval, max 8 polls) starting at stream completion; empty responses mean generation is still in flight, and the chip bar hides silently when the window expires. Polling loops must carry a run token plus `AbortController` and re-check both after every `await`, so a completed, destroyed, or relaunched poll run can never render into a stale chip bar.
- **Cooldown Persistence Across Failed Attempts**: Rate limiting cooldowns for background generation (such as suggestion chips) must persist across failed, timed-out, or invalid generation attempts. When a background generation task fails or times out (and is not superseded by a newer sequence), record `last_generation_time = time.time()` to enforce the cooldown period and prevent rapid retry loops during outages.
- **State Dictionary Default Normalization**: When retrieving numerical timestamps, sequence IDs, or counters from session or state dictionaries where defaults initialize keys to `None` (e.g., `DEFAULT_CHIP_STATE = {"last_generation_time": None}`), never rely solely on `dict.get(key, default)`. Because the key exists with value `None`, `dict.get` returns `None` and ignores the fallback default. Always normalize using `dict.get(key) or default` or explicit `if value is not None` checks before performing arithmetic or comparisons.

---

## 2. Intent Routing & Interaction Safety

- **Intent Routing Safety**: When implementing deterministic intent routing (e.g., bypassing the LLM for hardcoded commands like tips or payments), never use simple substring checks (like `'tip' in text`) as it is prone to false positives. Always use regex word boundaries (e.g., `re.search(r'\btips?\b', text, re.IGNORECASE)`) to guarantee precise matching.

---

## 3. Cartesia 4.x Voice Synthesis & Audio Streaming

- **Cartesia 4.x Generation API**: Use `cartesia_client.tts.generate` (returning `BinaryAPIResponse`) rather than deprecated `.bytes()`, reading binary content via `.read()` or streaming via `.iter_bytes()`. Pass voice parameters as `{"id": voice_id}` or raw voice ID string.
- **Lazy Streaming Pipelining**: Never materialize generators eagerly (such as `list(generator)`) when pipelining stream inputs (e.g. streaming LLM outputs to TTS). Consume them lazily (using queue-based iterators if passing items between threads) to preserve low latency.
- **Heartbeat Safety**: When reading streaming iterators that yield heartbeat/keep-alive events, ensure you yield the heartbeats immediately but continue draining the iterator in a loop until the matching content chunk is acquired, preventing payload misalignment.

---

## 4. Phaser 4 Game Canvas & Component Lifecycle

- **Phaser 4 Secondary Loader Pass**: When queuing assets dynamically from a loaded JSON manifest in `create()`, Phaser's loader queue does not automatically start unless `this.load.start()` is explicitly invoked, accompanied by a `this.load.once('complete', ...)` listener before starting downstream scenes (`BarScene`).
- **Phaser 4 Audio Cache Verification**: In Phaser 4 audio management, `this.scene.sound.get(key)` only queries already-instantiated sound objects. To verify whether an audio asset was preloaded into cache before calling `sound.add(key)`, check `this.scene.cache.audio.exists(key) || this.scene.sound.get(key) !== null`.
- **Phaser Component & Timer Teardown Safety**: Composite GameObjects (such as `MayaCharacter`) that create internal looping scene timers (e.g. `MouthFlapController`'s viseme flap timer) must implement a `destroy()` method that explicitly cancels active timers and destroys child graphics objects upon container/scene teardown.
- **Phaser DOM Controls & Container Placement**: Use `dom.createContainer: true` with Phaser DOM elements for native forms and buttons that need keyboard, mobile-input, or assistive-technology support. Keep `#game-container` block/relative and force Phaser's generated DOM container to `top: 0; left: 0`; flex centering can preserve a static-position offset that conflicts with ScaleManager canvas margins and push scaled DOM overlays outside the viewport. Verify DOM and canvas rects at native and scaled viewports.
- **Phaser DOM Size Caching**: Phaser caches a DOM element's measured size at creation time, so origin-based anchoring (e.g. `setOrigin(0, 1)` bottom anchors) drifts as content renders and changes the element's height. Anchor variable-content overlays with fixed-height wrappers (e.g. a 120px flex column with `justify-content: flex-end`) instead of origins, and assert overlay geometry in smoke tests only after content has rendered.
- **Credential Start Gate UX**: Use a native `<form>` with explicit labels, required/password semantics, visible focus indicators, 44×44 logical-pixel targets, and `role="alert"` errors. Never persist credentials or project IDs in browser storage; only persist the session ID, clear sensitive inputs on success, and abort in-flight requests on scene shutdown.
- **Manifest-Driven Soundtrack Lifecycle**: Audio manifest entries should declare `title` and a boolean `placeholder`. Preload skips placeholders, and `SoundManager` must recheck `cache.audio` before playback. Start music is scene-owned, fixed, and looping; stop it before bar playlist playback. `NEXT` and natural track completion search forward while `PREV` searches backward across unavailable entries, with wrapping. Pause/resume must preserve the same sound instance, and speech audio must remain independent of soundtrack state.

---

## 5. Accessibility Standards (WCAG 2.1 AA)

- **WCAG 2.1 AA Color Contrast Across Gradient Endpoints**: Any CSS gradient used behind standard-sized text (<18pt regular / <14pt bold) must ensure that *all* gradient color stops independently achieve at least a 4.5:1 contrast ratio against the foreground text color to satisfy WCAG 2.1 AA compliance (e.g. using dark indigo `#4338ca`/`#312e81` or deep wine `#be185d`/`#881337` behind white `#ffffff`).
- **Touch Targets & ARIA Labels**: Each interactive element (e.g. suggestion chip) must have a minimum 44x44px touch target, support keyboard activation (Enter/Space), and maintain ARIA live region announcements for screen reader users.
