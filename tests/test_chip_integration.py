"""Integration tests for chip generation within conversation processor.

This module tests the full flow: user message → response stream → chip generation → session storage.
"""

from threading import RLock
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.conversation.processor import _trigger_chip_generation, process_order_stream
from src.schemas.chips import (
    ActionID,
    ChipGenerationContext,
    ChipType,
    SuggestionChip,
    SuggestionChipSet,
)


@pytest.fixture
def mock_session_state():
    """Mock session state with payment and conversation history."""
    return {
        "conversation_history": [],
        "payment": {"status": "none"},
        "chip_state": {},
    }


@pytest.fixture
def mock_chip_set():
    """Mock chip set for testing."""
    return SuggestionChipSet(
        chips=[
            SuggestionChip(text="Show me the menu", type=ChipType.ACTION, action_id=ActionID.MENU),
            SuggestionChip(text="Surprise me", type=ChipType.DIALOGUE),
            SuggestionChip(text="What's popular?", type=ChipType.DIALOGUE),
            SuggestionChip(text="Something refreshing", type=ChipType.DIALOGUE),
        ]
    )


class TestChipIntegration:
    """Integration tests for chip generation in conversation flow."""

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    @patch("src.conversation.chip_generator.ChipGenerator")
    def test_trigger_chip_generation_with_conversation_history(
        self,
        mock_chip_generator_class,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        mock_session_state,
        mock_chip_set,
    ):
        """Test chip generation is triggered after response with conversation history."""
        # Setup: Mock session state with history
        mock_session_state["conversation_history"] = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! Welcome to Maya's Bar."},
        ]
        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = RLock()
        
        # Setup: Mock chip generator
        mock_generator = Mock()
        mock_generator.generate_chips_async.return_value = mock_chip_set
        mock_chip_generator_class.return_value = mock_generator
        
        # Setup: Truncated history for input
        truncated_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! Welcome to Maya's Bar."},
        ]
        
        # Execute: Trigger chip generation
        _trigger_chip_generation(
            session_id="test_session",
            app_state=None,
            user_message="What do you recommend?",
            maya_response="I'd recommend our signature Old Fashioned!",
            truncated_history=truncated_history,
        )
        
        # Assert: ChipGenerator instantiated with session_id
        mock_chip_generator_class.assert_called_once_with("test_session")
        
        # Assert: generate_chips_async called with correct context
        mock_generator.generate_chips_async.assert_called_once()
        call_args = mock_generator.generate_chips_async.call_args
        context: ChipGenerationContext = call_args[0][0]
        
        assert len(context.conversation_turns) <= 4
        assert context.payment_status == "none"
        assert context.conversation_phase in ["greeting", "ordering", "describing", "payment", "complete"]
        assert len(context.recent_user_messages) <= 2
        
        # Assert: Session data saved at least twice — once for seq claim, once for chips
        assert mock_save_session.call_count >= 2
        # Verify the final write contains the chips
        final_saved_data = mock_save_session.call_args[0][2]
        assert "chip_state" in final_saved_data
        assert final_saved_data["chip_state"]["current_chips"] == mock_chip_set

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    @patch("src.conversation.chip_generator.ChipGenerator")
    def test_trigger_chip_generation_with_empty_history_uses_fallback(
        self,
        mock_chip_generator_class,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        mock_session_state,
        mock_chip_set,
    ):
        """Test fallback chips are generated when conversation history is empty."""
        # Setup: Mock session state with empty history
        mock_session_state["conversation_history"] = []
        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = RLock()
        
        # Setup: Mock chip generator
        mock_generator = Mock()
        mock_generator.generate_fallback_chips.return_value = mock_chip_set
        mock_chip_generator_class.return_value = mock_generator
        
        # Execute: Trigger chip generation with empty history
        _trigger_chip_generation(
            session_id="test_session",
            app_state=None,
            user_message="Hello",
            maya_response="Hi! Welcome to Maya's Bar.",
            truncated_history=[],
        )
        
        # Assert: generate_fallback_chips called instead of generate_chips_async
        mock_generator.generate_fallback_chips.assert_called_once()
        mock_generator.generate_chips_async.assert_not_called()
        
        # Assert: Session data saved at least twice — once for seq claim, once for chips
        assert mock_save_session.call_count >= 2
        # Verify the final write contains the fallback chips
        final_saved_data = mock_save_session.call_args[0][2]
        assert "chip_state" in final_saved_data
        assert final_saved_data["chip_state"]["current_chips"] == mock_chip_set

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    @patch("src.conversation.chip_generator.ChipGenerator")
    def test_trigger_chip_generation_extracts_last_4_turns(
        self,
        mock_chip_generator_class,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        mock_session_state,
        mock_chip_set,
    ):
        """Test chip generation extracts last 4 conversation turns."""
        # Setup: Mock session state with 6 turns
        mock_session_state["conversation_history"] = [
            {"role": "user", "content": "Turn 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Turn 2"},
            {"role": "assistant", "content": "Response 2"},
            {"role": "user", "content": "Turn 3"},
            {"role": "assistant", "content": "Response 3"},
        ]
        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = RLock()
        
        # Setup: Mock chip generator
        mock_generator = Mock()
        mock_generator.generate_chips_async.return_value = mock_chip_set
        mock_chip_generator_class.return_value = mock_generator
        
        # Execute: Trigger chip generation
        truncated_history = mock_session_state["conversation_history"]
        _trigger_chip_generation(
            session_id="test_session",
            app_state=None,
            user_message="Turn 4",
            maya_response="Response 4",
            truncated_history=truncated_history,
        )
        
        # Assert: Context contains exactly last 4 turns
        mock_generator.generate_chips_async.assert_called_once()
        call_args = mock_generator.generate_chips_async.call_args
        context: ChipGenerationContext = call_args[0][0]
        
        assert len(context.conversation_turns) == 4
        # Should contain Turn 3, Response 3, Turn 4, Response 4
        assert context.conversation_turns[0]["content"] == "Turn 3"
        assert context.conversation_turns[1]["content"] == "Response 3"
        assert context.conversation_turns[2]["content"] == "Turn 4"
        assert context.conversation_turns[3]["content"] == "Response 4"

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    @patch("src.conversation.chip_generator.ChipGenerator")
    def test_trigger_chip_generation_extracts_recent_user_messages(
        self,
        mock_chip_generator_class,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        mock_session_state,
        mock_chip_set,
    ):
        """Test chip generation extracts last 2 user messages for deduplication."""
        # Setup: Mock session state with multiple user messages
        mock_session_state["conversation_history"] = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Message 2"},
            {"role": "assistant", "content": "Response 2"},
            {"role": "user", "content": "Message 3"},
            {"role": "assistant", "content": "Response 3"},
        ]
        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = RLock()
        
        # Setup: Mock chip generator
        mock_generator = Mock()
        mock_generator.generate_chips_async.return_value = mock_chip_set
        mock_chip_generator_class.return_value = mock_generator
        
        # Execute: Trigger chip generation
        truncated_history = mock_session_state["conversation_history"]
        _trigger_chip_generation(
            session_id="test_session",
            app_state=None,
            user_message="Message 4",
            maya_response="Response 4",
            truncated_history=truncated_history,
        )
        
        # Assert: Context contains last 2 user messages
        mock_generator.generate_chips_async.assert_called_once()
        call_args = mock_generator.generate_chips_async.call_args
        context: ChipGenerationContext = call_args[0][0]
        
        assert len(context.recent_user_messages) == 2
        assert context.recent_user_messages[0] == "Message 3"
        assert context.recent_user_messages[1] == "Message 4"

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    @patch("src.conversation.chip_generator.ChipGenerator")
    def test_trigger_chip_generation_includes_payment_status(
        self,
        mock_chip_generator_class,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        mock_session_state,
        mock_chip_set,
    ):
        """Test chip generation includes payment status in context."""
        # Setup: Mock session state with pending payment
        mock_session_state["payment"] = {"status": "pending"}
        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = RLock()
        
        # Setup: Mock chip generator
        mock_generator = Mock()
        mock_generator.generate_chips_async.return_value = mock_chip_set
        mock_chip_generator_class.return_value = mock_generator
        
        # Setup: Add some history so fallback isn't triggered
        history = [
            {"role": "user", "content": "What's the total?"},
            {"role": "assistant", "content": "Your total is $12."},
        ]
        
        # Execute: Trigger chip generation
        _trigger_chip_generation(
            session_id="test_session",
            app_state=None,
            user_message="Can I pay now?",
            maya_response="Absolutely! Your total is $12.",
            truncated_history=history,
        )
        
        # Assert: Context includes payment status
        mock_generator.generate_chips_async.assert_called_once()
        call_args = mock_generator.generate_chips_async.call_args
        context: ChipGenerationContext = call_args[0][0]
        
        assert context.payment_status == "pending"

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._get_session_data")
    @patch("src.conversation.chip_generator.ChipGenerator")
    def test_trigger_chip_generation_handles_none_chip_set_gracefully(
        self,
        mock_chip_generator_class,
        mock_get_session,
        mock_get_lock,
        mock_session_state,
    ):
        """Test chip generation handles None result gracefully (timeout/failure)."""
        # Setup: Mock session state
        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = RLock()
        
        # Setup: Mock chip generator returning None (timeout/failure)
        mock_generator = Mock()
        mock_generator.generate_chips_async.return_value = None
        mock_chip_generator_class.return_value = mock_generator
        
        # Execute: Trigger chip generation (should not raise exception)
        try:
            _trigger_chip_generation(
                session_id="test_session",
                app_state=None,
                user_message="Hello",
                maya_response="Hi there!",
                truncated_history=[],
            )
        except Exception as e:
            pytest.fail(f"Chip generation should handle None gracefully, but raised: {e}")
        
        # Assert: No chips stored (None result)
        # This is logged but doesn't block conversation

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._get_session_data")
    @patch("src.conversation.chip_generator.ChipGenerator")
    def test_trigger_chip_generation_handles_exception_gracefully(
        self,
        mock_chip_generator_class,
        mock_get_session,
        mock_get_lock,
        mock_session_state,
    ):
        """Test chip generation handles exceptions gracefully without blocking conversation."""
        # Setup: Mock session state
        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = RLock()
        
        # Setup: Mock chip generator raising exception
        mock_generator = Mock()
        mock_generator.generate_chips_async.side_effect = Exception("LLM API failure")
        mock_chip_generator_class.return_value = mock_generator
        
        # Execute: Trigger chip generation (should not raise exception)
        try:
            _trigger_chip_generation(
                session_id="test_session",
                app_state=None,
                user_message="Hello",
                maya_response="Hi there!",
                truncated_history=[],
            )
        except Exception as e:
            pytest.fail(f"Chip generation should handle exceptions gracefully, but raised: {e}")
        
        # Assert: Exception logged but conversation continues

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    @patch("src.conversation.chip_generator.ChipGenerator")
    @patch("src.conversation.processor.determine_conversation_phase")
    def test_trigger_chip_generation_determines_conversation_phase(
        self,
        mock_determine_phase,
        mock_chip_generator_class,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        mock_session_state,
        mock_chip_set,
    ):
        """Test chip generation determines conversation phase correctly."""
        # Setup: Mock session state
        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = RLock()
        mock_determine_phase.return_value = "ordering"
        
        # Setup: Mock chip generator
        mock_generator = Mock()
        mock_generator.generate_chips_async.return_value = mock_chip_set
        mock_chip_generator_class.return_value = mock_generator
        
        # Setup: Add history so fallback isn't triggered
        history = [
            {"role": "user", "content": "I'm looking for a drink"},
            {"role": "assistant", "content": "I can help with that!"},
        ]
        
        # Execute: Trigger chip generation
        maya_response = "I'll prepare your Old Fashioned right away."
        _trigger_chip_generation(
            session_id="test_session",
            app_state=None,
            user_message="I'll take an Old Fashioned",
            maya_response=maya_response,
            truncated_history=history,
        )
        
        # Assert: determine_conversation_phase called with session data and response
        mock_determine_phase.assert_called_once()
        call_args = mock_determine_phase.call_args
        assert call_args[0][0] == mock_session_state  # session_data
        assert call_args[0][1] == maya_response  # latest_response
        
        # Assert: Context includes detected phase
        mock_generator.generate_chips_async.assert_called_once()
        context_call_args = mock_generator.generate_chips_async.call_args
        context: ChipGenerationContext = context_call_args[0][0]
        assert context.conversation_phase == "ordering"

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    @patch("src.conversation.chip_generator.ChipGenerator")
    def test_trigger_chip_generation_with_explicit_claimed_seq(
        self,
        mock_chip_generator_class,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        mock_session_state,
        mock_chip_set,
    ):
        """Test _trigger_chip_generation accepts claimed generation_seq without overwriting it."""
        mock_session_state["chip_state"] = {"generation_seq": 5}
        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = RLock()

        mock_generator = Mock()
        mock_generator.generate_chips_async.return_value = mock_chip_set
        mock_chip_generator_class.return_value = mock_generator

        history = [{"role": "user", "content": "hi"}]
        _trigger_chip_generation(
            session_id="test_session",
            app_state=None,
            user_message="hi",
            maya_response="Hello!",
            truncated_history=history,
            generation_seq=5,
        )

        # Chips saved with seq 5
        mock_save_session.assert_called_once()
        saved_data = mock_save_session.call_args[0][2]
        assert saved_data["chip_state"]["generation_seq"] == 5
        assert saved_data["chip_state"]["current_chips"] == mock_chip_set

    @patch("src.conversation.processor._chip_trigger_executor")
    @patch("src.conversation.processor.ConversationPhaseManager")
    @patch("src.conversation.processor.get_combined_prompt", return_value="sys prompt")
    @patch("src.llm.tools.get_menu", return_value="menu")
    @patch("src.conversation.processor._build_order_context", return_value="")
    @patch("src.conversation.processor.scan_input")
    @patch("src.conversation.processor.scan_output")
    def test_process_order_stream_claims_seq_in_batch_context(
        self,
        mock_scan_output,
        mock_scan_input,
        mock_order_ctx,
        mock_get_menu,
        mock_combined_prompt,
        mock_phase_manager_class,
        mock_executor,
    ):
        """Test process_order_stream increments generation_seq in batch context and passes it to executor."""
        mock_scan_input.return_value = Mock(is_valid=True, sanitized_text="hello")
        mock_scan_output.return_value = Mock(is_valid=True, sanitized_text="Hello back!")
        mock_phase_manager = Mock()
        mock_phase_manager.get_current_phase.return_value = "greeting"
        mock_phase_manager_class.return_value = mock_phase_manager

        mock_llm = "gemini-2.5-flash"
        # Mock runner event generator
        async def mock_run_async(*args, **kwargs):
            mock_event = MagicMock()
            mock_event.content.parts = [MagicMock(text="Hello back!")]
            yield mock_event

        app_state = {"test_session": {"chip_state": {"generation_seq": 2}}}

        with patch("google.adk.runners.Runner.run_async", side_effect=mock_run_async):
            events = list(process_order_stream(
                user_input_text="hello",
                current_session_history=[],
                llm=mock_llm,
                session_id="test_session",
                app_state=app_state,
            ))

        # Check executor was called with generation_seq=3
        mock_executor.submit.assert_called_once()
        submit_kwargs = mock_executor.submit.call_args[1]
        assert submit_kwargs["generation_seq"] == 3

        # Check store has generation_seq=3 after batch flush
        assert app_state["test_session"]["chip_state"]["generation_seq"] == 3

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    @patch("src.conversation.chip_generator.ChipGenerator")
    def test_trigger_chip_generation_discards_stale_chips_when_superseded(
        self,
        mock_chip_generator_class,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
        mock_session_state,
        mock_chip_set,
    ):
        """Test _trigger_chip_generation discards stale chips when generation_seq is superseded."""
        # Setup: session state has already progressed to seq 3 (e.g. from newer turns)
        mock_session_state["chip_state"] = {"generation_seq": 3}
        mock_get_session.return_value = mock_session_state
        mock_get_lock.return_value = RLock()

        mock_generator = Mock()
        mock_generator.generate_chips_async.return_value = mock_chip_set
        mock_chip_generator_class.return_value = mock_generator

        # Execute: older turn with seq 1 finishes
        history = [{"role": "user", "content": "hi"}]
        _trigger_chip_generation(
            session_id="test_session",
            app_state=None,
            user_message="hi",
            maya_response="Hello!",
            truncated_history=history,
            generation_seq=1,
        )

        # Assert: Chips were NOT saved because seq 1 != current seq 3
        mock_save_session.assert_not_called()


# Mark integration tests
pytestmark = pytest.mark.integration


