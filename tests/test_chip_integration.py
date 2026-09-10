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







# Mark integration tests
pytestmark = pytest.mark.integration




