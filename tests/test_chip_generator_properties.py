"""
Property-based tests for ChipGenerator timeout enforcement.

Uses Hypothesis for property-based testing. Each test is annotated
with the property or requirement it validates.

**Validates: Requirements 1.4**
"""

import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.conversation.chip_generator import ChipGenerator
from src.schemas.chips import ChipGenerationContext, SuggestionChipSet

# =============================================================================
# Test Configuration
# =============================================================================

# Property tests for timeout enforcement (timeout tests are expensive)
# Using 10 examples to balance coverage vs test execution time
TEST_SETTINGS = settings(max_examples=10, deadline=15000)

# For slow timeout tests that actually sleep, use even fewer examples  
SLOW_TEST_SETTINGS = settings(max_examples=3, deadline=20000)


# =============================================================================
# Strategies (Generators)
# =============================================================================

# Session ID strategy
session_id_strategy = st.text(
    min_size=8,
    max_size=32,
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        min_codepoint=48,
        max_codepoint=122,
    ),
)

# Delay strategy (3.1 to 4.0 seconds - all should timeout, but minimize test time)
timeout_delay_strategy = st.floats(min_value=3.1, max_value=4.0)

# Context strategy for chip generation
conversation_turn_strategy = st.fixed_dictionaries(
    {
        "role": st.sampled_from(["user", "assistant"]),
        "content": st.text(min_size=1, max_size=100),
    }
)

chip_context_strategy = st.builds(
    ChipGenerationContext,
    conversation_turns=st.lists(
        conversation_turn_strategy, min_size=1, max_size=4
    ),
    payment_status=st.sampled_from(
        ["pending", "completed", "failed", "none", None]
    ),
    conversation_phase=st.sampled_from(
        ["greeting", "ordering", "describing", "payment", "complete"]
    ),
    recent_user_messages=st.lists(st.text(min_size=1, max_size=50), max_size=2),
)


# =============================================================================
# Helper Functions
# =============================================================================


def create_slow_llm_mock(delay_seconds: float):
    """
    Create a mock LLM client that simulates slow response WITHOUT actually sleeping.
    
    We use side_effect to raise an exception from the thread pool that will trigger
    timeout, rather than actually sleeping for the delay duration.
    
    Args:
        delay_seconds: Time to sleep before returning response

    Returns:
        Mock LLM client with delayed generate_content
    """
    mock_client = MagicMock()
    mock_models = MagicMock()

    def slow_generate_content(*args, **kwargs):
        """Simulate slow LLM response by sleeping"""
        time.sleep(delay_seconds)
        # Return valid response after delay
        return MagicMock(
            text='{"chips": [{"text": "Yes", "type": "dialogue"}, '
            '{"text": "No", "type": "dialogue"}, '
            '{"text": "Maybe", "type": "dialogue"}]}'
        )

    mock_models.generate_content = slow_generate_content
    mock_client.models = mock_models

    return mock_client


# =============================================================================
# Property Tests
# =============================================================================


