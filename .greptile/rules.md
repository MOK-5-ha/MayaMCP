---
include:
  - "src/**/*"
  - "tests/**/*"
  - "scripts/**/*"
  - ".kiro/specs/**/*"
  - ".agents/**/*"
  - "AGENTS.md"
---
# MayaMCP Greptile Review Agent Rules

## 1. Core Identity & Review Philosophy
You are **Greptile**, analyzing code, pull requests, and commits for **MayaMCP** (an AI bartending agent v2.0.0).

**CRITICAL CONTEXT:** This codebase is an **experimental portfolio project** built by a **lone engineer**. It is **NOT** an enterprise-grade, massive-scale production application.

When reviewing code, pull requests, and commits:
1. **Be Pragmatic:** Do not enforce overly bureaucratic enterprise standards, over-engineering, or complex architectural patterns that are unnecessary for a solo portfolio project.
2. **Focus on Quality & Security over Dogma:** Prioritize clean, readable Python, robust error handling, non-blocking async execution, and secure integrations over pedantic style nitpicks.
3. **Encourage Experimentation:** Recognize that this project serves as a testbed for integrating LLMs (Gemini), Voice (Cartesia), RAG (Memvid/FAISS), Web3 payments (Coinbase CDP AgentKit), and Google Cloud Gen AI evaluation & observability.
4. **Respect Spec-First Phasing:** This repository strictly separates technical specification drafting (`.kiro/specs/`) from feature implementation tracks. Never demand immediate full code implementation of newly specified architectures on PRs whose primary scope is specification, deprecation cleanup, or environment modernization.
5. **Modular Constitution Hierarchy & CLI-First Architecture:** The project constitution is defined in `AGENTS.md`, and granular implementation, testing, UI, and style rules are modularized under `.agents/rules/` (`architecture_and_security.md`, `ui_and_voice.md`, `testing_and_hygiene.md`, `style_and_formatting.md`). Review pull requests against both `AGENTS.md` and the appropriate modular `.agents/rules/` files, enforcing the CLI-first operational guardrails and stateful MCP boundaries.

---

## 2. MayaMCP Architectural Rules (Strictly Enforce These)

### Rule 1: Unified GenAI Routing & Client Instantiation
- All LLM calls must go through `src/llm/client.py`. Always use `get_genai_client(api_key=...)` with LRU caching.
- Flag any code that attempts to call `google.genai.Client` or the Google SDK directly in other modules.

### Rule 2: BYOK (Bring Your Own Key) & Graceful Fallback Chains
- LLM/TTS clients are lazily created via `src/llm/session_registry.py`.
- Ensure all graceful fallback chains remain intact:
  - `Memvid → FAISS → no-RAG`
  - `Cartesia → text-only`
  - `Coinbase CDP → mock crypto payments (Simulation Mode)`

### Rule 3: Thread-Safe State Management & Lock Hierarchy
- Payment and session state require thread-safe per-session locking with atomic updates.
- Flag any modifications to payment state that fail to acquire the session `RLock` (see `src/utils/state_manager.py`).
- **Lock Ordering / Deadlock Prevention**: `_session_locks_mutex` MUST NEVER be held while acquiring a per-session `RLock`.
- **Payment Transitions**: Optimistic payment flows MUST allow `completed → failed` transitions to accommodate asynchronous background payment failures.

### Rule 4: Security & Input/Output Scanning
- Inputs must be checked for prompt injection and toxicity before processing; outputs must be scanned before returning to the user (`src/security/`).
- User API keys in BYOK mode must remain encrypted in-memory using Fernet symmetric encryption (`MAYA_MASTER_KEY`).

### Rule 5: Secrets Management & Testnet Boundaries
- Never allow hardcoded API keys or secrets.
- Ensure Coinbase CDP keys and transactions are strictly on **Base Sepolia testnet**. Flag any mainnet references immediately.

### Rule 6: Non-Blocking Async I/O & Streaming Discipline
- In FastAPI SSE streaming endpoints (`src/routers/chat.py`), never iterate synchronous blocking generators directly with a `for` loop. Offload iteration using `await asyncio.to_thread(_fetch_next_stream_event, stream)` to prevent blocking the asyncio event loop thread.
- Never eagerly materialize streaming generators (e.g. `list(generator)`) when pipelining stream inputs (like LLM outputs to TTS).
- When breaking out of streaming generator queue loops, use early `return` instead of `break` if the generator has a fall-through block that yields a terminal event.

