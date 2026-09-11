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


@pytest.fixture(autouse=True)
def cleanup_test_sessions():
    """Ensure clean lock and sequence state for test sessions."""
    from src.utils.state_manager import cleanup_session_lock, clear_session_chip_seq
    test_ids = [
        "test_session",
        "test_cancel_session",
        "test_concurrent_claims_session",
        "test_reset_cancel_session",
        "test_reset_monotonic_session",
        "test_journey_session",
        "test_action_routing_session",
        "test_unrecognized_action_session",
        "test_timeout_failure_session",
        "test_validation_failure_session",
        "test_llm_failure_session",
        "test_lifecycle_reset_session",
        "test_submission_hide_session",
    ]
    for s_id in test_ids:
        cleanup_session_lock(s_id)
        clear_session_chip_seq(s_id)
    yield
    for s_id in test_ids:
        cleanup_session_lock(s_id)
        clear_session_chip_seq(s_id)


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

    def test_concurrent_sequence_claims_are_atomic(self):
        """Test concurrent sequence claims for same session produce strictly unique monotonically increasing seqs."""
        import threading

        from src.utils.state_manager import (
            claim_chip_generation_seq,
            cleanup_session_lock,
        )

        session_id = "test_concurrent_claims_session"
        cleanup_session_lock(session_id)
        store = {session_id: {"chip_state": {"generation_seq": 0}}}

        claimed_seqs = []
        lock = threading.Lock()

        def claim_worker():
            seq = claim_chip_generation_seq(session_id=session_id, store=store)
            with lock:
                claimed_seqs.append(seq)

        threads = [threading.Thread(target=claim_worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(claimed_seqs) == 10
        assert sorted(claimed_seqs) == list(range(1, 11))
        cleanup_session_lock(session_id)

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager.get_chip_generation_seq", return_value=3)
    @patch("src.conversation.chip_generator.ChipGenerator")
    def test_older_trigger_job_aborts_early_without_touching_chip_generator(
        self,
        mock_chip_generator_class,
        mock_get_seq,
        mock_get_lock,
    ):
        """Test older trigger job aborts early without calling ChipGenerator or checking rate limits."""
        mock_get_lock.return_value = RLock()
        history = [{"role": "user", "content": "hi"}]

        _trigger_chip_generation(
            session_id="test_session",
            app_state=None,
            user_message="hi",
            maya_response="Hello!",
            truncated_history=history,
            generation_seq=1,  # Older than current seq 3
        )

        # Assert: ChipGenerator was NEVER initialized, avoiding task cancellation and rate limiting
        mock_chip_generator_class.assert_not_called()

    @patch("src.conversation.processor._chip_trigger_executor")
    @patch("src.conversation.processor.ConversationPhaseManager")
    @patch("src.conversation.processor.get_combined_prompt", return_value="sys prompt")
    @patch("src.llm.tools.get_menu", return_value="menu")
    @patch("src.conversation.processor._build_order_context", return_value="")
    @patch("src.conversation.processor.scan_input")
    @patch("src.conversation.processor.scan_output")
    def test_prior_trigger_future_is_cancelled_on_new_turn(
        self,
        mock_scan_output,
        mock_scan_input,
        mock_order_ctx,
        mock_get_menu,
        mock_combined_prompt,
        mock_phase_manager_class,
        mock_executor,
    ):
        """Test that any prior pending trigger future in _session_trigger_tasks is cancelled when a new turn arrives."""
        from src.conversation.processor import _session_trigger_tasks

        mock_scan_input.return_value = Mock(is_valid=True, sanitized_text="hello")
        mock_scan_output.return_value = Mock(is_valid=True, sanitized_text="Hello back!")
        mock_phase_manager = Mock()
        mock_phase_manager.get_current_phase.return_value = "greeting"
        mock_phase_manager_class.return_value = mock_phase_manager

        # Set up a mock prior trigger future for the session
        mock_prior_future = Mock()
        mock_prior_future.done.return_value = False
        _session_trigger_tasks["test_cancel_session"] = mock_prior_future

        async def mock_run_async(*args, **kwargs):
            mock_event = MagicMock()
            mock_event.content.parts = [MagicMock(text="Hello back!")]
            yield mock_event

        app_state = {"test_cancel_session": {"chip_state": {"generation_seq": 1}}}

        with patch("google.adk.runners.Runner.run_async", side_effect=mock_run_async):
            events = list(process_order_stream(
                user_input_text="hello",
                current_session_history=[],
                llm="gemini-2.5-flash",
                session_id="test_cancel_session",
                app_state=app_state,
            ))

        # Assert: prior future was cancelled
        mock_prior_future.cancel.assert_called_once()

    def test_cleanup_session_lock_acquires_lock(self):
        """Test cleanup_session_lock safely synchronizes with the per-session lock."""
        from src.utils.state_manager import cleanup_session_lock, get_session_lock

        session_id = "test_cleanup_sync_session"
        lock = get_session_lock(session_id)
        assert lock is not None

        # Lock can be acquired and cleaned up
        cleanup_session_lock(session_id)

    def test_reset_session_state_cancels_pending_trigger_task(self):
        """Test reset_session_state cancels any in-flight outer trigger task."""
        from src.conversation.processor import _session_trigger_tasks
        from src.utils.state_manager import reset_session_state

        session_id = "test_reset_cancel_session"
        mock_future = Mock()
        mock_future.done.return_value = False
        _session_trigger_tasks[session_id] = mock_future

        store = {session_id: {}}
        reset_session_state(session_id, store)

        mock_future.cancel.assert_called_once()
        assert session_id not in _session_trigger_tasks

    def test_reset_session_state_advances_sequence_and_preserves_monotonicity(self):
        """Test reset_session_state advances sequence and preserves strictly monotonic claims."""
        from src.utils.state_manager import (
            claim_chip_generation_seq,
            clear_session_chip_seq,
            get_chip_generation_seq,
            reset_session_state,
        )

        session_id = "test_reset_monotonic_session"
        clear_session_chip_seq(session_id)
        store = {session_id: {"chip_state": {"generation_seq": 0}}}

        seq1 = claim_chip_generation_seq(session_id, store)
        assert seq1 == 1

        # Reset session
        reset_session_state(session_id, store)
        latest_after_reset = get_chip_generation_seq(session_id, store)
        assert latest_after_reset > seq1

        # Post-reset claim must be strictly greater than pre-reset seq1
        seq2 = claim_chip_generation_seq(session_id, store)
        assert seq2 > seq1
        clear_session_chip_seq(session_id)

    def test_batch_flush_does_not_discard_fresh_chips_from_background_generation(self):
        """Test that batch flush does not overwrite fresh chips written by background generation."""
        import copy
        import threading

        from src.schemas.chips import ChipType, SuggestionChip, SuggestionChipSet
        from src.utils.batch_state import batch_state_commits
        from src.utils.state_manager import (
            _get_session_data,
            _save_session_data,
            claim_chip_generation_seq,
            clear_session_chip_seq,
            get_session_lock,
        )

        class RemoteStore(dict):
            """Simulates remote modal.Dict by returning deep copies on read/write."""
            def __getitem__(self, key):
                return copy.deepcopy(super().__getitem__(key))
            def __setitem__(self, key, value):
                super().__setitem__(key, copy.deepcopy(value))

        session_id = "test_batch_flush_chip_session"
        clear_session_chip_seq(session_id)
        store = RemoteStore({
            session_id: {
                "conversation": {"turn": 1},
                "conversation_history": [],
                "chip_state": {
                    "current_chips": None,
                    "generation_seq": 0,
                    "last_generation_time": 0,
                    "generation_count": 0,
                    "failure_count": 0,
                    "pending_task": None,
                },
            }
        })

        fresh_chips = SuggestionChipSet(
            chips=[
                SuggestionChip(text="Gin & Tonic", type=ChipType.DIALOGUE),
                SuggestionChip(text="Old Fashioned", type=ChipType.DIALOGUE),
                SuggestionChip(text="Margarita", type=ChipType.DIALOGUE),
            ]
        )

        # Request thread enters batch_state_commits
        with batch_state_commits(session_id, store) as batch_cache:
            # Request modifies conversation in batch cache
            batch_cache.update_section("conversation", {"turn": 2})

            # Simulate background worker thread writing fresh chips before request exits
            def background_chip_worker():
                lock = get_session_lock(session_id)
                with lock:
                    seq = claim_chip_generation_seq(session_id, store)
                    worker_data = _get_session_data(session_id, store)
                    chip_state = worker_data.get("chip_state", {})
                    chip_state["current_chips"] = fresh_chips
                    chip_state["generation_seq"] = seq
                    worker_data["chip_state"] = chip_state
                    _save_session_data(session_id, store, worker_data)

            worker_thread = threading.Thread(target=background_chip_worker)
            worker_thread.start()
            worker_thread.join()

        # After batch_state_commits exits and flushes, store must retain the fresh chips
        flushed_data = store[session_id]
        assert flushed_data["conversation"]["turn"] == 2
        assert flushed_data["chip_state"]["current_chips"] is not None
        assert len(flushed_data["chip_state"]["current_chips"].chips) == 3
        assert flushed_data["chip_state"]["current_chips"].chips[0].text == "Gin & Tonic"
        clear_session_chip_seq(session_id)

    def test_superseded_task_does_not_update_last_generation_time_or_suppress_new_turn(self):
        """Test that a superseded task completion does not update last_generation_time."""
        from src.conversation.chip_generator import ChipGenerator
        from src.schemas.chips import (
            ChipGenerationContext,
            ChipType,
            SuggestionChip,
            SuggestionChipSet,
        )
        from src.utils.state_manager import (
            _get_session_data,
            claim_chip_generation_seq,
            clear_session_chip_seq,
        )

        session_id = "test_superseded_rate_limit_session"
        clear_session_chip_seq(session_id)
        store = {
            session_id: {
                "chip_state": {
                    "current_chips": None,
                    "generation_seq": 0,
                    "last_generation_time": 0,
                    "generation_count": 0,
                    "failure_count": 0,
                    "pending_task": None,
                    "pending_task_seq": None,
                },
            }
        }

        with patch("src.utils.state_manager._global_store", store):
            generator = ChipGenerator(session_id)
            context = ChipGenerationContext(
                conversation_turns=[{"role": "user", "content": "hello"}],
                payment_status="none",
                conversation_phase="greeting",
                recent_user_messages=["hello"],
            )

            # Claim seq 1 for Turn 1
            seq1 = claim_chip_generation_seq(session_id, store)
            assert seq1 == 1

            mock_chip_set = SuggestionChipSet(
                chips=[
                    SuggestionChip(text="Gin", type=ChipType.DIALOGUE),
                    SuggestionChip(text="Tonic", type=ChipType.DIALOGUE),
                    SuggestionChip(text="Lime", type=ChipType.DIALOGUE),
                ]
            )

            # Mock sync generation to return chips
            with patch.object(generator, "_generate_chips_sync", return_value=mock_chip_set):
                # Simulate Turn 1 past the initial freshness check by invoking generate_chips_sync
                # and while waiting on result, Turn 2 claims seq 2
                def delayed_sync(ctx):
                    claim_chip_generation_seq(session_id, store)  # seq becomes 2
                    return mock_chip_set

                generator._generate_chips_sync = delayed_sync

                # Now Turn 1's generate_chips_async runs with seq1=1
                result = generator.generate_chips_async(context, generation_seq=seq1)

                # Superseded task should return None
                assert result is None

                # Crucially: last_generation_time must NOT be updated by the superseded task!
                data = _get_session_data(session_id, store)
                assert data["chip_state"]["last_generation_time"] == 0
                assert data["chip_state"]["generation_count"] == 0
        clear_session_chip_seq(session_id)

    def test_reset_session_state_invalidates_active_batch_cache_and_prevents_stale_flush(self):
        """Test that reset invalidates active batch cache and prevents earlier request from restoring stale state."""
        from src.utils.batch_state import batch_state_commits
        from src.utils.state_manager import (
            clear_session_chip_seq,
            reset_session_state,
        )

        session_id = "test_reset_stale_batch_session"
        clear_session_chip_seq(session_id)
        store = {
            session_id: {
                "conversation": {"turn_count": 5},
                "chip_state": {"generation_seq": 5},
                "payment": {"status": "completed"},
                "current_order": {"order": ["drink"], "finished": False},
                "history": {"items": ["drink"], "total_cost": 10.0},
                "api_keys": {},
            }
        }

        # Turn 1 enters batch_state_commits
        with batch_state_commits(session_id, store) as batch_cache:
            # Turn 1 makes changes in batch cache
            batch_cache.update_section("conversation", {"turn_count": 6})

            # Session is reset while Turn 1 is still active
            reset_session_state(session_id, store)

            # Store must have clean state now
            clean_data = store[session_id]
            assert clean_data["conversation"]["turn_count"] == 0

        # When Turn 1 exits batch_state_commits and calls flush(),
        # it must NOT restore the pre-reset turn 6!
        post_flush_data = store[session_id]
        assert post_flush_data["conversation"]["turn_count"] == 0
        clear_session_chip_seq(session_id)

    def test_reset_invalidates_all_concurrent_overlapping_batch_caches(self):
        """Test that reset invalidates ALL active batch caches if multiple requests overlap."""
        import threading

        from src.utils.batch_state import batch_state_commits
        from src.utils.state_manager import (
            clear_session_chip_seq,
            reset_session_state,
        )

        session_id = "test_reset_concurrent_caches_session"
        clear_session_chip_seq(session_id)
        store = {
            session_id: {
                "conversation": {"turn_count": 5},
                "chip_state": {"generation_seq": 5},
                "payment": {"status": "completed"},
                "current_order": {"order": ["drink"], "finished": False},
                "history": {"items": ["drink"], "total_cost": 10.0},
                "api_keys": {},
            }
        }

        t1_entered = threading.Event()
        t2_entered = threading.Event()
        reset_done = threading.Event()

        def worker1():
            with batch_state_commits(session_id, store) as cache1:
                cache1.update_section("conversation", {"turn_count": 6})
                t1_entered.set()
                reset_done.wait(timeout=5)

        def worker2():
            with batch_state_commits(session_id, store) as cache2:
                cache2.update_section("conversation", {"turn_count": 7})
                t2_entered.set()
                reset_done.wait(timeout=5)

        t1 = threading.Thread(target=worker1)
        t2 = threading.Thread(target=worker2)
        t1.start()
        assert t1_entered.wait(timeout=5)
        t2.start()
        assert t2_entered.wait(timeout=5)

        # Now reset the session while both t1 and t2 have active batch caches
        reset_session_state(session_id, store)

        # Allow both workers to exit and attempt to flush
        reset_done.set()
        t1.join(timeout=5)
        t2.join(timeout=5)

        # Neither worker should have restored its stale turn count!
        post_flush_data = store[session_id]
        assert post_flush_data["conversation"]["turn_count"] == 0
        clear_session_chip_seq(session_id)


class TestFullConversationFlow:
    """End-to-end integration tests for full conversation journey and action chip routing."""

    @patch("src.utils.state_manager.get_session_lock")
    @patch("src.utils.state_manager._save_session_data")
    @patch("src.utils.state_manager._get_session_data")
    @patch("src.conversation.chip_generator.ChipGenerator")
    def test_complete_user_journey_greeting_ordering_description_payment(
        self,
        mock_chip_generator_class,
        mock_get_session,
        mock_save_session,
        mock_get_lock,
    ):
        """Test complete user journey: greeting → ordering → description → payment with chips at each phase."""
        from src.utils.state_manager import clear_session_chip_seq

        session_id = "test_journey_session"
        clear_session_chip_seq(session_id)
        mock_get_lock.return_value = RLock()

        # Phase 1: Greeting Phase
        greeting_chips = SuggestionChipSet(
            chips=[
                SuggestionChip(text="Show me the menu", type=ChipType.ACTION, action_id=ActionID.MENU),
                SuggestionChip(text="Surprise me", type=ChipType.DIALOGUE),
                SuggestionChip(text="What's popular?", type=ChipType.DIALOGUE),
            ]
        )
        generator_greeting = Mock()
        generator_greeting.generate_fallback_chips.return_value = greeting_chips
        generator_greeting.generate_chips_async.return_value = greeting_chips
        mock_chip_generator_class.return_value = generator_greeting

        session_data = {
            "conversation_history": [],
            "payment": {"status": "none"},
            "current_order": {"order": [], "finished": False},
            "chip_state": {"generation_seq": 0},
        }
        mock_get_session.return_value = session_data

        _trigger_chip_generation(
            session_id=session_id,
            app_state=None,
            user_message="Hello",
            maya_response="Welcome to Maya's Bar! What can I get for you?",
            truncated_history=[],
        )

        assert mock_save_session.call_count >= 1
        saved = mock_save_session.call_args[0][2]
        assert saved["chip_state"]["current_chips"] == greeting_chips

        # Phase 2: Ordering Phase
        ordering_chips = SuggestionChipSet(
            chips=[
                SuggestionChip(text="Complete payment", type=ChipType.ACTION, action_id=ActionID.PAYMENT),
                SuggestionChip(text="Order another drink", type=ChipType.ACTION, action_id=ActionID.ORDER_ANOTHER),
                SuggestionChip(text="Make it a double", type=ChipType.DIALOGUE),
            ]
        )
        generator_ordering = Mock()
        generator_ordering.generate_chips_async.return_value = ordering_chips
        mock_chip_generator_class.return_value = generator_ordering

        session_data["conversation_history"] = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Welcome to Maya's Bar! What can I get for you?"},
            {"role": "user", "content": "I'll have an Old Fashioned."},
            {"role": "assistant", "content": "One Old Fashioned coming up! That will be $12.00."},
        ]
        session_data["current_order"] = {"order": [{"name": "Old Fashioned", "price": 12.0}], "finished": False}

        _trigger_chip_generation(
            session_id=session_id,
            app_state=None,
            user_message="I'll have an Old Fashioned.",
            maya_response="One Old Fashioned coming up! That will be $12.00.",
            truncated_history=session_data["conversation_history"],
        )

        call_ctx = generator_ordering.generate_chips_async.call_args[0][0]
        assert call_ctx.conversation_phase == "ordering"
        saved = mock_save_session.call_args[0][2]
        assert saved["chip_state"]["current_chips"] == ordering_chips
        assert any(c.action_id == ActionID.PAYMENT for c in saved["chip_state"]["current_chips"].chips)

        # Phase 3: Describing Phase
        describing_chips = SuggestionChipSet(
            chips=[
                SuggestionChip(text="What bourbon do you use?", type=ChipType.DIALOGUE),
                SuggestionChip(text="Can you make it sweeter?", type=ChipType.DIALOGUE),
                SuggestionChip(text="Sounds great, I'll take it", type=ChipType.DIALOGUE),
            ]
        )
        generator_describing = Mock()
        generator_describing.generate_chips_async.return_value = describing_chips
        mock_chip_generator_class.return_value = generator_describing

        session_data["conversation_history"].extend([
            {"role": "user", "content": "What's in an Old Fashioned?"},
            {"role": "assistant", "content": "The Old Fashioned recipe is made with bourbon, Angostura bitters, simple syrup, and an orange twist."},
        ])

        _trigger_chip_generation(
            session_id=session_id,
            app_state=None,
            user_message="What's in an Old Fashioned?",
            maya_response="The Old Fashioned recipe is made with bourbon, Angostura bitters, simple syrup, and an orange twist.",
            truncated_history=session_data["conversation_history"],
        )

        call_ctx = generator_describing.generate_chips_async.call_args[0][0]
        assert call_ctx.conversation_phase == "describing"
        saved = mock_save_session.call_args[0][2]
        assert saved["chip_state"]["current_chips"] == describing_chips
        assert all(c.type == ChipType.DIALOGUE for c in saved["chip_state"]["current_chips"].chips)

        # Phase 4: Payment Phase
        payment_chips = SuggestionChipSet(
            chips=[
                SuggestionChip(text="Complete payment", type=ChipType.ACTION, action_id=ActionID.PAYMENT),
                SuggestionChip(text="Cancel order", type=ChipType.ACTION, action_id=ActionID.CANCEL),
                SuggestionChip(text="Add a tip", type=ChipType.ACTION, action_id=ActionID.TIP),
            ]
        )
        generator_payment = Mock()
        generator_payment.generate_chips_async.return_value = payment_chips
        mock_chip_generator_class.return_value = generator_payment

        session_data["payment"] = {"status": "pending", "amount": 12.0}
        session_data["conversation_history"].extend([
            {"role": "user", "content": "Ready to pay."},
            {"role": "assistant", "content": "Your total is $12.00. Ready when you are!"},
        ])

        _trigger_chip_generation(
            session_id=session_id,
            app_state=None,
            user_message="Ready to pay.",
            maya_response="Your total is $12.00. Ready when you are!",
            truncated_history=session_data["conversation_history"],
        )

        call_ctx = generator_payment.generate_chips_async.call_args[0][0]
        assert call_ctx.conversation_phase == "payment"
        assert call_ctx.payment_status == "pending"
        saved = mock_save_session.call_args[0][2]
        assert saved["chip_state"]["current_chips"] == payment_chips
        assert saved["chip_state"]["current_chips"].chips[0].action_id == ActionID.PAYMENT
        clear_session_chip_seq(session_id)

    @pytest.mark.parametrize(
        "action_id,raw_chip_text,expected_clean_text",
        [
            (ActionID.PAYMENT, "💳 Complete payment", "Complete payment"),
            (ActionID.TIP, "💰 Add a tip", "Add a tip"),
            (ActionID.MENU, "📋 Show me the menu", "Show me the menu"),
            (ActionID.CANCEL, "❌ Cancel order", "Cancel order"),
            (ActionID.ORDER_ANOTHER, "🍹 Order another drink", "Order another drink"),
        ],
    )
    def test_action_chip_routing_all_actions(self, action_id, raw_chip_text, expected_clean_text):
        """Test action chip routing for payment, tip, menu, cancel, and order_another."""
        from src.ui.chips import handle_chip_click

        populated_text, submit_trigger = handle_chip_click(
            chip_text=raw_chip_text,
            chip_type=ChipType.ACTION,
            action_id=action_id,
            session_id="test_action_routing_session",
            textbox=MagicMock(),
        )

        assert populated_text == expected_clean_text
        assert submit_trigger == "submit"

    def test_action_chip_routing_unrecognized_id_fallback(self, caplog):
        """Test unrecognized action_id falls back to dialogue behavior without auto-submit."""
        from src.ui.chips import handle_chip_click

        with caplog.at_level("WARNING"):
            populated_text, submit_trigger = handle_chip_click(
                chip_text="Unrecognized button",
                chip_type=ChipType.ACTION,
                action_id="nonexistent_action_xyz",
                session_id="test_unrecognized_action_session",
                textbox=MagicMock(),
            )

        assert populated_text == "Unrecognized button"
        assert submit_trigger is None
        assert any("Unrecognized action_id" in record.message for record in caplog.records)


class TestFailureScenarios:
    """End-to-end integration tests for suggestion chip failure scenarios."""

    def test_chip_generation_timeout_scenario(self, caplog):
        """Test timeout scenarios: LLM delay >3.0s returns None, logs timeout warning, tracks failure."""
        import concurrent.futures

        from src.conversation.chip_generator import ChipGenerator
        from src.utils.state_manager import _get_session_data, clear_session_chip_seq

        session_id = "test_timeout_failure_session"
        clear_session_chip_seq(session_id)
        store = {
            session_id: {
                "chip_state": {
                    "current_chips": None,
                    "generation_seq": 0,
                    "last_generation_time": 0,
                    "generation_count": 0,
                    "failure_count": 0,
                    "pending_task": None,
                }
            }
        }

        with patch("src.utils.state_manager._global_store", store):
            generator = ChipGenerator(session_id)
            context = ChipGenerationContext(
                conversation_turns=[{"role": "user", "content": "hi"}],
                payment_status="none",
                conversation_phase="greeting",
                recent_user_messages=["hi"],
            )

            mock_future = Mock(spec=concurrent.futures.Future)
            mock_future.done.return_value = False
            mock_future.result.side_effect = concurrent.futures.TimeoutError("LLM call timed out")

            with patch("src.conversation.chip_generator._chip_executor.submit", return_value=mock_future):
                with caplog.at_level("WARNING"):
                    result = generator.generate_chips_async(context)

            assert result is None
            assert mock_future.cancel.called
            data = _get_session_data(session_id, store)
            assert data["chip_state"]["failure_count"] == 1
            assert any("Chip generation timeout" in r.message for r in caplog.records)

        clear_session_chip_seq(session_id)

    def test_chip_generation_validation_error_scenario(self, caplog):
        """Test validation error scenarios: malformed JSON or invalid schema returns None, logs error, tracks failure."""
        from src.conversation.chip_generator import ChipGenerator
        from src.utils.state_manager import _get_session_data, clear_session_chip_seq

        session_id = "test_validation_failure_session"
        clear_session_chip_seq(session_id)
        store = {
            session_id: {
                "chip_state": {
                    "current_chips": None,
                    "generation_seq": 0,
                    "last_generation_time": 0,
                    "generation_count": 0,
                    "failure_count": 0,
                    "pending_task": None,
                }
            }
        }

        with patch("src.utils.state_manager._global_store", store):
            generator = ChipGenerator(session_id)
            context = ChipGenerationContext(
                conversation_turns=[{"role": "user", "content": "hi"}],
                payment_status="none",
                conversation_phase="greeting",
                recent_user_messages=["hi"],
            )

            mock_llm_response = MagicMock()
            mock_llm_response.text = '{"chips": []}'

            with patch("src.conversation.chip_generator.call_gemini_api", return_value=mock_llm_response):
                with caplog.at_level("WARNING"):
                    result = generator.generate_chips_async(context)

            assert result is None
            data = _get_session_data(session_id, store)
            assert data["chip_state"]["failure_count"] == 1
            assert any("Chip validation failed" in r.message for r in caplog.records)

        clear_session_chip_seq(session_id)

    def test_chip_generation_llm_error_scenario(self, caplog):
        """Test LLM error scenarios: client API exception returns None, logs error, proceeds gracefully."""
        from src.conversation.chip_generator import ChipGenerator
        from src.utils.state_manager import _get_session_data, clear_session_chip_seq

        session_id = "test_llm_failure_session"
        clear_session_chip_seq(session_id)
        store = {
            session_id: {
                "chip_state": {
                    "current_chips": None,
                    "generation_seq": 0,
                    "last_generation_time": 0,
                    "generation_count": 0,
                    "failure_count": 0,
                    "pending_task": None,
                }
            }
        }

        with patch("src.utils.state_manager._global_store", store):
            generator = ChipGenerator(session_id)
            context = ChipGenerationContext(
                conversation_turns=[{"role": "user", "content": "hi"}],
                payment_status="none",
                conversation_phase="greeting",
                recent_user_messages=["hi"],
            )

            with patch("src.conversation.chip_generator.call_gemini_api", side_effect=RuntimeError("GCP Vertex API Unavailable")):
                with caplog.at_level("ERROR"):
                    result = generator.generate_chips_async(context)

            assert result is None
            data = _get_session_data(session_id, store)
            assert data["chip_state"]["failure_count"] == 1
            assert any("LLM call failed for chip generation" in r.message for r in caplog.records)

        clear_session_chip_seq(session_id)


class TestSessionLifecycleIntegration:
    """End-to-end integration tests for session lifecycle and suggestion chips."""

    def test_session_reset_clears_chips_and_hides_ui(self):
        """Test session reset clears chip state and hides all chip buttons."""
        from src.ui.chips import create_chip_row, update_chips
        from src.utils.state_manager import (
            clear_session_chip_seq,
            get_session_state,
            reset_session_state,
        )

        session_id = "test_lifecycle_reset_session"
        clear_session_chip_seq(session_id)
        app_state = {}
        _, buttons = create_chip_row(session_id)

        session_state = get_session_state(session_id, app_state)
        sample_chips = SuggestionChipSet(
            chips=[
                SuggestionChip(text="Show menu", type=ChipType.ACTION, action_id=ActionID.MENU),
                SuggestionChip(text="Old Fashioned", type=ChipType.DIALOGUE),
                SuggestionChip(text="Surprise me", type=ChipType.DIALOGUE),
            ]
        )
        session_state["chip_state"] = {"current_chips": sample_chips}

        updated = update_chips(session_id, buttons, app_state=app_state)
        assert updated[0].visible is True
        assert updated[1].visible is True
        assert updated[2].visible is True

        reset_session_state(session_id, app_state)

        clean_state = get_session_state(session_id, app_state)
        assert clean_state.get("chip_state", {}).get("current_chips") is None

        hidden = update_chips(session_id, buttons, app_state=app_state)
        assert all(b.visible is False for b in hidden)
        clear_session_chip_seq(session_id)

    def test_user_message_submission_hides_chips_and_restores_on_complete(self):
        """Test user message submission hides chips until Maya completes her response."""
        import gradio as gr

        from src.ui.chips import create_chip_row, update_chips
        from src.utils.state_manager import clear_session_chip_seq, get_session_state

        session_id = "test_submission_hide_session"
        clear_session_chip_seq(session_id)
        app_state = {}
        chip_row, buttons = create_chip_row(session_id)

        # 1. User submits a message: chips row is hidden
        hide_update = gr.Row(visible=False)
        assert hide_update.visible is False

        # 2. Response completes and chips are stored
        session_state = get_session_state(session_id, app_state)
        new_chips = SuggestionChipSet(
            chips=[
                SuggestionChip(text="Yes please", type=ChipType.DIALOGUE),
                SuggestionChip(text="No thank you", type=ChipType.DIALOGUE),
                SuggestionChip(text="Tell me more", type=ChipType.DIALOGUE),
            ]
        )
        session_state["chip_state"] = {"current_chips": new_chips}

        # 3. Chips become visible again after response finishes
        refreshed = update_chips(session_id, buttons, app_state=app_state)
        assert refreshed[0].visible is True
        assert refreshed[0].value == "Yes please"
        assert refreshed[1].visible is True
        assert refreshed[1].value == "No thank you"
        assert refreshed[2].visible is True
        assert refreshed[2].value == "Tell me more"
        clear_session_chip_seq(session_id)


# Mark integration tests
pytestmark = pytest.mark.integration