class TestChipGeneratorTimeoutProperty:
    """
    **Feature: suggestion-chips, Property 2: Chip generation never exceeds timeout**

    *For any* LLM response that takes longer than 3 seconds, the ChipGenerator
    SHALL return None within the timeout window (3.5 seconds max including overhead).
    The timeout SHALL be enforced via ThreadPoolExecutor.Future.result(timeout=3.0).

    **Validates: Requirements 1.4**
    """

    @pytest.mark.slow
    @SLOW_TEST_SETTINGS
    @given(
        session_id=session_id_strategy,
        delay_seconds=timeout_delay_strategy,
        context=chip_context_strategy,
    )
    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    @patch("src.conversation.chip_generator.get_genai_client")
    def test_timeout_enforcement_with_slow_llm(
        self,
        mock_get_client,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        session_id,
        delay_seconds,
        context,
    ):
        """
        Property 2: Chip generation timeout enforcement (slow LLM response)

        Preconditions:
        - LLM response takes between 3.0 and 10.0 seconds
        - Valid chip generation context provided
        - Session state initialized

        Invariant:
        - generate_chips_async returns None (timeout)
        - Execution time does not exceed 3.5 seconds (3.0s timeout + 0.5s overhead)
        - failure_count increments in session state
        """
        # Setup session state mock (empty state)
        mock_session_data = {"chip_state": {}}
        mock_get_session.return_value = mock_session_data

        # Setup lock mock (reentrant lock)
        from threading import RLock

        mock_lock = RLock()
        mock_get_lock.return_value = mock_lock

        # Setup slow LLM mock
        mock_client = create_slow_llm_mock(delay_seconds)
        mock_get_client.return_value = mock_client

        # Create generator with mocked client
        generator = ChipGenerator(session_id=session_id, llm_client=mock_client)

        # Act: Generate chips with slow LLM
        start_time = time.time()
        result = generator.generate_chips_async(context)
        elapsed_time = time.time() - start_time

        # Assert: Returns None on timeout
        assert (
            result is None
        ), f"Expected None on timeout, got {result} for delay={delay_seconds}s"

        # Assert: Execution time does not exceed timeout + overhead
        max_allowed_time = ChipGenerator.TIMEOUT_SECONDS + 0.5
        assert (
            elapsed_time <= max_allowed_time
        ), f"Execution took {elapsed_time:.2f}s, exceeded max {max_allowed_time}s"

        # Assert: Timeout is enforced (execution time should be close to timeout)
        min_expected_time = ChipGenerator.TIMEOUT_SECONDS - 0.1
        assert (
            elapsed_time >= min_expected_time
        ), f"Execution took {elapsed_time:.2f}s, expected ~{ChipGenerator.TIMEOUT_SECONDS}s"

        # Assert: failure_count incremented in session state
        assert (
            "failure_count" in mock_session_data["chip_state"]
        ), "failure_count should be set in chip_state"
        assert (
            mock_session_data["chip_state"]["failure_count"] == 1
        ), "failure_count should be incremented to 1"

    @TEST_SETTINGS
    @given(
        session_id=session_id_strategy,
        context=chip_context_strategy,
    )
    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    @patch("src.conversation.chip_generator.get_genai_client")
    def test_no_timeout_with_fast_llm(
        self,
        mock_get_client,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        session_id,
        context,
    ):
        """
        Property 2: Chip generation completes within timeout (fast LLM response)

        Preconditions:
        - LLM response takes less than 1.0 seconds
        - Valid chip generation context provided
        - Session state initialized

        Invariant:
        - generate_chips_async returns valid SuggestionChipSet
        - Execution time does not exceed 2.0 seconds
        - generation_count increments in session state
        """
        # Setup session state mock (empty state)
        mock_session_data = {"chip_state": {}}
        mock_get_session.return_value = mock_session_data

        # Setup lock mock
        from threading import RLock

        mock_lock = RLock()
        mock_get_lock.return_value = mock_lock

        # Setup fast LLM mock (instant response)
        mock_client = MagicMock()
        mock_models = MagicMock()
        mock_models.generate_content.return_value = MagicMock(
            text='{"chips": [{"text": "Yes", "type": "dialogue"}, '
            '{"text": "No", "type": "dialogue"}, '
            '{"text": "Maybe", "type": "dialogue"}]}'
        )
        mock_client.models = mock_models
        mock_get_client.return_value = mock_client

        # Create generator with mocked client
        generator = ChipGenerator(session_id=session_id, llm_client=mock_client)

        # Act: Generate chips with fast LLM
        start_time = time.time()
        result = generator.generate_chips_async(context)
        elapsed_time = time.time() - start_time

        # Assert: Returns valid chip set
        assert result is not None, "Expected valid chip set from fast LLM"
        assert isinstance(
            result, SuggestionChipSet
        ), f"Expected SuggestionChipSet, got {type(result)}"
        assert len(result.chips) == 3, f"Expected 3 chips, got {len(result.chips)}"

        # Assert: Execution time is fast (well under timeout)
        assert (
            elapsed_time <= 2.0
        ), f"Fast LLM took {elapsed_time:.2f}s, expected < 2.0s"

        # Assert: generation_count incremented in session state
        assert (
            "generation_count" in mock_session_data["chip_state"]
        ), "generation_count should be set in chip_state"
        assert (
            mock_session_data["chip_state"]["generation_count"] == 1
        ), "generation_count should be incremented to 1"

    @TEST_SETTINGS
    @given(
        session_id=session_id_strategy,
        delay_seconds=st.floats(min_value=2.8, max_value=3.2),
        context=chip_context_strategy,
    )
    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    @patch("src.conversation.chip_generator.get_genai_client")
    def test_timeout_boundary_enforcement(
        self,
        mock_get_client,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        session_id,
        delay_seconds,
        context,
    ):
        """
        Property 2: Chip generation timeout at boundary (edge case)

        Preconditions:
        - LLM response takes 2.8-3.2 seconds (near timeout boundary)
        - Valid chip generation context provided
        - Session state initialized

        Invariant:
        - Delays >= 3.0s return None (timeout)
        - Delays < 3.0s return valid SuggestionChipSet
        - Execution time never exceeds 3.5 seconds
        """
        # Setup session state mock
        mock_session_data = {"chip_state": {}}
        mock_get_session.return_value = mock_session_data

        # Setup lock mock
        from threading import RLock

        mock_lock = RLock()
        mock_get_lock.return_value = mock_lock

        # Setup slow LLM mock
        mock_client = create_slow_llm_mock(delay_seconds)
        mock_get_client.return_value = mock_client

        # Create generator
        generator = ChipGenerator(session_id=session_id, llm_client=mock_client)

        # Act: Generate chips
        start_time = time.time()
        result = generator.generate_chips_async(context)
        elapsed_time = time.time() - start_time

        # Assert: Execution time never exceeds timeout + overhead
        max_allowed_time = ChipGenerator.TIMEOUT_SECONDS + 0.5
        assert (
            elapsed_time <= max_allowed_time
        ), f"Execution took {elapsed_time:.2f}s, exceeded max {max_allowed_time}s"

        # Assert: Result matches expected timeout behavior
        if delay_seconds >= ChipGenerator.TIMEOUT_SECONDS:
            assert (
                result is None
            ), f"Expected timeout (None) for delay={delay_seconds:.2f}s"
            assert (
                "failure_count" in mock_session_data["chip_state"]
            ), "failure_count should be set on timeout"
        else:
            # Delay < 3.0s, should complete successfully
            assert (
                result is not None
            ), f"Expected success for delay={delay_seconds:.2f}s < 3.0s"
            assert isinstance(
                result, SuggestionChipSet
            ), f"Expected SuggestionChipSet, got {type(result)}"

    def test_timeout_constant_value(self):
        """Unit test: Verify timeout constant is 3.0 seconds"""
        assert (
            ChipGenerator.TIMEOUT_SECONDS == 3.0
        ), "TIMEOUT_SECONDS constant should be 3.0"

    @pytest.mark.slow
    def test_timeout_with_real_thread_pool(self):
        """
        Integration test: Verify timeout works with real ThreadPoolExecutor

        This test uses actual threading (not mocks) to validate timeout behavior
        with real concurrent execution.
        """
        from threading import RLock

        session_id = "test_session_real_pool"

        # Setup session state mock
        with patch("src.utils.state_manager._get_session_data") as mock_get:
            with patch(
                "src.utils.state_manager._save_session_data"
            ) as mock_save:
                with patch(
                    "src.utils.state_manager.get_session_lock"
                ) as mock_lock:
                    mock_get.return_value = {"chip_state": {}}
                    mock_lock.return_value = RLock()

                    # Create slow mock client
                    mock_client = create_slow_llm_mock(5.0)

                    # Create generator
                    generator = ChipGenerator(
                        session_id=session_id, llm_client=mock_client
                    )

                    # Create context
                    context = ChipGenerationContext(
                        conversation_turns=[
                            {"role": "user", "content": "Hi"},
                            {"role": "assistant", "content": "Hello!"},
                        ],
                        conversation_phase="greeting",
                    )

                    # Act: Generate chips
                    start_time = time.time()
                    result = generator.generate_chips_async(context)
                    elapsed_time = time.time() - start_time

                    # Assert: Timeout enforced
                    assert result is None, "Expected timeout with 5.0s delay"
                    assert (
                        elapsed_time <= 3.5
                    ), f"Timeout not enforced: {elapsed_time:.2f}s"
                    assert (
                        elapsed_time >= 2.9
                    ), f"Timeout too fast: {elapsed_time:.2f}s"


