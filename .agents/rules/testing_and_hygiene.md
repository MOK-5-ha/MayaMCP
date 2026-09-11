# Testing, BDD & Evaluation Rules

This document outlines testing standards, mock double conventions, BDD acceptance testing patterns, and evaluation harness rules for MayaMCP.

---

## 1. SDK Mocking & Test Double Contracts

- **Always Mock External APIs**: Always mock external APIs (Google, Cartesia, Coinbase CDP) — never make real calls in tests.
- **Native SDK Mocking**: When testing Gemini functionality, mock the native `google.genai.Client` and stub its `models.generate_content` / `models.generate_content_stream` returns using standard native formats instead of obsolete LangChain structures.
- **Mocking Tools**: Never use "mock-sniffing" wrappers in production code to detect `unittest.mock` objects. Instead, fix the test doubles. When patching tools that used to be invoked via LangChain's `.invoke()`, set both `mock.return_value` and `mock.invoke.return_value` to the expected string to ensure compatibility with both direct calls and legacy test harnesses.
- **Refactoring & Mocks**: When extracting logic into helper functions, do not move the calls to state managers or mocked dependencies into the helper if it bypasses existing `@patch` targets in the test suite. Instead, fetch the data in the original module and pass the data structures into the helper.
- **ADK Model Double Generator Protocol**: Test doubles implementing `Gemini.generate_content_async` must be defined as async generators yielding `LlmResponse.create(...)` rather than coroutines returning responses, matching Google ADK's runner interface.
- **ADK Stream Mock Event Contracts**: When mocking Google ADK runner streams (`Runner.run_async`) for `process_order_stream`, test event doubles must set `event.author = 'model'` and `event.content.parts = [Mock(text="...")]` to trigger token accumulation. Event type assertions must verify the application's actual yielded stream event types (`'text_chunk'`, `'sentence'`, `'complete'`) rather than generic names like `'content'`.
- **Mocking Background Event Loop Dispatch**: When mocking `asyncio.get_running_loop().create_task` in unit tests, configure `mock_loop.create_task.side_effect = lambda coro: coro.close()` to cleanly terminate the coroutine and prevent unawaited coroutine `RuntimeWarning` exceptions during garbage collection.

---

## 2. Rate Limiting & Concurrency Test Safety

- **Rate Limit Testing**: Never allow global app rate limits to restrict the standard test suite, as it causes false-negative token exhaustion errors. Set rate limit environment variables to high values (e.g., `9999`) in `tests/conftest.py`. When testing the rate limiter itself, use context-manager overrides to temporarily enforce limits strictly within those specific tests.
- **Stateful Singletons (Rate Limits)**: The application uses a global singleton for rate limiting (`RateLimiter`). When writing tests, ensure `check_rate_limits` is mocked in fixtures (e.g., returning `(True, "")`) to prevent sequential test execution from accumulating state and failing due to burst limits.
- **Rate Limiter Initialization Timing**: If overriding rate limit constraints via environment variables (e.g. setting `MAYA_SESSION_RATE_LIMIT` to `9999` for tests or evaluations), ensure those environment variables are set *before* importing any package from the application to prevent the `RateLimiter` singleton from initializing with default values.
- **Thread Synchronization in Test Injection Hooks**: Programmatic injection helpers and test validation hooks (e.g., `inject_chips_programmatically`) must always acquire the session `RLock` or delegate to thread-safe state mutators (`update_chip_state`) before modifying session dictionaries. This prevents race conditions with concurrent background workers (e.g., `ThreadPoolExecutor` chip generation or async payment lifecycles) during multi-turn test sequences.
- **Active Test Suite Timers & Progress Monitoring**: When running test suites (especially full suite runs, long-running suites, or background test tasks), never rely on passive, blind waiting. Always set a timer via the `schedule` tool with an estimated upper bound or incremental check intervals (e.g. 10–30s) to monitor test progress, inspect logs, and immediately kill and diagnose hanging test loops, deadlock conditions, or leaking non-daemon background threads.

---

## 3. BDD Acceptance Testing Patterns

