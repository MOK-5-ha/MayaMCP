## Project Overview
MayaMCP is an AI bartending agent (v2.0.0) with conversational drink ordering, voice synthesis, and simulated payments. It uses Google Gemini (via `google-generativeai` and `langchain-google-genai`) for LLM, Cartesia for TTS, FAISS/Memvid for RAG, and Coinbase CDP AgentKit for crypto payments. The UI is built with Gradio, and API resilience is handled by `tenacity`.

## Repository Layout
```
src/
├── config/          # API keys, logging, model settings
├── conversation/    # Phase management, message processing
├── llm/             # Gemini client, prompts, function tools, session registry
├── memvid/          # Memvid RAG implementation
├── payments/        # Coinbase CDP crypto payment client and logic
├── rag/             # RAG pipeline (embeddings, retrieval, vector store)
├── routers/         # FastAPI REST & SSE v1 API routers (chat, payments, session)
├── schemas/         # Pydantic v2 data transfer schemas
├── security/        # Input/output scanning, encryption, scan config
├── ui/              # Gradio components, handlers, tab overlay, BYOK modal
├── utils/           # Errors, helpers, state management
└── voice/           # Cartesia TTS integration
tests/               # pytest suite (unit, integration, property-based, API)
assets/              # Static files (avatar, media)
deploy.py            # Modal Labs deployment
run_maya.sh          # Dev runner script
```

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```
Always activate the `.venv` before running any command.

## Running
```bash
# Via console script
mayamcp

# Via runner script
./run_maya.sh

# Deployment (Modal Labs)
modal serve deploy.py   # Dev
modal deploy deploy.py  # Prod
```

## Testing
```bash
pytest                    # All tests
pytest --cov              # With coverage
pytest -m "not slow"      # Skip slow tests
pytest -m unit            # Unit tests only
pytest -m integration     # Integration tests only

