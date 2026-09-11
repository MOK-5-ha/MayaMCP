# Architecture & Security Rules

This document specifies the backend architectural patterns, concurrency invariants, security scanning standards, and session/payment workflows for MayaMCP.

---

## 1. GCP Vertex AI Platform & Model Governance

- **100% GCP Vertex AI Mode Vendor Lock-in**: The application operates exclusively in GCP Vertex AI Mode using GCP billing credits (`GCP_PROJECT`, `GCP_LOCATION`, `GEMINI_TIER=paid`). Google AI Studio API Key Mode and free-tier throttles are permanently removed.
- **Deprecated Environment Variable Literal Prohibition**: The exact literal string identifiers for legacy AI Studio API keys (such as `GEMINI` + `_API_KEY`, `LLM` + `_API_KEY`, and `BACKUP_LLM` + `_API_KEY`) are strictly prohibited repository-wide in all files (including documentation, YAML configs, docstrings, and comments). Use generalized descriptions in text (e.g., "legacy AI Studio API keys") and dynamic string concatenation (e.g., `"GEMINI" + "_API_KEY"`) in purge functions or test assertions.
- **Google GenAI Enterprise Mode Flag**: In 100% GCP Vertex AI mode, always set both `GOOGLE_GENAI_USE_VERTEXAI="true"` and `GOOGLE_GENAI_USE_ENTERPRISE="true"` to ensure compatibility with Google ADK runtime and avoid deprecation warnings.
- **Unified LLM Client**: All GenAI calls go through `src/llm/client.py`. Never call the Google SDK directly elsewhere (including evaluation scripts and test helpers). Always use `get_genai_client()` instead of instantiating `genai.Client` directly.
- **Centralized Routing with Injected LLM Clients**: When supporting dependency-injected `genai.Client` instances (e.g. for testing or isolated session clients), never invoke `client.models.generate_content` directly outside `src/llm/client.py`. Always pass the injected client through `call_gemini_api(..., client=injected_client)` to ensure centralized configuration building (`response_schema`, `response_mime_type`), tracing, and retry resilience are consistently applied.
- **Vertex AI Mode Sessions**: Per-session LLM clients are lazily created via `src/llm/session_registry.py` utilizing Application Default Credentials (ADC).
- **Dynamic Model Verification**: Diagnostic scripts (`verify_environment.py`) must import and inspect `get_model_config()["model_version"]` to guarantee exact parity with runtime LLM configuration.
- **UI Contract Synchronization**: When modifying backend configuration semantics (such as shifting from API keys to Vertex AI ADC), all UI form labels, placeholders, Pydantic schemas, and modal instruction markdown must be updated in lockstep.

---

## 2. Concurrency, Locking & Session Management

- **Lock Ordering & Deadlock Prevention**: Never hold `_session_locks_mutex` while acquiring a per-session `RLock`. Background cleanup routines must snapshot expired session IDs under mutex lock, release `_session_locks_mutex`, acquire `session_lock`, and re-check `_session_last_access` under `_session_locks_mutex` before evicting session resources.
- **FastAPI Distributed Session Store**: In FastAPI routers, always use `get_session_store(request)` to read `request.app.state.session_store` dynamically (falling back to local `_SESSION_STORE`), ensuring session and payment state are shared across multi-container Modal deployments (`max_containers > 1`).
- **Batch State Defensive Merging**: When flushing request-scoped caches (`BatchStateCache.flush()`), never blindly overwrite persistent storage. Always check if out-of-band background workers (e.g. background suggestion chip generation, async payment settlements) updated state directly in the store, and defensively merge fresher records (using `generation_seq` or non-null checks) before writing back.
- **Batch Cache Invalidation on Session Reset**: In `reset_session_state()`, `clear_batch_cache_for_session(session_id)` MUST be invoked at the very beginning of the session lock acquisition *before* `initialize_state(session_id, store)` or reading sequence counters. This guarantees `_get_session_data()` reads clean store defaults and any pending `flush()` from an overlapping in-flight request becomes an immediate no-op, preventing pre-reset conversation, order, or payment state from being restored.
- **Multi-Tenant Concurrent Batch Cache Tracking**: Cross-thread batch cache registries (`_active_session_caches`) MUST track a collection (`list[BatchStateCache]`) per session rather than a single instance. When concurrent requests for the same session overlap, each registers its cache instance. `clear_batch_cache_for_session()` must atomically pop and call `.invalidate()` on ALL active caches for that session.
- **State Clearing Task & Cache Invalidation**: Any state-clearing helper (such as `clear_chip_state`) must mirror the full invalidation lifecycle of `reset_session_state`: (1) cancel active futures and background tasks, (2) invalidate active batch state caches via `clear_batch_cache_for_session(session_id)`, and (3) advance the monotonic sequence counter (`_session_chip_seq[session_id] += 1`) so late-arriving results from in-flight workers are cleanly discarded.
- **ContextVars and Thread Boundaries**: When using `ThreadPoolExecutor` or spawning new threads within ADK workflows, thread-local `ContextVar` states (like `session_id`) are not automatically propagated. You must explicitly initialize the context inside the thread worker closure (e.g., `set_current_session(session_id)`) before invoking ADK tools or database helpers.

---

## 3. Asynchronous Execution & Streaming Protocols