class TestChipGeneratorRateLimitProperty:
    """
    **Feature: suggestion-chips, Property 3: Rate limit enforcement**

    Rate limiting is tested separately to ensure it doesn't interfere
    with timeout testing. This validates Requirements 10.6.
    """

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    @patch("src.conversation.chip_generator.get_genai_client")
    def test_rate_limit_blocks_rapid_requests(
        self,
        mock_get_client,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
    ):
        """
        Test that rate limiting prevents rapid chip generation requests.

        Validates: Requirements 10.6 (rate limit: 1 request per 2 seconds)
        """
        from threading import RLock

        session_id = "test_session_rate_limit"

        # Setup session state with recent generation time
        current_time = time.time()
        mock_session_data = {
            "chip_state": {
                "last_generation_time": current_time - 1.0,  # 1 second ago
                "generation_count": 1,
            }
        }
        mock_get_session.return_value = mock_session_data
        mock_get_lock.return_value = RLock()

        # Setup fast mock client (instant response)
        mock_client = MagicMock()
        mock_models = MagicMock()
        mock_models.generate_content.return_value = MagicMock(
            text='{"chips": [{"text": "A", "type": "dialogue"}, '
            '{"text": "B", "type": "dialogue"}, '
            '{"text": "C", "type": "dialogue"}]}'
        )
        mock_client.models = mock_models
        mock_get_client.return_value = mock_client

        # Create generator
        generator = ChipGenerator(session_id=session_id, llm_client=mock_client)

        # Create context
        context = ChipGenerationContext(
            conversation_turns=[{"role": "user", "content": "Hi"}],
            conversation_phase="greeting",
        )

        # Act: Try to generate chips (should be blocked by rate limit)
        result = generator.generate_chips_async(context)

        # Assert: Rate limit blocks request
        assert result is None, "Expected None due to rate limit (< 2 seconds elapsed)"

        # Assert: LLM was not called
        mock_models.generate_content.assert_not_called()


