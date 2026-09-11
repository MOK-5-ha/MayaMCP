"""Unit tests for chip state management in session store.

Validates: Requirements 6.3, 7.6, 8.6
Tasks: 11.1, 11.2, 11.3
"""

import threading
import time
from concurrent.futures import Future

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
        """Verify concurrent updates across threads do not corrupt chip state."""
        initialize_state(session_id, session_store)
        num_threads = 10
        updates_per_thread = 20

        def worker(worker_idx: int):
            for i in range(updates_per_thread):
                update_chip_state(
                    session_id,
                    session_store,
                    {
                        "last_generation_time": time.time(),
                    },
                )
                # Read and update counts
                current = get_chip_state(session_id, session_store)
                gen_count = current.get("generation_count", 0)
                update_chip_state(
                    session_id,
                    session_store,
                    {"generation_count": gen_count + 1},
                )
                time.sleep(0.001)

        threads = [
            threading.Thread(target=worker, args=(i,)) for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        final_state = get_chip_state(session_id, session_store)
        assert final_state["generation_count"] > 0
        assert final_state["last_generation_time"] is not None
