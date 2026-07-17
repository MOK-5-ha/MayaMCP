## Project Overview
MayaMCP is an AI bartending agent (v2.0.0) with conversational drink ordering, voice synthesis, and simulated payments. It uses Google Gemini (via `google-generativeai` and `langchain-google-genai`) for LLM, Cartesia for TTS, FAISS/Memvid for RAG, and Stripe MCP for payments. The UI is built with Gradio, and API resilience is handled by `tenacity`.

## Repository Layout
```
src/
├── config/          # API keys, logging, model settings
├── conversation/    # Phase management, message processing
├── llm/             # Gemini client, prompts, function tools, session registry
├── memvid/          # Memvid RAG implementation
├── payments/        # Stripe MCP client and payment logic
├── prompt_engineering/  # Prompt templates
├── rag/             # RAG pipeline (embeddings, retrieval, vector store)
├── security/        # Input/output scanning, encryption, scan config
├── ui/              # Gradio components, handlers, tab overlay, BYOK modal
├── utils/           # Errors, helpers, state management
├── voice/           # Cartesia TTS integration
├── handlers/        # Request handlers
└── media/           # Media utilities
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
- Always mock external APIs (Google, Cartesia, Stripe) — never make real calls in tests.
- **Native SDK Mocking**: When testing Gemini functionality, mock the native `google.genai.Client` and stub its `models.generate_content` / `models.generate_content_stream` returns using standard native formats instead of obsolete LangChain structures.
- **Rate Limit Testing**: Never allow global app rate limits to restrict the standard test suite, as it causes false-negative token exhaustion errors. Set rate limit environment variables to high values (e.g., `9999`) in `tests/conftest.py`. When testing the rate limiter itself, use context-manager overrides to temporarily enforce limits strictly within those specific tests.
- **Stateful Singletons (Rate Limits)**: The application uses a global singleton for rate limiting (`RateLimiter`). When writing tests, ensure `check_rate_limits` is mocked in fixtures (e.g., returning `(True, "")`) to prevent sequential test execution from accumulating state and failing due to burst limits.
- **Refactoring & Mocks**: When extracting logic into helper functions, do not move the calls to state managers or mocked dependencies into the helper if it bypasses existing `@patch` targets in the test suite. Instead, fetch the data in the original module and pass the data structures into the helper.

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
- `STRIPE_SECRET_KEY` — Stripe test mode key (`sk_test_*` only)

## Key Architecture Rules
- **Unified LLM client**: All GenAI calls go through `src/llm/client.py`. Never call the Google SDK directly elsewhere. Always use `get_genai_client(api_key=...)` instead of instantiating `genai.Client` directly (this applies to sessions, registration modules, and integration tests to ensure proper caching).
- **Graceful fallbacks**: Memvid → FAISS → no-RAG; Cartesia → text-only; Stripe MCP → mock payment links.
- **Security scanning**: Inputs are checked for prompt injection/toxicity before processing; outputs are checked before returning to user. See `src/security/`.
- **Payment state**: Thread-safe per-session locking with atomic updates and version checks. Always acquire the session lock before modifying payment state. See `src/utils/state_manager.py`.
- **BYOK mode**: Per-session LLM/TTS clients are lazily created via `src/llm/session_registry.py`.
- **Lazy Streaming Pipelining**: Never materialize generators eagerly (such as `list(generator)`) when pipelining stream inputs (e.g. streaming LLM outputs to TTS). Consume them lazily (using queue-based iterators if passing items between threads) to preserve low latency.
- **Heartbeat Safety**: When reading streaming iterators that yield heartbeat/keep-alive events, ensure you yield the heartbeats immediately but continue draining the iterator in a loop until the matching content chunk is acquired, preventing payload misalignment.
- **Intent Routing Safety**: When implementing deterministic intent routing (e.g., bypassing the LLM for hardcoded commands like tips or payments), never use simple substring checks (like `'tip' in text`) as it is prone to false positives. Always use regex word boundaries (e.g., `re.search(r'\btips?\b', text, re.IGNORECASE)`) to guarantee precise matching.

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
- Use Stripe live mode keys (test mode only: `sk_test_*`)
- Modify payment state without acquiring the session lock
- Commit changes — only stage them for owner review
- Eagerly materialize streaming generators using `list()` or list comprehensions.
