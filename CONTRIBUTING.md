# Contributing to MayaMCP

Thank you for contributing to MayaMCP! This document provides guidelines for human contributors to ensure our codebase remains clean, testable, and robust.

## Code Architecture & DRY Principles

When writing code for MayaMCP, please adhere to the DRY (Don't Repeat Yourself) principle.

- **Centralized Logic**: Extract repetitive code into well-named helper functions following the single responsibility principle. Most utility functions should live in `src/utils/helpers.py`.
- **Unified LLM Client**: All GenAI calls must go through `src/llm/client.py`. Do not call the Google SDK directly in other modules. Always use `get_genai_client(api_key=...)`.
- **Intent Routing Safety**: When implementing deterministic intent routing (e.g., hardcoded commands like tips or payments), never use simple substring checks (like `'tip' in text`). Always use regex word boundaries (e.g., `re.search(r'\btips?\b', text, re.IGNORECASE)`) to prevent false positives.
- **Streaming Pipeline Guidelines**: Never materialize generators eagerly (such as `list(generator)`) when pipelining stream inputs. Consume them lazily to preserve low latency.
- **Heartbeat Safety**: When reading streaming iterators that yield heartbeat/keep-alive events, ensure you yield the heartbeats immediately but continue draining the iterator in a loop until the matching content chunk is acquired.

## Testing Guidelines

Our test suite aims to be fast, reliable, and decoupled from external services.

### Test Isolation and Mocking

- **No Real API Calls**: Always mock external APIs (Google, Cartesia, Coinbase CDP). Never make real calls in tests.
- **Native SDK Mocking**: When testing Gemini functionality, mock the native `google.genai.Client` and stub its `models.generate_content` / `models.generate_content_stream` returns using standard native formats. Do not use legacy LangChain structures.
- **Stateful Singletons**: The application uses a global singleton for rate limiting (`RateLimiter`). When writing tests, ensure `check_rate_limits` is mocked in fixtures (e.g., returning `(True, "")`) to prevent sequential test execution from accumulating state and failing due to burst limits. Never allow global app rate limits to restrict the standard test suite.
- **Patch Preservation during Refactoring**: When extracting logic into helper functions, do not move the calls to state managers or mocked dependencies into the helper if it bypasses existing `@patch` targets in the test suite. Instead, fetch the data in the original module and pass the data structures into the helper.

## Running Tests and Evaluations

- Run the main test suite with `pytest`.
- For LLM-as-judge evaluation, use the Weave pipeline: `python scripts/run_weave_evals.py`. Ensure `WANDB_API_KEY` is set in your `.env`.

Thank you for helping improve MayaMCP!