- **Async Background Task Dispatch**: When dispatching background tasks from synchronous tool functions, attempt `asyncio.get_running_loop().create_task()` first. If no event loop is active, spawn a daemon thread (`threading.Thread(daemon=True)`) running `asyncio.run()`.
- **Async Event Loop Unblocking for SSE**: In `async def` SSE streaming endpoints, never iterate synchronous blocking generators directly with a `for` loop. Offload iteration using `await asyncio.to_thread(_fetch_next_stream_event, stream)` to prevent blocking FastAPI's asyncio event loop thread.
- **EventSource Session Resolution**: Browser `EventSource` APIs cannot set custom request headers or inspect response headers. SSE streaming endpoints MUST support `session_id` via URL query parameters (`session_id=...`) and yield an initial `{"type": "session", "session_id": "..."}` SSE event upon connection.
- **Nested Event Loop Avoidance**: When executing synchronous entrypoint wraps of async ADK code (such as ADK `Runner` routines using `asyncio.run()`), always verify if an event loop is already running in the current thread. If a loop is active, execute the coroutine in a separate thread/executor to avoid event loop collision errors (`RuntimeError: asyncio.run() cannot be called from a running event loop`).
- **ADK Streaming Payload Gathering**: When accumulating chunks from ADK's `Runner.run_async` SSE events, do not restrict data collection exclusively to `event.partial == True`. Final text chunks may arrive without the partial flag, leading to dropped content. Process any `text_chunk` that contains valid string data.
- **Streaming Generator Exit Protocol**: When breaking out of a streaming generator queue loop (e.g., due to timeouts or errors), use early `return` instead of `break` if the generator has a fall-through logic block that yields a `'complete'` event. This prevents the consumer from receiving conflicting duplicate terminal events (both `'error'` and `'complete'`).
- **Server Dependencies**: The application uses a FastAPI-based server on Modal relying on `google-adk` and `a2a-sdk`. The `JSONRPCApplication` within the `a2a` server specifically requires `sse-starlette` to function. If test collection errors occur related to ADK routing (e.g. `ModuleNotFoundError: No module named 'sse-starlette'`), ensure `sse-starlette` is included in dependencies.

---

## 4. Payment Workflows & State Integrity

- **Payment State Thread-Safety**: Thread-safe per-session locking with atomic updates and version checks. Always acquire the session lock before modifying payment state. See `src/utils/state_manager.py`.
- **Optimistic Payment Status Transitions**: In zero-latency optimistic payment flows, `completed → failed` transitions MUST be allowed in `VALID_STATUS_TRANSITIONS` so async background processing tasks can record failures without raising validation exceptions.
- **Deterministic Payment Failure Testing**: Order amounts of `$99.99` trigger simulated background transaction failures in `CryptoPaymentClient._simulate_payment_lifecycle` for testing "register malfunction" apology flows in BDD and Vertex AI evaluations.

---

## 5. Security Scanning & Token Hygiene

- **Security Scanning**: Inputs are checked for prompt injection and toxicity before processing; outputs are checked before returning to the user. See `src/security/`.
- **Token Budget Dynamic Field Partitioning**: When constructing prompts with strict token ceilings (e.g. 512 tokens for suggestion chips), never right-truncate the assembled prompt string (`prompt[:budget*4]`), as this drops critical suffix directives (phase constraints, payment indicators, schema formatting rules). Instead, allocate proportional token budgets to dynamic fields (e.g., 75% conversation turns, 25% recent user messages) and truncate dynamic sections *before* appending invariant static prompt templates. Any remaining token trim must strictly reduce dynamic history while preserving the complete static suffix.

---

## 6. Developer Tooling Governance: MCP Scope & CLI-First Workflow

- **Scope Clarification (Developer Tooling vs. Application Architecture)**: This section governs the *development environment and AI coding assistant workflows* (how Antigravity, subagents, and review bots operate on this codebase). It does **NOT** dictate the runtime architecture of Maya herself (an asynchronous bartending service running on FastAPI, Modal serverless containers, Google ADK 2.0, Cartesia TTS, and Coinbase CDP).
- **MCP Scope & Stateful Boundaries**: Coding agents operate on a **CLI-first, stateful-MCP-sparing architecture**:
  - **MCP Reserved Tier (Stateful & Daemon Integrations Only)**:
    - AST Knowledge Graph: `codebase-memory-mcp` maintains the persistent SQLite Abstract Syntax Tree graph for codebase navigation and call-graph tracing.
    - External Library Documentation: `context7` resolves third-party package syntax and API definitions.
    - Live Browser Sessions: `chrome-devtools` and `axe-core` manage interactive Chrome DevTools Protocol (CDP) sessions and accessibility validation.
    - Automated Review Agent Gateways: `greptile` triggers and manages PR code reviews.
  - **CLI Tier (Stateless Operations)**:
    - All version control, pull requests, issues, cloud infrastructure, container management, and build tasks MUST execute through native CLI tools (`gh`, `git`, `gcloud`, `modal`, `docker`, `cargo`, `npm`, etc.) paired with lightweight companion skills.
- **Architectural Perpetuation & Downstream Agent Invariant**: This CLI-first, MCP-sparing doctrine is a permanent, indefinite architectural standard for coding agents. All future agents, subagents, and automated workflows governed by this constitution must:
  1. **Perpetuate the Pattern**: When recommending, designing, or scaffolding new tools, integrations, or workflows, agents must prioritize CLI binaries paired with lightweight skills rather than introducing new MCP servers.
  2. **Defend the Boundaries**: Strictly reject the addition of stateless MCP servers (e.g. for Jira, Slack, Linear, Stripe, GitHub, or Git) whenever a mature CLI tool or scriptable API exists. Reserve MCP exclusively for persistent stateful daemons, database connections, and AST memory graphs.
  3. **Propagate to Project Invariants**: When authoring repository-level `AGENTS.md`, `.cursor/rules/`, or subagent system prompts, agents must explicitly codify this CLI-first discipline to ensure child agents and subagents inherit identical token hygiene.