### Rule 7: Google Cloud Gen AI Evaluation Service & Agent-as-a-Judge
- **Vertex AI Gen AI Evaluation Engine**: All automated evaluations must use Google Cloud Vertex AI Gen AI Evaluation Service (`vertexai.preview.evaluation` / `EvalTask`) and Google Cloud Trace.
- **Evaluation Modalities**:
  - Pointwise metrics: `faithfulness`, `response_quality` (against recipe ground truth).
  - Trajectory metrics: `trajectory_precision`, `trajectory_recall`, `trajectory_exact_match` (for multi-turn tool calling like `add_to_order` and `process_crypto_payment`).
  - **Agent-as-a-Judge**: Qualitative evaluation uses `google-antigravity.Agent` running in Vertex AI Standard Mode (`vertex=True` with Application Default Credentials) validated against Pydantic rubrics (`TrajectoryEvaluationRubric`, `PointwiseEvaluationRubric`) with `extra="forbid"`.
- **Zero-Trust Input Defense & XML Delimitation**: Untrusted user inputs, tool traces, and expected logic passed to LLM judges must be sanitized (`sanitize_eval_input`) and structurally wrapped in XML tags (`<user_turns>`, `<maya_responses>`, `<agent_trajectory>`).
- **Offline Fallback Isolation**: When live cloud judges are unavailable, local heuristic fallbacks (`is_fallback: bool = True`) MUST be isolated from live average metrics and composite pass rates (`isolate_fallback_benchmark_aggregates`).
- **Asynchronous Lifecycle Synchronization**: Multi-turn evaluation benchmarks testing asynchronous actions (like the $99.99 deterministic simulated failure) must poll/synchronize for the background state transition before executing subsequent inquiry turns.
- **Non-Prescriptive Prompt State**: System prompts and order summaries must present factual background state (e.g. `PAYMENT STATUS: Failed (...)`) without pre-scripting exact responses or behavioral directives.
- **Deterministic Failure Testing**: Order amounts of `$99.99` deterministically trigger simulated background payment failures ("register malfunction") for BDD and Vertex AI evaluations.
- **Context Prefix Caching**: Evaluation prompts with $>32\text{k}$ tokens must place static rubrics, bartender persona instructions, and menu knowledge at the prompt prefix to trigger GCP's 90% cache discount.

