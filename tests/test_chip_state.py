"""Unit tests for chip state management in session store.

Validates: Requirements 6.3, 7.6, 8.6
Tasks: 11.1, 11.2, 11.3
"""

import threading
import time
from concurrent.futures import Future
from unittest.mock import MagicMock, patch

import pytest

from src.schemas.chips import (
    ActionID,
    ChipState,
    ChipType,
    SuggestionChip,
    SuggestionChipSet,
)
from src.utils.state_manager import (
    DEFAULT_CHIP_STATE,
    cleanup_session_lock,
    clear_chip_state,
    get_chip_state,
    get_current_chips,
    get_session_lock,
    get_session_state,
    initialize_state,
    reset_session_state,
    set_current_chips,
    update_chip_state,
)


@pytest.fixture
def session_id():
    """Unique session ID for test isolation."""
    sid = "test_chip_state_session"
    yield sid
    cleanup_session_lock(sid)


@pytest.fixture
def session_store():
    """In-memory session store dictionary."""
    return {}


@pytest.fixture
def sample_chip_set():
    """Sample valid SuggestionChipSet."""
    return SuggestionChipSet(
        chips=[
            SuggestionChip(text="What's in this?", type=ChipType.DIALOGUE),
            SuggestionChip(text="Make it sweet", type=ChipType.DIALOGUE),
            SuggestionChip(
                text="Pay with crypto",
                type=ChipType.ACTION,
                action_id=ActionID.PAYMENT,
            ),
        ]
    )


class TestChipStateStorageAndRetrieval:
    """Test storage and retrieval of chip state in session store (Task 11.1, 11.3)."""

    def test_default_chip_state_initialized(self, session_id, session_store):
        """Verify default chip state is initialized in session store."""
        initialize_state(session_id, session_store)
        chip_state = get_chip_state(session_id, session_store)

        assert chip_state["current_chips"] is None
        assert chip_state["last_generation_time"] is None
        assert chip_state["generation_count"] == 0
        assert chip_state["failure_count"] == 0
        assert chip_state["pending_task"] is None

    def test_store_and_retrieve_current_chips(
        self, session_id, session_store, sample_chip_set
    ):
        """Verify storing and retrieving SuggestionChipSet in session."""
        initialize_state(session_id, session_store)
        set_current_chips(session_id, session_store, sample_chip_set)

        retrieved = get_current_chips(session_id, session_store)
        assert retrieved is not None
        assert len(retrieved.chips) == 3
        assert retrieved.chips[0].text == "What's in this?"
        assert retrieved.chips[2].action_id == ActionID.PAYMENT

    def test_update_chip_state_fields(self, session_id, session_store):
        """Verify updating individual chip state fields."""
        initialize_state(session_id, session_store)
        now = time.time()
        dummy_future = Future()

        update_chip_state(
            session_id,
            session_store,
            {
                "last_generation_time": now,
                "generation_count": 5,
                "failure_count": 1,
                "pending_task": dummy_future,
            },
        )

        chip_state = get_chip_state(session_id, session_store)
        assert chip_state["last_generation_time"] == now
        assert chip_state["generation_count"] == 5
        assert chip_state["failure_count"] == 1
        assert chip_state["pending_task"] is dummy_future

    def test_clear_chip_state_resets_defaults(
        self, session_id, session_store, sample_chip_set
    ):
        """Verify clear_chip_state resets chip fields back to defaults."""
        initialize_state(session_id, session_store)
        set_current_chips(session_id, session_store, sample_chip_set)
        update_chip_state(
            session_id,
            session_store,
            {"generation_count": 10, "failure_count": 2},
        )

        clear_chip_state(session_id, session_store)
        cleared = get_chip_state(session_id, session_store)

        assert cleared["current_chips"] is None
        assert cleared["generation_count"] == 0
        assert cleared["failure_count"] == 0

    def test_reset_session_state_clears_chip_state(
        self, session_id, session_store, sample_chip_set
    ):
        """Verify full reset_session_state clears chip state (Requirement 6.5)."""
        initialize_state(session_id, session_store)
        set_current_chips(session_id, session_store, sample_chip_set)

        reset_session_state(session_id, session_store)
        state = get_session_state(session_id, session_store)
        chip_state = state.get("chip_state", {})

        assert chip_state.get("current_chips") is None
        assert chip_state.get("failure_count", 0) == 0


