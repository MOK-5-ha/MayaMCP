"""
Tests for Suggestion Chips Performance, Token Budgets, Caching, and Resource Limits.

Validates:
- Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6
- Properties 29, 30, 31
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from src.conversation.chip_generator import (
    ChipGenerator,
    _chip_executor,
    create_mock_chip_context,
)
from src.llm.client import get_genai_client
from src.schemas.chips import ChipGenerationContext, SuggestionChipSet
from src.utils.state_manager import get_session_state, initialize_state


class TestTokenBudgetCompliance:
    """Tests for token budget compliance (Requirements 10.1, 10.2, Property 29)."""

    def test_prompt_token_count_under_512_tokens(self):
        """Prompt built for chip generation must never exceed 512 tokens (approx 2048 chars)."""
        generator = ChipGenerator(session_id="token-budget-session")

        # Standard context
        std_context = create_mock_chip_context(phase="greeting")
        prompt = generator._build_chip_prompt(std_context)
        # Using standard token approximation (1 token ≈ 4 chars) and word count
        approx_tokens = len(prompt) / 4.0
        assert approx_tokens <= 512, f"Prompt token count {approx_tokens} exceeds 512"

    def test_prompt_token_count_under_512_with_adversarial_large_context(self):
        """Even with massive conversation turns and huge messages, prompt must stay <= 512 tokens."""
        generator = ChipGenerator(session_id="token-budget-large-session")

        # Create massive conversation turns and recent messages
        massive_turns = [
            {"role": "user", "content": "A" * 2000},
            {"role": "assistant", "content": "B" * 2000},
            {"role": "user", "content": "C" * 2000},
            {"role": "assistant", "content": "D" * 2000},
        ]
        massive_messages = ["E" * 1000, "F" * 1000]

        large_context = ChipGenerationContext(
            conversation_turns=massive_turns,
            payment_status="pending",
            conversation_phase="ordering",
            recent_user_messages=massive_messages,
        )

        prompt = generator._build_chip_prompt(large_context)
        approx_tokens = len(prompt) / 4.0
        assert approx_tokens <= 512, f"Large prompt token count {approx_tokens} exceeds 512"

    @patch("src.conversation.chip_generator.call_gemini_api")
    def test_max_output_tokens_limit_enforced(self, mock_gemini):
        """LLM generation config must specify max_output_tokens=200."""
        generator = ChipGenerator(session_id="output-token-session")
        context = create_mock_chip_context(phase="greeting")

        # Configure mock return
        mock_response = MagicMock()
        mock_response.text = '{"chips": [{"text": "Hello", "type": "dialogue"}, {"text": "Menu", "type": "action", "action_id": "menu"}, {"text": "Drink", "type": "dialogue"}]}'
        mock_gemini.return_value = mock_response

        generator._generate_chips_sync(context)
        mock_gemini.assert_called_once()
        _, kwargs = mock_gemini.call_args
        config = kwargs.get("config", {})
        assert config.get("max_output_tokens") == 200
        assert generator.MAX_OUTPUT_TOKENS == 200


class TestContextRepresentationCaching:
    """Tests for conversation context representation caching (Requirement 10.3)."""

    def test_context_caching_reuses_cached_prompt(self):
        """Identical contexts must hit ChipGenerator._cache without re-evaluating prompt logic."""
        generator = ChipGenerator(session_id="cache-test-session")
        context = create_mock_chip_context(phase="greeting")

        assert len(generator._cache) == 0
        prompt1 = generator._build_chip_prompt(context)
        assert len(generator._cache) == 1

        # Second call should retrieve from cache
        prompt2 = generator._build_chip_prompt(context)
        assert prompt1 == prompt2
        assert len(generator._cache) == 1

    def test_context_caching_keys_differentiate_changes(self):
        """Different context parameters must result in separate cache entries."""
        generator = ChipGenerator(session_id="cache-diff-session")
        ctx_greeting = create_mock_chip_context(phase="greeting")
        ctx_ordering = create_mock_chip_context(phase="ordering")

        p_greeting = generator._build_chip_prompt(ctx_greeting)
        p_ordering = generator._build_chip_prompt(ctx_ordering)

        assert p_greeting != p_ordering
        assert len(generator._cache) == 2

    def test_context_cache_bounded_size(self):
        """Cache must bound its size to prevent unbounded memory growth."""
        generator = ChipGenerator(session_id="cache-bounded-session")

        for i in range(60):
            ctx = create_mock_chip_context(
                phase="greeting",
                turns=[{"role": "user", "content": f"Message turn {i}"}],
            )
            generator._build_chip_prompt(ctx)

        assert len(generator._cache) <= 50


class TestResourceLimitsAndClientReuse:
    """Tests for client reuse, concurrency limits, and rate limits (Requirements 10.4, 10.5, 10.6)."""

    def test_gemini_client_reuse_across_instances(self):
        """Multiple ChipGenerator instances must reuse the singleton client without creating new connections."""
        gen1 = ChipGenerator(session_id="sess-1")
        gen2 = ChipGenerator(session_id="sess-2")
        global_client = get_genai_client()

        assert gen1.llm_client is gen2.llm_client
        assert gen1.llm_client is global_client

    def test_concurrency_limit_thread_pool(self):
        """Chip generator thread pool executor must enforce a maximum concurrency limit of 10 workers."""
        assert _chip_executor._max_workers == 10

    def test_rate_limit_enforcement_timing(self):
        """Chip generation requests within 2.0s must be rate-limited and skipped."""
        session_id = "rate-limit-timing-session"
        initialize_state(session_id)

        generator = ChipGenerator(session_id=session_id, test_mode=True)
        context = create_mock_chip_context(phase="greeting")

        # First request succeeds
        res1 = generator.generate_chips_async(context)
        assert res1 is not None

        # Immediate second request should be rate-limited
        res2 = generator.generate_chips_async(context)
        assert res2 is None

        # Manually backdate last_generation_time in session state by 2.1s
        state = get_session_state(session_id)
        state["chip_state"]["last_generation_time"] = time.time() - 2.1

        # Request after rate limit interval should succeed
        res3 = generator.generate_chips_async(context)
        assert res3 is not None