# Vertex AI Gen AI Evaluation Service & Cloud Trace
python scripts/run_evals.py
python tests/eval/eval_crypto_payment.py
```
- Tests live in `tests/` with `test_*.py` naming.
- `tests/conftest.py` provides fixtures and SDK stubs for offline testing.
- Markers: `slow`, `integration`, `unit`, `memvid`, `rag`, `llm`, `ui`.
- Property-based tests use Hypothesis.
- Always mock external APIs (Google, Cartesia, Coinbase CDP) — never make real calls in tests.
- **Native SDK Mocking**: When testing Gemini functionality, mock the native `google.genai.Client` and stub its `models.generate_content` / `models.generate_content_stream` returns using standard native formats instead of obsolete LangChain structures.
- **Rate Limit Testing**: Never allow global app rate limits to restrict the standard test suite, as it causes false-negative token exhaustion errors. Set rate limit environment variables to high values (e.g., `9999`) in `tests/conftest.py`. When testing the rate limiter itself, use context-manager overrides to temporarily enforce limits strictly within those specific tests.
- **Stateful Singletons (Rate Limits)**: The application uses a global singleton for rate limiting (`RateLimiter`). When writing tests, ensure `check_rate_limits` is mocked in fixtures (e.g., returning `(True, "")`) to prevent sequential test execution from accumulating state and failing due to burst limits.
- **Refactoring & Mocks**: When extracting logic into helper functions, do not move the calls to state managers or mocked dependencies into the helper if it bypasses existing `@patch` targets in the test suite. Instead, fetch the data in the original module and pass the data structures into the helper.
- **Mocking Tools**: Never use "mock-sniffing" wrappers in production code to detect `unittest.mock` objects. Instead, fix the test doubles. When patching tools that used to be invoked via LangChain's `.invoke()`, set both `mock.return_value` and `mock.invoke.return_value` to the expected string to ensure compatibility with both direct calls and legacy test harnesses.
- **Rate Limiter Initialization timing**: If overriding rate limit constraints via environment variables (e.g. setting `MAYA_SESSION_RATE_LIMIT` to `9999` for tests or evaluations), ensure those environment variables are set *before* importing any package from the application to prevent the `RateLimiter` singleton from initializing with default values.
- **Offline Evaluations & Telemetry**: Headless evaluation suites and OpenTelemetry exporters must support running completely offline without demanding remote authentication if GCP Application Default Credentials (ADC) are absent. Provide local test doubles and fallback to standard Python logging to execute evaluations locally.

## Linting & Type Checking
```bash
ruff check src/ tests/    # Lint (line-length: 88, target: py38)
mypy src/                 # Type checking
```
Ruff config is in `pyproject.toml`. Rules: E, W, F, I, B, C4, UP.

## Environment Variables
Copy `.env.example` to `.env`. Maya operates in 100% GCP Vertex AI Mode using Application Default Credentials (ADC) and GCP billing credits. Optional session overrides can be provided via the UI.

Required:
- `GCP_PROJECT` — Google Cloud Platform Project ID (for Vertex AI mode ADC authentication)
- `GCP_LOCATION` — GCP Location (defaults to `global`)
- `GEMINI_TIER` — Locked to `paid` (high-throughput concurrency quota)
- `CARTESIA_API_KEY` — Cartesia TTS API key

Optional:
- `GEMINI_MODEL_VERSION` — defaults to `gemini-3.5-flash-lite`
- `TEMPERATURE` — defaults to `1.0`
- `MAX_OUTPUT_TOKENS` — defaults to `8192`
- `MAYA_MASTER_KEY` — Fernet key for encrypting session data (ephemeral if unset)
- `CDP_API_KEY_ID` — Coinbase CDP API key ID
- `CDP_API_KEY_SECRET` — Coinbase CDP API key secret
- `CDP_MERCHANT_PRIVATE_KEY` — Wallet private key for Base Sepolia (optional)
- `CDP_RECEIVER_ADDRESS` — Merchant wallet address (optional, has default)

## Key Architecture Rules
- **100% GCP Vertex AI Mode Vendor Lock-in**: The application operates exclusively in GCP Vertex AI Mode using GCP billing credits (`GCP_PROJECT`, `GCP_LOCATION`, `GEMINI_TIER=paid`). Google AI Studio API Key Mode and free-tier throttles are permanently removed.
- **Deprecated Environment Variable Literal Prohibition**: The exact literal string identifiers for legacy AI Studio API keys (such as `GEMINI` + `_API_KEY`, `LLM` + `_API_KEY`, and `BACKUP_LLM` + `_API_KEY`) are strictly prohibited repository-wide in all files (including documentation, YAML configs, docstrings, and comments). Use generalized descriptions in text (e.g., "legacy AI Studio API keys") and dynamic string concatenation (e.g., `"GEMINI" + "_API_KEY"`) in purge functions or test assertions.
- **Unified LLM client**: All GenAI calls go through `src/llm/client.py`. Never call the Google SDK directly elsewhere (including evaluation scripts and test helpers). Always use `get_genai_client()` instead of instantiating `genai.Client` directly.
- **UI Contract Synchronization**: When modifying backend configuration semantics (such as shifting from API keys to Vertex AI ADC), all UI form labels, placeholders, Pydantic schemas, and modal instruction markdown must be updated in lockstep.
- **Dynamic Model Verification**: Diagnostic scripts (`verify_environment.py`) must import and inspect `get_model_config()["model_version"]` to guarantee exact parity with runtime LLM configuration.
- **Graceful fallbacks**: Memvid → FAISS → no-RAG; Cartesia → text-only; Coinbase CDP → mock crypto payments.
- **Security scanning**: Inputs are checked for prompt injection/toxicity before processing; outputs are checked before returning to user. See `src/security/`.
- **Payment state**: Thread-safe per-session locking with atomic updates and version checks. Always acquire the session lock before modifying payment state. See `src/utils/state_manager.py`.
- **Vertex AI Mode Sessions**: Per-session LLM clients are lazily created via `src/llm/session_registry.py` utilizing Application Default Credentials (ADC).
- **Lazy Streaming Pipelining**: Never materialize generators eagerly (such as `list(generator)`) when pipelining stream inputs (e.g. streaming LLM outputs to TTS). Consume them lazily (using queue-based iterators if passing items between threads) to preserve low latency.
- **Heartbeat Safety**: When reading streaming iterators that yield heartbeat/keep-alive events, ensure you yield the heartbeats immediately but continue draining the iterator in a loop until the matching content chunk is acquired, preventing payload misalignment.
- **Intent Routing Safety**: When implementing deterministic intent routing (e.g., bypassing the LLM for hardcoded commands like tips or payments), never use simple substring checks (like `'tip' in text`) as it is prone to false positives. Always use regex word boundaries (e.g., `re.search(r'\btips?\b', text, re.IGNORECASE)`) to guarantee precise matching.
- **Nested Event Loop Avoidance**: When executing synchronous entrypoint wraps of async ADK code (such as ADK `Runner` routines using `asyncio.run()`), always verify if an event loop is already running in the current thread. If a loop is active, execute the coroutine in a separate thread/executor to avoid event loop collision errors (`RuntimeError: asyncio.run() cannot be called from a running event loop`).
- **ContextVars and Thread Boundaries**: When using `ThreadPoolExecutor` or spawning new threads within ADK workflows, thread-local `ContextVar` states (like `session_id`) are not automatically propagated. You must explicitly initialize the context inside the thread worker closure (e.g., `set_current_session(session_id)`) before invoking ADK tools or database helpers.
- **ADK Streaming Payload Gathering**: When accumulating chunks from ADK's `Runner.run_async` SSE events, do not restrict data collection exclusively to `event.partial == True`. Final text chunks may arrive without the partial flag, leading to dropped content. Process any `text_chunk` that contains valid string data.
- **Streaming Generator Exit Protocol**: When breaking out of a streaming generator queue loop (e.g., due to timeouts or errors), use early `return` instead of `break` if the generator has a fall-through logic block that yields a `'complete'` event. This prevents the consumer from receiving conflicting duplicate terminal events (both `'error'` and `'complete'`).
- **Server Dependencies**: The application uses a FastAPI-based server on Modal relying on `google-adk` and `a2a-sdk`. The `JSONRPCApplication` within the `a2a` server specifically requires `sse-starlette` to function. If test collection errors occur related to ADK routing (e.g. `ModuleNotFoundError: No module named 'sse-starlette'`), ensure `sse-starlette` is included in dependencies.
- **Optimistic Payment Status Transitions**: In zero-latency optimistic payment flows, `completed → failed` transitions MUST be allowed in `VALID_STATUS_TRANSITIONS` so async background processing tasks can record failures without raising validation exceptions.
- **Deterministic Payment Failure Testing**: Order amounts of `$99.99` trigger simulated background transaction failures in `CryptoPaymentClient._simulate_payment_lifecycle` for testing "register malfunction" apology flows in BDD and Vertex AI evaluations.
- **Async Background Task Dispatch**: When dispatching background tasks from synchronous tool functions, attempt `asyncio.get_running_loop().create_task()` first. If no event loop is active, spawn a daemon thread (`threading.Thread(daemon=True)`) running `asyncio.run()`.
- **FastAPI Distributed Session Store**: In FastAPI routers, always use `get_session_store(request)` to read `request.app.state.session_store` dynamically (falling back to local `_SESSION_STORE`), ensuring session and payment state are shared across multi-container Modal deployments (`max_containers > 1`).
- **Async Event Loop Unblocking for SSE**: In `async def` SSE streaming endpoints, never iterate synchronous blocking generators directly with a `for` loop. Offload iteration using `await asyncio.to_thread(_fetch_next_stream_event, stream)` to prevent blocking FastAPI's asyncio event loop thread.
- **EventSource Session Resolution**: Browser `EventSource` APIs cannot set custom request headers or inspect response headers. SSE streaming endpoints MUST support `session_id` via URL query parameters (`session_id=...`) and yield an initial `{"type": "session", "session_id": "..."}` SSE event upon connection.
- **Lock Ordering & Deadlock Prevention**: Never hold `_session_locks_mutex` while acquiring a per-session `RLock`. Background cleanup routines must snapshot expired session IDs under mutex lock, release `_session_locks_mutex`, acquire `session_lock`, and re-check `_session_last_access` under `_session_locks_mutex` before evicting session resources.
- **Phaser 3 Secondary Loader Pass**: When queuing assets dynamically from a loaded JSON manifest in `create()`, Phaser's loader queue does not automatically start unless `this.load.start()` is explicitly invoked, accompanied by a `this.load.once('complete', ...)` listener before starting downstream scenes (`BarScene`).
- **Phaser 3 Audio Cache Verification**: In Phaser 3 audio management, `this.scene.sound.get(key)` only queries already-instantiated sound objects. To verify whether an audio asset was preloaded into cache before calling `sound.add(key)`, check `this.scene.cache.audio.exists(key) || this.scene.sound.get(key) !== null`.
- **Phaser Component & Timer Teardown Safety**: Composite GameObjects (such as `MayaCharacter`) that create internal looping scene timers (e.g. `MouthFlapController`'s viseme flap timer) must implement a `destroy()` method that explicitly cancels active timers and destroys child graphics objects upon container/scene teardown.
- **Evaluation Fallback Isolation**: When authoring Agent-as-a-Judge or EvalTask harnesses with local heuristic fallback paths (`is_fallback: bool = True`), evaluation runners and metric aggregators MUST explicitly isolate fallback verdicts from live passing percentages and average score calculations (`isolate_fallback_benchmark_aggregates`), reporting `fallback_count` and fallback scores in a separate section to avoid inflating live pass rates.
- **Asynchronous Lifecycle Evaluation Synchronization**: When evaluating multi-turn conversational agents with asynchronous/background operations (e.g. background blockchain transactions with simulated delays), evaluation benchmark runners must synchronize/poll for terminal state (e.g. `payment_status == 'failed'`) before executing subsequent query turns rather than immediately issuing follow-up turns across an unsettled race condition.
- **Zero-Trust Evaluation Context Delimitation & Sanitization**: Before passing user messages or agent responses to an LLM-as-a-judge, sanitize untrusted strings (`sanitize_eval_input`) to defuse control tokens (`[INST]`, `<<SYS>>`, `<|im_start|>`), instruction override patterns, and score manipulation directives, and wrap dynamic sections in structural XML tags (`<user_turns>`, `<maya_responses>`, `<agent_trajectory>`).
- **Prefix Invariant Caching**: To leverage GCP Context Caching in LLM judge routines, structure prompts with static evaluation rubrics and instructions at the prompt prefix (Invariant Prefix), placing dynamic test case inputs at the prompt tail.
- **Non-Prescriptive Prompt State vs Scripted Responses**: When exposing background failures (like register malfunctions) to conversational agents via system prompt context, provide only factual state indicators (e.g. `PAYMENT STATUS: Failed (register malfunction during settlement)`) rather than prescriptive behavioral instructions (e.g. "Apologize and offer retry"), ensuring evaluation benchmarks measure authentic agent behavior rather than scripted prompt directives.
- **Evaluation Scorer Guard Discipline**: In LLM evaluation scorers checking list outputs (like derived visemes), empty lists `[]` must NOT evaluate to `True` via fall-through guards like `... if visemes else True`. Scorers must strictly enforce non-empty lists (`bool(visemes) and len(visemes) == len(turns)`).
- **Google GenAI Enterprise Mode Flag**: In 100% GCP Vertex AI mode, always set both `GOOGLE_GENAI_USE_VERTEXAI="true"` and `GOOGLE_GENAI_USE_ENTERPRISE="true"` to ensure compatibility with Google ADK runtime and avoid `GOOGLE_GENAI_USE_VERTEXAI is deprecated` warnings.
- **Mocking Background Event Loop Dispatch**: When mocking `asyncio.get_running_loop().create_task` in unit tests, configure `mock_loop.create_task.side_effect = lambda coro: coro.close()` to cleanly terminate the coroutine and prevent unawaited coroutine `RuntimeWarning` exceptions during garbage collection.
- **ADK Model Double Generator Protocol**: Test doubles implementing `Gemini.generate_content_async` must be defined as async generators yielding `LlmResponse.create(...)` rather than coroutines returning responses, matching Google ADK's runner interface.

## Adding a New Tool
1. Define tool schema in `src/llm/tools.py`
2. Implement handler in `src/conversation/processor.py`
3. Add tests in `tests/`

## Don't
- Call Google SDK directly outside `src/llm/client.py` (use `get_genai_client` for all model interactions, including evals)
- Use Google AI Studio API key mode or free-tier rate limits
- Hardcode API keys or secrets
- Skip error handling for external API calls
- Break the graceful fallback chain
- Add tests that require real API calls without mocking
- Use Coinbase CDP mainnet keys in development (Base Sepolia testnet only)
- Modify payment state without acquiring the session lock
- Commit changes — only stage them for owner review
- Eagerly materialize streaming generators using `list()` or list comprehensions.
