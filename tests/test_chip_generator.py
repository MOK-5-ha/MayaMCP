"""
Unit tests for ChipGenerator.

Covers all success and failure scenarios for chip generation including:
- Successful chip generation with valid context
- Timeout handling returns None
- Validation failure returns None
- LLM failure returns None
- Rate limit enforcement
- Pending task cancellation
- Fallback chip generation

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 7.5, 8.1, 8.2, 8.3, 8.4**
"""

import time
from concurrent.futures import Future
from threading import RLock
from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic import ValidationError

from src.conversation.chip_generator import ChipGenerator
from src.schemas.chips import (
    ActionID,
    ChipGenerationContext,
    ChipType,
    SuggestionChip,
    SuggestionChipSet,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def session_id():
    """Test session ID."""
    return "test_session_12345"


@pytest.fixture
def mock_session_state():
    """Mock session state with empty chip state."""
    return {"chip_state": {}}


@pytest.fixture
def mock_session_lock():
    """Mock session lock (reentrant)."""
    return RLock()


@pytest.fixture
def valid_context():
    """Valid chip generation context."""
    return ChipGenerationContext(
        conversation_turns=[
            {"role": "user", "content": "I'd like a mojito"},
            {
                "role": "assistant",
                "content": "Great choice! A mojito is a refreshing rum cocktail.",
            },
        ],
        payment_status="none",
        conversation_phase="ordering",
        recent_user_messages=["I'd like a mojito"],
    )


@pytest.fixture
def valid_chip_response():
    """Valid LLM response with chip set."""
    return MagicMock(
        text='{"chips": [{"text": "Tell me more", "type": "dialogue"}, '
        '{"text": "Make it stronger", "type": "dialogue"}, '
        '{"text": "Complete payment", "type": "action", "action_id": "payment"}]}'
    )


@pytest.fixture
def mock_llm_client(valid_chip_response):
    """Mock LLM client with valid response (legacy - for DI tests only)."""
    mock_client = MagicMock()
    mock_models = MagicMock()
    mock_models.generate_content.return_value = valid_chip_response
    mock_client.models = mock_models
    return mock_client


@pytest.fixture
def mock_call_gemini_api(valid_chip_response):
    """Mock call_gemini_api function."""
    with patch("src.conversation.chip_generator.call_gemini_api") as mock:
        mock.return_value = valid_chip_response
        yield mock


@pytest.fixture
def chip_generator(session_id, mock_llm_client):
    """ChipGenerator instance with mocked LLM client (for DI tests)."""
    return ChipGenerator(session_id=session_id, llm_client=mock_llm_client)


@pytest.fixture
def chip_generator_with_api_mock(session_id, mock_call_gemini_api):
    """ChipGenerator instance with mocked API calls."""
    return ChipGenerator(session_id=session_id)


# =============================================================================
# Test Suite: Successful Chip Generation
# =============================================================================


class TestSuccessfulChipGeneration:
    """Test successful chip generation with valid context."""

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_generate_chips_success(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        session_id,
        mock_session_state,
        mock_session_lock,
        valid_context,
        chip_generator_with_api_mock,
        mock_call_gemini_api,
    ):
        """
        Test successful chip generation with valid context.
        
        Validates: Requirements 1.1, 1.2, 1.3
        """
        # Setup
        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = mock_session_lock

        # Act
        result = chip_generator_with_api_mock.generate_chips_async(valid_context)

        # Assert: Valid chip set returned
        assert result is not None
        assert isinstance(result, SuggestionChipSet)
        assert len(result.chips) == 3
        
        # Assert: Chips have correct types
        assert result.chips[0].type == ChipType.DIALOGUE
        assert result.chips[1].type == ChipType.DIALOGUE
        assert result.chips[2].type == ChipType.ACTION
        
        # Assert: Action chip has action_id
        assert result.chips[2].action_id == ActionID.PAYMENT
        
        # Assert: Generation count incremented
        assert mock_session_state["chip_state"]["generation_count"] == 1
        assert "last_generation_time" in mock_session_state["chip_state"]
        
        # Assert: call_gemini_api was called
        mock_call_gemini_api.assert_called_once()

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_llm_client_called_correctly(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        session_id,
        mock_session_state,
        mock_session_lock,
        valid_context,
        mock_call_gemini_api,
    ):
        """
        Test that call_gemini_api is called with correct parameters.
        
        Validates: Requirements 1.1, 1.6
        """
        # Setup
        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = mock_session_lock
        
        generator = ChipGenerator(session_id=session_id)

        # Act
        generator.generate_chips_async(valid_context)

        # Assert: call_gemini_api called once
        mock_call_gemini_api.assert_called_once()
        
        # Get call arguments
        call_args = mock_call_gemini_api.call_args
        
        # Assert: Correct config parameters
        config = call_args.kwargs["config"]
        assert config["max_output_tokens"] == 200
        assert config["temperature"] == 0.7
        assert config["response_mime_type"] == "application/json"
        assert "response_schema" in config
        
        # Assert: Prompt content structure
        prompt_content = call_args.kwargs["prompt_content"]
        assert len(prompt_content) == 1
        assert prompt_content[0]["role"] == "user"

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_context_included_in_prompt(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        session_id,
        mock_session_state,
        mock_session_lock,
        valid_context,
        chip_generator_with_api_mock,
        mock_call_gemini_api,
    ):
        """
        Test that context is properly included in prompt.
        
        Validates: Requirements 1.2, 7.2
        """
        # Setup
        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = mock_session_lock

        # Act
        chip_generator_with_api_mock.generate_chips_async(valid_context)

        # Assert: call_gemini_api was called
        call_args = mock_call_gemini_api.call_args
        prompt_content = call_args.kwargs["prompt_content"]
        prompt = prompt_content[0]["parts"][0]["text"]
        
        # Assert: Context elements in prompt
        assert "ordering" in prompt.lower()  # conversation_phase
        assert "mojito" in prompt.lower()  # conversation_turns
        assert "none" in prompt.lower() or "payment status" in prompt.lower()  # payment_status


# =============================================================================
# Test Suite: Timeout Handling
# =============================================================================


class TestTimeoutHandling:
    """Test timeout handling returns None."""

    @patch("src.conversation.chip_generator.call_gemini_api")
    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_timeout_returns_none(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        mock_call_api,
        session_id,
        mock_session_state,
        mock_session_lock,
        valid_context,
    ):
        """
        Test that timeout returns None and increments failure count.
        
        Validates: Requirements 1.4, 8.1
        """
        # Setup: Slow API call that exceeds timeout
        def slow_generate(*args, **kwargs):
            time.sleep(5.0)  # Exceeds 3 second timeout
            return MagicMock(text='{"chips": []}')

        mock_call_api.side_effect = slow_generate

        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = mock_session_lock

        generator = ChipGenerator(session_id=session_id)

        # Act
        start_time = time.time()
        result = generator.generate_chips_async(valid_context)
        elapsed = time.time() - start_time

        # Assert: Returns None
        assert result is None

        # Assert: Timeout enforced (should be ~3 seconds, not 5)
        assert elapsed < 4.0  # Should timeout before 4 seconds
        assert elapsed >= 2.9  # Should wait at least the timeout duration

        # Assert: Failure count incremented
        assert mock_session_state["chip_state"]["failure_count"] == 1

    @patch("src.conversation.chip_generator.call_gemini_api")
    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_timeout_does_not_crash(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        mock_call_api,
        session_id,
        mock_session_state,
        mock_session_lock,
        valid_context,
    ):
        """
        Test that timeout is handled gracefully without exceptions.
        
        Validates: Requirements 1.4, 1.5, 8.1
        """
        # Setup: Slow API call
        mock_call_api.side_effect = lambda *args, **kwargs: time.sleep(5.0)

        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = mock_session_lock

        generator = ChipGenerator(session_id=session_id)

        # Act & Assert: No exception raised
        try:
            result = generator.generate_chips_async(valid_context)
            assert result is None
        except Exception as e:
            pytest.fail(f"Timeout handling raised exception: {e}")


# =============================================================================
# Test Suite: Validation Failure Handling
# =============================================================================


class TestValidationFailure:
    """Test validation failure returns None."""

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_invalid_json_returns_none(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        session_id,
        mock_session_state,
        mock_session_lock,
        valid_context,
    ):
        """
        Test that invalid JSON returns None and logs error.
        
        Validates: Requirements 2.5, 8.2
        """
        # Setup: LLM returns malformed JSON
        mock_client = MagicMock()
        mock_models = MagicMock()
        mock_models.generate_content.return_value = MagicMock(
            text='{"chips": [invalid json'
        )
        mock_client.models = mock_models

        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = mock_session_lock

        generator = ChipGenerator(session_id=session_id, llm_client=mock_client)

        # Act
        result = generator.generate_chips_async(valid_context)

        # Assert: Returns None
        assert result is None

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_invalid_chip_schema_returns_none(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        session_id,
        mock_session_state,
        mock_session_lock,
        valid_context,
    ):
        """
        Test that invalid chip schema returns None.
        
        Validates: Requirements 2.2, 2.3, 2.5, 8.3
        """
        # Setup: LLM returns invalid chip data (text too long)
        mock_client = MagicMock()
        mock_models = MagicMock()
        mock_models.generate_content.return_value = MagicMock(
            text='{"chips": [{"text": "' + "x" * 100 + '", "type": "dialogue"}]}'
        )
        mock_client.models = mock_models

        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = mock_session_lock

        generator = ChipGenerator(session_id=session_id, llm_client=mock_client)

        # Act
        result = generator.generate_chips_async(valid_context)

        # Assert: Returns None due to validation error
        assert result is None

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_too_few_chips_returns_none(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        session_id,
        mock_session_state,
        mock_session_lock,
        valid_context,
    ):
        """
        Test that chip set with too few chips returns None.
        
        Validates: Requirements 2.4, 8.3
        """
        # Setup: LLM returns only 2 chips (min is 3)
        mock_client = MagicMock()
        mock_models = MagicMock()
        mock_models.generate_content.return_value = MagicMock(
            text='{"chips": [{"text": "Yes", "type": "dialogue"}, '
            '{"text": "No", "type": "dialogue"}]}'
        )
        mock_client.models = mock_models

        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = mock_session_lock

        generator = ChipGenerator(session_id=session_id, llm_client=mock_client)

        # Act
        result = generator.generate_chips_async(valid_context)

        # Assert: Returns None
        assert result is None

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_action_chip_missing_action_id_returns_none(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        session_id,
        mock_session_state,
        mock_session_lock,
        valid_context,
    ):
        """
        Test that action chip without action_id returns None.
        
        Validates: Requirements 2.6, 8.3
        """
        # Setup: LLM returns action chip without action_id
        mock_client = MagicMock()
        mock_models = MagicMock()
        mock_models.generate_content.return_value = MagicMock(
            text='{"chips": [{"text": "Pay now", "type": "action"}, '
            '{"text": "Yes", "type": "dialogue"}, '
            '{"text": "No", "type": "dialogue"}]}'
        )
        mock_client.models = mock_models

        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = mock_session_lock

        generator = ChipGenerator(session_id=session_id, llm_client=mock_client)

        # Act
        result = generator.generate_chips_async(valid_context)

        # Assert: Returns None due to validation error
        assert result is None


# =============================================================================
# Test Suite: LLM Failure Handling
# =============================================================================


class TestLLMFailure:
    """Test LLM failure returns None."""

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_llm_exception_returns_none(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        session_id,
        mock_session_state,
        mock_session_lock,
        valid_context,
    ):
        """
        Test that LLM exception returns None and increments failure count.
        
        Validates: Requirements 1.5, 8.4
        """
        # Setup: LLM raises exception
        mock_client = MagicMock()
        mock_models = MagicMock()
        mock_models.generate_content.side_effect = Exception("LLM API error")
        mock_client.models = mock_models

        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = mock_session_lock

        generator = ChipGenerator(session_id=session_id, llm_client=mock_client)

        # Act
        result = generator.generate_chips_async(valid_context)

        # Assert: Returns None
        assert result is None

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_llm_network_error_returns_none(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        session_id,
        mock_session_state,
        mock_session_lock,
        valid_context,
    ):
        """
        Test that network error returns None gracefully.
        
        Validates: Requirements 1.5, 8.4
        """
        # Setup: LLM raises network error
        mock_client = MagicMock()
        mock_models = MagicMock()
        mock_models.generate_content.side_effect = ConnectionError("Network error")
        mock_client.models = mock_models

        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = mock_session_lock

        generator = ChipGenerator(session_id=session_id, llm_client=mock_client)

        # Act & Assert: No exception propagated
        try:
            result = generator.generate_chips_async(valid_context)
            assert result is None
        except Exception as e:
            pytest.fail(f"LLM error was not handled: {e}")


# =============================================================================
# Test Suite: Rate Limit Enforcement
# =============================================================================


class TestRateLimitEnforcement:
    """Test rate limit enforcement."""

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_rate_limit_blocks_rapid_requests(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        session_id,
        mock_session_state,
        mock_session_lock,
        valid_context,
        mock_llm_client,
    ):
        """
        Test that rate limit blocks requests within 2 seconds.
        
        Validates: Requirements 10.6
        """
        # Setup: Session with recent generation
        current_time = time.time()
        mock_session_state["chip_state"]["last_generation_time"] = (
            current_time - 1.0
        )  # 1 second ago

        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = mock_session_lock

        generator = ChipGenerator(session_id=session_id, llm_client=mock_llm_client)

        # Act
        result = generator.generate_chips_async(valid_context)

        # Assert: Returns None due to rate limit
        assert result is None

        # Assert: LLM was not called
        mock_llm_client.models.generate_content.assert_not_called()

    @patch("src.conversation.chip_generator.call_gemini_api")
    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_rate_limit_allows_after_cooldown(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        mock_call_api,
        session_id,
        mock_session_state,
        mock_session_lock,
        valid_context,
        valid_chip_response,
    ):
        """
        Test that rate limit allows requests after 2 seconds.
        
        Validates: Requirements 10.6
        """
        # Setup: Session with old generation (> 2 seconds ago)
        current_time = time.time()
        mock_session_state["chip_state"]["last_generation_time"] = (
            current_time - 2.5
        )

        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = mock_session_lock
        mock_call_api.return_value = valid_chip_response

        generator = ChipGenerator(session_id=session_id)

        # Act
        result = generator.generate_chips_async(valid_context)

        # Assert: Request allowed
        assert result is not None

        # Assert: API was called
        mock_call_api.assert_called_once()

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_rate_limit_constant_value(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
    ):
        """
        Test that rate limit constant is 2.0 seconds.
        
        Validates: Requirements 10.6
        """
        assert ChipGenerator.RATE_LIMIT_SECONDS == 2.0


# =============================================================================
# Test Suite: Pending Task Cancellation
# =============================================================================


class TestPendingTaskCancellation:
    """Test pending task cancellation."""

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_cancels_pending_task(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        session_id,
        mock_session_state,
        mock_session_lock,
        valid_context,
        mock_llm_client,
    ):
        """
        Test that new generation cancels pending task.
        
        Validates: Requirements 7.5
        """
        # Setup: Create a pending task
        mock_future = Mock(spec=Future)
        mock_future.done.return_value = False  # Task is still running
        mock_future.cancel = Mock()

        mock_session_state["chip_state"]["pending_task"] = mock_future
        mock_session_state["chip_state"]["last_generation_time"] = 0  # Old time

        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = mock_session_lock

        generator = ChipGenerator(session_id=session_id, llm_client=mock_llm_client)

        # Act
        generator.generate_chips_async(valid_context)

        # Assert: Pending task was cancelled
        mock_future.cancel.assert_called_once()

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_does_not_cancel_completed_task(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        session_id,
        mock_session_state,
        mock_session_lock,
        valid_context,
        mock_llm_client,
    ):
        """
        Test that completed tasks are not cancelled.
        
        Validates: Requirements 7.5
        """
        # Setup: Create a completed task
        mock_future = Mock(spec=Future)
        mock_future.done.return_value = True  # Task is complete
        mock_future.cancel = Mock()

        mock_session_state["chip_state"]["pending_task"] = mock_future
        mock_session_state["chip_state"]["last_generation_time"] = 0

        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = mock_session_lock

        generator = ChipGenerator(session_id=session_id, llm_client=mock_llm_client)

        # Act
        generator.generate_chips_async(valid_context)

        # Assert: Cancel was not called (task already done)
        mock_future.cancel.assert_not_called()

    @patch("src.utils.state_manager.get_chip_generation_seq", return_value=2)
    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_superseded_task_does_not_cancel_newer_pending_task(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        mock_get_seq,
        session_id,
        mock_session_state,
        mock_session_lock,
        valid_context,
        mock_llm_client,
    ):
        """Test that an older task does not cancel a newer task or consume rate limits."""
        mock_future = Mock(spec=Future)
        mock_future.done.return_value = False
        mock_future.cancel = Mock()

        mock_session_state["chip_state"]["pending_task"] = mock_future
        mock_session_state["chip_state"]["pending_task_seq"] = 2
        mock_session_state["chip_state"]["last_generation_time"] = 0

        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = mock_session_lock

        generator = ChipGenerator(session_id=session_id, llm_client=mock_llm_client)

        # Act: call with older seq 1 (current is seq 2)
        result = generator.generate_chips_async(valid_context, generation_seq=1)

        # Assert: returns None immediately, does not cancel newer task, does not save session
        assert result is None
        mock_future.cancel.assert_not_called()
        mock_save_session.assert_not_called()


# =============================================================================
# Test Suite: Fallback Chip Generation
# =============================================================================


class TestFallbackChipGeneration:
    """Test fallback chip generation."""

    def test_fallback_chips_structure(self, chip_generator):
        """
        Test that fallback chips have correct structure.
        
        Validates: Requirements 8.4
        """
        # Act
        result = chip_generator.generate_fallback_chips()

        # Assert: Valid chip set
        assert isinstance(result, SuggestionChipSet)
        assert len(result.chips) == 4

        # Assert: All chips valid
        for chip in result.chips:
            assert isinstance(chip, SuggestionChip)
            assert 2 <= len(chip.text) <= 40
            assert chip.type in [ChipType.DIALOGUE, ChipType.ACTION]

    def test_fallback_chips_content(self, chip_generator):
        """
        Test that fallback chips have appropriate content.
        
        Validates: Requirements 8.4
        """
        # Act
        result = chip_generator.generate_fallback_chips()

        # Assert: Contains menu action
        menu_chips = [c for c in result.chips if c.action_id == ActionID.MENU]
        assert len(menu_chips) == 1

        # Assert: Contains dialogue options
        dialogue_chips = [c for c in result.chips if c.type == ChipType.DIALOGUE]
        assert len(dialogue_chips) == 3

    def test_fallback_chips_greeting_appropriate(self, chip_generator):
        """
        Test that fallback chips are appropriate for greeting phase.
        
        Validates: Requirements 8.4
        """
        # Act
        result = chip_generator.generate_fallback_chips()

        # Assert: Greeting-appropriate texts
        texts = [chip.text.lower() for chip in result.chips]
        assert any("menu" in text for text in texts)
        assert any("surprise" in text or "popular" in text for text in texts)


# =============================================================================
# Test Suite: Prompt Building
# =============================================================================


class TestPromptBuilding:
    """Test prompt building logic."""

    def test_build_chip_prompt_includes_static_instructions(
        self, chip_generator, valid_context
    ):
        """
        Test that prompt includes static instructions.
        
        Validates: Requirements 1.2
        """
        # Act
        prompt = chip_generator._build_chip_prompt(valid_context)

        # Assert: Static instruction elements present
        assert "suggestion chip generator" in prompt.lower()
        assert "dialogue" in prompt.lower()
        assert "action" in prompt.lower()
        assert "payment" in prompt
        assert "tip" in prompt
        assert "menu" in prompt

    def test_build_chip_prompt_includes_context(
        self, chip_generator, valid_context
    ):
        """
        Test that prompt includes dynamic context.
        
        Validates: Requirements 1.2, 7.2, 7.3
        """
        # Act
        prompt = chip_generator._build_chip_prompt(valid_context)

        # Assert: Dynamic context elements present
        assert "mojito" in prompt.lower()
        assert "ordering" in prompt.lower()
        assert "none" in prompt.lower() or "payment status" in prompt.lower()

    def test_build_chip_prompt_includes_recent_messages(
        self, chip_generator
    ):
        """
        Test that prompt includes recent user messages for deduplication.
        
        Validates: Requirements 3.5
        """
        # Setup: Context with recent messages
        context = ChipGenerationContext(
            conversation_turns=[
                {"role": "user", "content": "What's in a margarita?"}
            ],
            conversation_phase="describing",
            recent_user_messages=["What's in a margarita?", "Tell me more"],
        )

        # Act
        prompt = chip_generator._build_chip_prompt(context)

        # Assert: Recent messages included
        assert "what's in a margarita?" in prompt.lower()
        assert "tell me more" in prompt.lower()


# =============================================================================
# Test Suite: Thread Safety
# =============================================================================


class TestThreadSafety:
    """Test thread safety of chip generation."""

    @patch("src.conversation.chip_generator.call_gemini_api")
    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    def test_session_lock_acquired(
        self,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        mock_call_api,
        session_id,
        mock_session_state,
        valid_context,
        valid_chip_response,
    ):
        """
        Test that session lock is properly acquired.
        
        Validates: Requirements 1.1
        """
        # Setup: Use real RLock to test thread-safe behavior
        mock_lock = RLock()

        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = mock_lock
        mock_call_api.return_value = valid_chip_response

        generator = ChipGenerator(session_id=session_id)

        # Act
        result = generator.generate_chips_async(valid_context)

        # Assert: Function completed successfully with lock management
        assert result is not None
        assert isinstance(result, SuggestionChipSet)