class TestChipStateSerialization:
    """Test chip state serialization and deserialization (Task 11.2, 11.3)."""

    def test_chip_state_to_dict_empty(self):
        """Verify to_dict on empty ChipState."""
        state = ChipState()
        serialized = state.to_dict()

        assert serialized["chips"] == []
        assert serialized["last_generation_time"] is None
        assert serialized["generation_count"] == 0
        assert serialized["failure_count"] == 0
        assert "pending_task" not in serialized

    def test_chip_state_to_dict_with_chips(self, sample_chip_set):
        """Verify to_dict serializes SuggestionChipSet to primitive dicts."""
        future = Future()
        state = ChipState(
            current_chips=sample_chip_set,
            last_generation_time=1234567.89,
            generation_count=3,
            failure_count=1,
            pending_task=future,
        )

        serialized = state.to_dict()
        assert len(serialized["chips"]) == 3
        assert serialized["chips"][0]["text"] == "What's in this?"
        assert serialized["chips"][0]["type"] == "dialogue"
        assert serialized["chips"][2]["action_id"] == "payment"
        assert serialized["last_generation_time"] == 1234567.89
        assert serialized["generation_count"] == 3
        assert serialized["failure_count"] == 1
        # unpickleable pending_task must be excluded from persistence dict
        assert "pending_task" not in serialized

    def test_chip_state_from_dict_roundtrip(self, sample_chip_set):
        """Verify from_dict properly reconstructs ChipState and SuggestionChipSet."""
        state = ChipState(
            current_chips=sample_chip_set,
            last_generation_time=9876543.21,
            generation_count=7,
            failure_count=2,
        )
        serialized = state.to_dict()
        reconstructed = ChipState.from_dict(serialized)

        assert reconstructed.current_chips is not None
        assert len(reconstructed.current_chips.chips) == 3
        assert reconstructed.current_chips.chips[2].action_id == ActionID.PAYMENT
        assert reconstructed.last_generation_time == 9876543.21
        assert reconstructed.generation_count == 7
        assert reconstructed.failure_count == 2
        assert reconstructed.pending_task is None

    def test_failure_rate_property(self):
        """Verify failure_rate calculation (Requirement 8.6)."""
        state = ChipState(generation_count=0, failure_count=0)
        assert state.failure_rate == 0.0

        state = ChipState(generation_count=3, failure_count=1)
        assert state.failure_rate == 0.25

        state = ChipState(generation_count=0, failure_count=5)
        assert state.failure_rate == 1.0


class TestThreadSafeConcurrentAccess:
    """Test thread-safe concurrent access to chip state (Task 11.3)."""

    def test_concurrent_chip_state_updates(self, session_id, session_store):
        """Verify concurrent atomic updates across threads do not lose updates."""
        initialize_state(session_id, session_store)
        num_threads = 10
        updates_per_thread = 20
        lock = get_session_lock(session_id)

        def worker(worker_idx: int):
            for _ in range(updates_per_thread):
                with lock:
                    current = get_chip_state(session_id, session_store)
                    gen_count = current.get("generation_count", 0)
                    update_chip_state(
                        session_id,
                        session_store,
                        {
                            "generation_count": gen_count + 1,
                            "last_generation_time": time.time(),
                        },
                    )
                time.sleep(0.0001)

        threads = [
            threading.Thread(target=worker, args=(i,)) for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)
            assert not t.is_alive(), "Worker thread timed out"

        final_state = get_chip_state(session_id, session_store)
        assert final_state["generation_count"] == num_threads * updates_per_thread
        assert final_state["last_generation_time"] is not None

    def test_clear_chip_state_during_active_generation(self, session_id):
        """Verify that in-flight generation completing after clear_chip_state does not repopulate chips."""
        from src.conversation.chip_generator import ChipGenerator
        from src.schemas.chips import ChipGenerationContext

        valid_chip_json = (
            '{"chips": ['
            '{"text": "Late chips 1", "type": "dialogue"}, '
            '{"text": "Late chips 2", "type": "dialogue"}, '
            '{"text": "Late chips 3", "type": "dialogue"}'
            ']}'
        )

        ctx = ChipGenerationContext(
            conversation_turns=[{"role": "user", "content": "Hi"}],
            payment_status="none",
            conversation_phase="greeting",
        )

        # Baseline verification: without clearing, valid 3-chip response succeeds
        baseline_sid = f"{session_id}_baseline"
        initialize_state(baseline_sid)
        try:
            baseline_gen = ChipGenerator(session_id=baseline_sid)
            with patch("src.conversation.chip_generator.call_gemini_api", return_value=MagicMock(text=valid_chip_json)):
                baseline_res = baseline_gen.generate_chips_async(ctx)
                assert baseline_res is not None
                assert len(baseline_res.chips) == 3
        finally:
            cleanup_session_lock(baseline_sid)

        # Now test with in-flight clearing:
        initialize_state(session_id)
        gen = ChipGenerator(session_id=session_id)

        start_event = threading.Event()
        finish_event = threading.Event()

        def slow_generate(prompt_content, config, api_key=None, gcp_project=None, gcp_location=None, client=None):
            start_event.set()
            finish_event.wait(timeout=5.0)
            mock_resp = MagicMock()
            mock_resp.text = valid_chip_json
            return mock_resp

        with patch("src.conversation.chip_generator.call_gemini_api", side_effect=slow_generate):
            result_holder = []
            def run_gen():
                res = gen.generate_chips_async(ctx)
                result_holder.append(res)

            gen_thread = threading.Thread(target=run_gen)
            gen_thread.start()

            # Wait until generation is actively executing
            assert start_event.wait(timeout=2.0)

            # Clear chip state while generation is in flight
            clear_chip_state(session_id)

            # Allow slow generation to complete
            finish_event.set()
            gen_thread.join(timeout=5.0)

            # In-flight generation result must be None (discarded as stale, not due to validation)
            assert len(result_holder) == 1
            assert result_holder[0] is None

            # Current chips in store must remain None
            chips = get_current_chips(session_id)
            assert chips is None