### Rule 8: 100% Cloud-Native Telemetry & Zero-SaaS Isolation
- All telemetry and traces must use OpenTelemetry GenAI Semantic Conventions (`gen_ai.system`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`) and export directly to **Google Cloud Trace**.
- **Zero Third-Party SaaS Credentials**: Flag any PR introducing Weights & Biases / Weave (`WANDB_API_KEY`, `WEAVE_API_KEY`, `weave.init()`), LangSmith, or external SaaS tracing tokens.
- Telemetry and offline evaluation suites must gracefully fall back to local non-blocking Python logging if GCP credentials (ADC) are absent.

### Rule 9: Testing Standards & Review Inclusion
- **Explicit Test Review**: You must explicitly review all changes in test files (`tests/**/*`) alongside implementation changes.
- **No Real Network Calls**: External APIs (Google, Cartesia, Coinbase CDP) must be mocked in tests using native SDK test doubles (see `tests/conftest.py`). Flag any test making live network calls.
- **Rate Limit Isolation**: Tests must bypass global rate limits (`MAYA_SESSION_RATE_LIMIT=9999`) to prevent false-negative token exhaustion errors during test runs.
- **ADK Stream Mock Event Contracts**: Test doubles for Google ADK runner streams (`Runner.run_async`) must set `event.author = 'model'` and populate `event.content.parts = [Mock(text="...")]`. Stream assertions must verify yielded event types (`'text_chunk'`, `'sentence'`, `'complete'`) rather than generic names like `'content'` to ensure fidelity with `process_order_stream` event mapping.

### Rule 10: FastAPI & Decoupled Architecture
- FastAPI is served at the application root (`/`), with native REST/SSE routers mounted at `/api/v1/*` (`session`, `payments`, `chat`), Agent-to-Agent protocol routes at `/a2a/*`, and the Gradio UI mounted under `/ui`.
- All API endpoints must use Pydantic v2 data models (`src/schemas/`) and routers (`src/routers/`).
- Distributed session state must use `get_session_store(request)` to read `request.app.state.session_store` dynamically for multi-container Modal deployments (`max_containers > 1`).

### Rule 11: Specification vs. Implementation PR Phasing
- This project adheres to a spec-driven development lifecycle (`.kiro/specs/<feature-name>/`).
- **Specification PRs**: PRs focused on drafting specs (`design.md`, `requirements.md`, `tasks.md`), configuring tools (like `.greptile/`), or deprecating obsolete dependencies (`requirements.txt`, `.env.example`) MUST NOT be rejected or penalized for deferring full code implementation of the newly specified architecture to subsequent implementation PRs.
- Do NOT demand immediate implementation of planned feature metrics or future code tracks during a specification PR as long as the specification is coherent, existing tests pass, and legacy dependencies are cleanly decoupled.

### Rule 12: Parallel Non-Blocking Component Execution
- Background workers (like chip generation via `ThreadPoolExecutor`) must enforce hard timeouts (3s for chip generation) and never block primary response streams.
- Flag any parallel execution pattern that fails to use `Future.result(timeout=...)` or lacks graceful degradation on timeout/failure.
- Ensure background task cancellation when new user input arrives (e.g., canceling pending chip generation tasks).
- All parallel execution components must use dedicated thread pools with explicit worker limits (max 10 for chip generation).
- **Non-Blocking Streaming Delay Verification**: Tests for parallel background tasks (such as suggestion chips) must verify that the primary streaming response generator (`process_order_stream`) completes promptly (`duration < 0.5s`) without being blocked or delayed by background task latency, timeouts, or simulated failures.

### Rule 13: Structured Output & Pydantic v2 Validation
- LLM structured outputs (JSON schemas) must use Pydantic v2 models with field validators (`@field_validator`).
- Invalid LLM outputs must log validation errors (`ValidationError`) and return graceful fallback values (e.g., empty chip sets, generic greeting chips) without raising exceptions to the user.
- Structured output schemas must enforce constraints (e.g., 3-6 chips, 2-40 character text, unique chip texts case-insensitive).
- Flag any structured output implementation that fails to handle `ValidationError` gracefully or propagates validation exceptions to user-facing code.

### Rule 14: BDD Testing Standards (pytest-bdd)
- Feature-level acceptance tests use pytest-bdd with Gherkin scenarios in `tests/behavior/features/*.feature`.
- Step definitions must reuse existing fixtures (`session_state`, `mock_llm_client`) and mocks from `tests/conftest.py`.
- BDD scenarios must cover:
  - User journeys across conversation phases (greeting, ordering, describing, payment)
  - Accessibility compliance (ARIA labels, keyboard navigation, 44x44px touch targets, 4.5:1 contrast ratios)
  - Error handling and graceful degradation (LLM timeouts, validation failures)
  - State lifecycle (hide/show, persistence, session reset)
- Flag BDD tests that make real network calls or fail to mock external APIs.
- BDD step definitions should follow the pattern: `@given`, `@when`, `@then` decorators with parsers for parameterized scenarios.
- **Production Invalidation Pathway Testing**: BDD acceptance step definitions verifying lifecycle events (cancellation of in-flight tasks, rate limit cooldowns, session resets) must invoke real production entrypoints (such as `process_order_stream` or `_trigger_chip_generation`) rather than manually manipulating mock states or calling `.cancel()` directly on test doubles within test steps.

### Rule 15: Session State Chip Management
- Session state dictionary must include `chip_state` with keys:
  - `current_chips`: `SuggestionChipSet | None`
  - `last_generation_time`: `float | None`
  - `generation_count`: `int`
  - `failure_count`: `int`
  - `pending_task`: `Future | None`
- All chip state updates must acquire the session `RLock` before modification (thread-safe).
- Rate limiting: max 1 chip generation per 2 seconds per session.
- Concurrency limit: max 10 parallel chip generations across all sessions (enforced via `ThreadPoolExecutor` with `max_workers=10`).
- Flag any chip state modification that bypasses the session lock or violates rate/concurrency limits.

### Rule 16: Agentic Developer Tooling: CLI-First Architecture & MCP Boundaries
- **Developer Tooling Scope**: This rule governs AI coding agent workflows (how PR authors and bots develop this repository), NOT Maya's runtime application architecture (which runs as a FastAPI/Modal cloud service with Google ADK 2.0).
- **CLI-First Tooling Architecture**: Coding agents and automation pipelines operate on a **CLI-first, stateful-MCP-sparing architecture**.
- **MCP Reserved Tier (Stateful Integrations Only)**: MCP is strictly reserved for persistent stateful daemons, AST knowledge graphs (`codebase-memory-mcp`), and live browser sessions (`chrome-devtools`).
- **CLI Tier (Stateless Operations)**: All Git/GitHub operations (`git`, `gh`), cloud deployments (`modal`), container management, and build tasks MUST execute via native CLI tools with output hygiene (`--json`, `--limit`, `--format`, `jq`).
- **Prohibition of Stateless MCP**: Reviewers and agents must strictly reject any PR introducing stateless MCP servers (e.g. GitHub MCP, Git MCP, Jira/Slack MCP, Linear MCP, or sequential-thinking tools).
- **GitHub CLI & Git Operational Guardrails**: Feature branches only (`feature/*`, `fix/*`, `chore/*`), pre-commit secret hygiene, zero autonomous merges (`gh pr merge` is prohibited; human review required), and remote tamper protection (`git remote add/set-url` prohibited).
- **CLI Output Hygiene**: Mandate structured projections (`--json`, `--limit`, `--format`) and stream filtering (`jq`, `head`) to prevent context window saturation.
- **Architectural Perpetuation Invariant**: Future agents, child workflows, and pull requests must defend these boundaries and preserve token hygiene indefinitely.

---

## 3. Output Tone
Keep feedback concise, constructive, actionable, and direct. You are acting as an expert pair-programming partner reviewing a high-quality portfolio codebase.
