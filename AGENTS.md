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
├── security/        # Input/output scanning, encryption, scan config
├── ui/              # Gradio components, handlers, tab overlay, BYOK modal
├── utils/           # Errors, helpers, state management
└── voice/           # Cartesia TTS integration
tests/               # pytest suite (unit, integration, property-based)
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

# Weave Evaluations (LLM-as-judge)
python scripts/run_weave_evals.py
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
- **Offline Evaluations**: Headless evaluation suites (such as Weights & Biases Weave integrations) must support running completely offline without demanding remote authentication if `WANDB_API_KEY` is missing. Create dummy mock fallbacks for classes like `weave.Model` and `weave.Evaluation` to execute evaluations locally.

## Linting & Type Checking
```bash
ruff check src/ tests/    # Lint (line-length: 88, target: py38)
mypy src/                 # Type checking
```
Ruff config is in `pyproject.toml`. Rules: E, W, F, I, B, C4, UP.

## Environment Variables
Copy `.env.example` to `.env`. Maya runs in BYOK (Bring Your Own Key) mode — users provide API keys via the UI.

Required (for server-side fallback):
- `GEMINI_API_KEY` — Google AI Studio API key
- `CARTESIA_API_KEY` — Cartesia TTS API key

Optional:
- `GEMINI_MODEL_VERSION` — defaults to `gemini-3-flash-preview`
- `TEMPERATURE` — defaults to `1.0`
- `MAX_OUTPUT_TOKENS` — defaults to `2048`
- `MAYA_MASTER_KEY` — Fernet key for encrypting session data (ephemeral if unset)
- `CDP_API_KEY_ID` — Coinbase CDP API key ID
- `CDP_API_KEY_SECRET` — Coinbase CDP API key secret
- `CDP_MERCHANT_PRIVATE_KEY` — Wallet private key for Base Sepolia (optional)
- `CDP_RECEIVER_ADDRESS` — Merchant wallet address (optional, has default)

## Key Architecture Rules
- **Unified LLM client**: All GenAI calls go through `src/llm/client.py`. Never call the Google SDK directly elsewhere. Always use `get_genai_client(api_key=...)` instead of instantiating `genai.Client` directly (this applies to sessions, registration modules, and integration tests to ensure proper caching).
- **Graceful fallbacks**: Memvid → FAISS → no-RAG; Cartesia → text-only; Coinbase CDP → mock crypto payments.
- **Security scanning**: Inputs are checked for prompt injection/toxicity before processing; outputs are checked before returning to user. See `src/security/`.
- **Payment state**: Thread-safe per-session locking with atomic updates and version checks. Always acquire the session lock before modifying payment state. See `src/utils/state_manager.py`.
- **BYOK mode**: Per-session LLM/TTS clients are lazily created via `src/llm/session_registry.py`.
- **Lazy Streaming Pipelining**: Never materialize generators eagerly (such as `list(generator)`) when pipelining stream inputs (e.g. streaming LLM outputs to TTS). Consume them lazily (using queue-based iterators if passing items between threads) to preserve low latency.
- **Heartbeat Safety**: When reading streaming iterators that yield heartbeat/keep-alive events, ensure you yield the heartbeats immediately but continue draining the iterator in a loop until the matching content chunk is acquired, preventing payload misalignment.
- **Intent Routing Safety**: When implementing deterministic intent routing (e.g., bypassing the LLM for hardcoded commands like tips or payments), never use simple substring checks (like `'tip' in text`) as it is prone to false positives. Always use regex word boundaries (e.g., `re.search(r'\btips?\b', text, re.IGNORECASE)`) to guarantee precise matching.
- **Nested Event Loop Avoidance**: When executing synchronous entrypoint wraps of async ADK code (such as ADK `Runner` routines using `asyncio.run()`), always verify if an event loop is already running in the current thread. If a loop is active, execute the coroutine in a separate thread/executor to avoid event loop collision errors (`RuntimeError: asyncio.run() cannot be called from a running event loop`).
- **ContextVars and Thread Boundaries**: When using `ThreadPoolExecutor` or spawning new threads within ADK workflows, thread-local `ContextVar` states (like `session_id`) are not automatically propagated. You must explicitly initialize the context inside the thread worker closure (e.g., `set_current_session(session_id)`) before invoking ADK tools or database helpers.
- **ADK Streaming Payload Gathering**: When accumulating chunks from ADK's `Runner.run_async` SSE events, do not restrict data collection exclusively to `event.partial == True`. Final text chunks may arrive without the partial flag, leading to dropped content. Process any `text_chunk` that contains valid string data.
- **Streaming Generator Exit Protocol**: When breaking out of a streaming generator queue loop (e.g., due to timeouts or errors), use early `return` instead of `break` if the generator has a fall-through logic block that yields a `'complete'` event. This prevents the consumer from receiving conflicting duplicate terminal events (both `'error'` and `'complete'`).
- **Server Dependencies**: The application uses a FastAPI-based server on Modal relying on `google-adk` and `a2a-sdk`. The `JSONRPCApplication` within the `a2a` server specifically requires `sse-starlette` to function. If test collection errors occur related to ADK routing (e.g. `ModuleNotFoundError: No module named 'sse-starlette'`), ensure `sse-starlette` is included in dependencies.

## Adding a New Tool
1. Define tool schema in `src/llm/tools.py`
2. Implement handler in `src/conversation/processor.py`
3. Add tests in `tests/`

## Don't
- Call Google SDK directly outside `src/llm/client.py` (use `get_genai_client`)
- Hardcode API keys or secrets
- Skip error handling for external API calls
- Break the graceful fallback chain
- Add tests that require real API calls without mocking
- Use Coinbase CDP mainnet keys in development (Base Sepolia testnet only)
- Modify payment state without acquiring the session lock
- Commit changes — only stage them for owner review
- Eagerly materialize streaming generators using `list()` or list comprehensions.