# =============================================================================
# Property Tests: Error Handling (Task 12.4)
# =============================================================================

# Strategy for malformed LLM outputs
malformed_json_strategy = st.sampled_from(
    [
        "not json at all",
        "{malformed json",
        '{"chips": [{"text": "hi"}]}',  # Too few chips (<3)
        '{"chips": [{"text": "1", "type": "dialogue"}, {"text": "2", "type": "dialogue"}, {"text": "3", "type": "dialogue"}, {"text": "4", "type": "dialogue"}, {"text": "5", "type": "dialogue"}, {"text": "6", "type": "dialogue"}, {"text": "7", "type": "dialogue"}]}',  # Too many chips (>6)
        '{"chips": [{"text": "x", "type": "dialogue"}, {"text": "y", "type": "dialogue"}, {"text": "z", "type": "dialogue"}]}',  # Text too short (<2 chars)
        '{"chips": [{"text": "' + ("a" * 50) + '", "type": "dialogue"}, {"text": "valid two", "type": "dialogue"}, {"text": "valid three", "type": "dialogue"}]}',  # Text too long (>40 chars)
        '{"chips": [{"text": "Duplicate", "type": "dialogue"}, {"text": "duplicate", "type": "dialogue"}, {"text": "unique", "type": "dialogue"}]}',  # Duplicate texts
        '{"chips": [{"text": "Pay", "type": "action"}, {"text": "A", "type": "dialogue"}, {"text": "B", "type": "dialogue"}]}',  # Action without action_id
        '{"chips": [{"text": "Chat", "type": "dialogue", "action_id": "payment"}, {"text": "A", "type": "dialogue"}, {"text": "B", "type": "dialogue"}]}',  # Dialogue with action_id
        '{"chips": [{"text": "Bad Action", "type": "action", "action_id": "unknown_act"}, {"text": "A", "type": "dialogue"}, {"text": "B", "type": "dialogue"}]}',  # Invalid action_id
    ]
)