- **BDD Test Coverage**: Feature-level acceptance tests use pytest-bdd with Gherkin scenarios (`tests/behavior/features/*.feature`) covering user journeys, accessibility (WCAG 2.1 AA: ARIA, keyboard nav, 44x44px touch targets, 4.5:1 contrast), error handling (timeouts, validation failures), and lifecycle (hide/show, persistence, session reset). Step definitions reuse existing fixtures and mocks.
- **Production Invalidation Pathway Testing**: In BDD and acceptance test suites verifying lifecycle events (such as cancellation of in-flight background tasks, cooldown rate limits, or session sequence invalidation), test steps must invoke real production entrypoints (e.g., `process_order_stream`, `_trigger_chip_generation`, or `reset_session_state`) rather than manually manipulating mock states or directly calling `.cancel()` on test doubles in the test step.
- **State-Direct Negative Verification in BDD Scenarios**: In BDD step definitions asserting negative or cleared states (e.g., verifying no suggestion chips are displayed on timeouts, errors, or phase resets), never use short-circuiting disjunctions on local step context handles (e.g., `assert ctx.chips is None or len(current_chips) == 0`). A `None` context handle upon timeout masks whether stale or default state persisted in storage. Step assertions must verify directly against the canonical session state dictionary (`current_chips = session_state.get("chip_state", {}).get("current_chips"); assert current_chips is None or len(current_chips) == 0`).
- **Component-Level Accessibility Inspection**: When testing accessible UI components (such as ARIA live regions, focus indicators, and screen reader announcements), tests must never assert ARIA attributes against static CSS declarations or style sheets. Component constructors must attach generated HTML sub-components directly to the container object (e.g., `chip_row.live_region_html = live_html`) so unit, integration, and BDD assertions verify the exact rendered DOM attributes and initial markup structure.

---

## 4. Integration & Property-Based Testing

- **Non-Blocking Streaming Stream-to-Background Isolation Verification**: When testing background tasks that run parallel to streaming conversational responses (such as suggestion chips or optimistic background transactions), integration test suites must include end-to-end streaming tests asserting that the streaming response generator (`process_order_stream`) completes prompt delivery without delay (e.g., `duration < 0.5s` well below background timeout ceilings) and yields all expected tokens (`'text_chunk'`, `'complete'`) regardless of background task latency, timeouts, or simulated failures.
- **Schema Invariant Parity in Stale Invalidation Test Fixtures**: When testing that stale background tasks or out-of-order responses are discarded upon session reset or state clearing, test fixtures and mocks must return schema-valid payloads (e.g. satisfying all Pydantic validators, such as >= 3 chips for `SuggestionChipSet`). Returning invalid fixtures causes validation to fail early and return `None`, producing false positives that mask regressions in sequence invalidation.
- **Property Test Timeout Jitter Tolerance**: In Hypothesis property-based tests or concurrency tests verifying timeout boundaries (e.g. 3.0s timeout), avoid testing exact float boundary equality (`delay == timeout`). Add an explicit jitter tolerance margin (e.g. `±0.05s` or evaluating `delay = timeout + 0.5s` for timeout cases vs `delay = 0` for non-timeout cases) to prevent operating system thread scheduling jitter from causing flaky test assertions.

---

## 5. Vertex AI Headless Evaluations & Telemetry

- **Offline Evaluations & Telemetry**: Headless evaluation suites and OpenTelemetry exporters must support running completely offline without demanding remote authentication if GCP Application Default Credentials (ADC) are absent. Provide local test doubles and fallback to standard Python logging to execute evaluations locally.
- **Evaluation Fallback Isolation**: When authoring Agent-as-a-Judge or EvalTask harnesses with local heuristic fallback paths (`is_fallback: bool = True`), evaluation runners and metric aggregators MUST explicitly isolate fallback verdicts from live passing percentages and average score calculations (`isolate_fallback_benchmark_aggregates`), reporting `fallback_count` and fallback scores in a separate section to avoid inflating live pass rates.
- **Asynchronous Lifecycle Evaluation Synchronization**: When evaluating multi-turn conversational agents with asynchronous/background operations (e.g. background blockchain transactions with simulated delays), evaluation benchmark runners must synchronize/poll for terminal state (e.g. `payment_status == 'failed'`) before executing subsequent query turns rather than immediately issuing follow-up turns across an unsettled race condition.
- **Zero-Trust Evaluation Context Delimitation & Sanitization**: Before passing user messages or agent responses to an LLM-as-a-judge, sanitize untrusted strings (`sanitize_eval_input`) to defuse control tokens (`[INST]`, `<<SYS>>`, `<|im_start|>`), instruction override patterns, and score manipulation directives, and wrap dynamic sections in structural XML tags (`<user_turns>`, `<maya_responses>`, `<agent_trajectory>`).
- **Prefix Invariant Caching**: To leverage GCP Context Caching in LLM judge routines, structure prompts with static evaluation rubrics and instructions at the prompt prefix (Invariant Prefix), placing dynamic test case inputs at the prompt tail.
- **Non-Prescriptive Prompt State vs Scripted Responses**: When exposing background failures (like register malfunctions) to conversational agents via system prompt context, provide only factual state indicators (e.g. `PAYMENT STATUS: Failed (register malfunction during settlement)`) rather than prescriptive behavioral instructions (e.g. "Apologize and offer retry"), ensuring evaluation benchmarks measure authentic agent behavior rather than scripted prompt directives.
- **Evaluation Scorer Guard Discipline**: In LLM evaluation scorers checking list outputs (like derived visemes), empty lists `[]` must NOT evaluate to `True` via fall-through guards like `... if visemes else True`. Scorers must strictly enforce non-empty lists (`bool(visemes) and len(visemes) == len(turns)`).