# Strategy for LLM exceptions
llm_exception_strategy = st.sampled_from(
    [
        ConnectionError("Network disconnected"),
        TimeoutError("Connection timed out"),
        ValueError("Unexpected response format"),
        RuntimeError("Internal SDK runtime failure"),
        Exception("Generic LLM API error"),
    ]
)


class TestChipGeneratorErrorHandlingProperty:
    """
    **Feature: suggestion-chips, Property 3: All chip generation errors result in empty chips, never exceptions**

    *For any* error condition (malformed JSON, validation failure, LLM exception, timeout),
    the ChipGenerator SHALL:
    1. Return None (empty chip set)
    2. Never raise an exception to the caller
    3. Log the error appropriately
    4. Increment failure_count in session state

    **Validates: Requirements 1.5, 8.1, 8.2, 8.3, 8.5, 8.6**
    """

    @TEST_SETTINGS
    @given(
        session_id=session_id_strategy,
        context=chip_context_strategy,
        malformed_output=malformed_json_strategy,
    )
    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_malformed_and_invalid_outputs_return_none_never_raise(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        session_id,
        context,
        malformed_output,
    ):
        """
        Property 3: Malformed JSON or invalid schema returns None without raising.

        Validates: Requirements 1.5, 2.5, 8.2, 8.3, 8.5
        """
        from threading import RLock

        mock_session_data = {"chip_state": {}}
        mock_get_session.return_value = mock_session_data
        mock_get_lock.return_value = RLock()

        mock_client = MagicMock()
        mock_models = MagicMock()
        mock_models.generate_content.return_value = MagicMock(text=malformed_output)
        mock_client.models = mock_models

        generator = ChipGenerator(session_id=session_id, llm_client=mock_client)

        try:
            result = generator.generate_chips_async(context)
            assert result is None, f"Expected None for invalid output: {malformed_output}"
            assert (
                mock_session_data["chip_state"].get("failure_count", 0) >= 1
            ), "failure_count must be incremented on invalid output"
        except Exception as e:
            pytest.fail(f"generate_chips_async raised an unhandled exception: {e}")

    @TEST_SETTINGS
    @given(
        session_id=session_id_strategy,
        context=chip_context_strategy,
        exception_to_raise=llm_exception_strategy,
    )
    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_llm_exceptions_return_none_never_raise(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        session_id,
        context,
        exception_to_raise,
    ):
        """
        Property 3: LLM exceptions return None without raising to caller.

        Validates: Requirements 1.5, 8.1, 8.4, 8.5, 8.6
        """
        from threading import RLock

        mock_session_data = {"chip_state": {}}
        mock_get_session.return_value = mock_session_data
        mock_get_lock.return_value = RLock()

        mock_client = MagicMock()
        mock_models = MagicMock()
        mock_models.generate_content.side_effect = exception_to_raise
        mock_client.models = mock_models

        generator = ChipGenerator(session_id=session_id, llm_client=mock_client)

        try:
            result = generator.generate_chips_async(context)
            assert result is None, f"Expected None for exception: {exception_to_raise}"
            assert (
                mock_session_data["chip_state"].get("failure_count", 0) >= 1
            ), "failure_count must be incremented on exception"
        except Exception as e:
            pytest.fail(f"generate_chips_async raised an unhandled exception: {e}")

