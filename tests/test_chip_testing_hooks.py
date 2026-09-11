"""
Tests for Suggestion Chips Testing and Validation Hooks.

Validates:
- Requirements 12.1, 12.2, 12.3, 12.4, 12.5
- Properties 44, 45
"""

import logging
from unittest.mock import MagicMock, patch

import gradio as gr
import pytest

from src.conversation.chip_generator import (
    ChipGenerator,
    create_mock_chip_context,
)
from src.schemas.chips import (
    ActionID,
    ChipGenerationContext,
    ChipType,
    SuggestionChip,
    SuggestionChipSet,
)
from src.ui.chips import inject_chips_programmatically, update_chips
from src.utils.state_manager import get_session_state, initialize_state


class TestTestModeDeterminism:
    """Tests for ChipGenerator test_mode flag and deterministic generation (Requirement 12.3, Property 45)."""

    def test_test_mode_flag_initialization(self):
        """ChipGenerator should accept test_mode boolean in __init__ defaulting to False."""
        gen_default = ChipGenerator(session_id="default-session")
        assert gen_default.test_mode is False

        gen_test = ChipGenerator(session_id="test-session", test_mode=True)
        assert gen_test.test_mode is True

    @patch("src.conversation.chip_generator.call_gemini_api")
    def test_test_mode_bypasses_llm_call(self, mock_gemini):
        """In test_mode, generate_chips_async and _generate_chips_sync must never call the LLM API."""
        generator = ChipGenerator(session_id="test-bypass-session", test_mode=True)
        context = create_mock_chip_context(phase="greeting")

        result = generator.generate_chips_async(context)
        assert result is not None
        assert isinstance(result, SuggestionChipSet)
        assert len(result.chips) >= 3
        mock_gemini.assert_not_called()

    def test_test_mode_reproducible_and_deterministic(self):
        """Identical contexts in test_mode must produce identical SuggestionChipSet outputs."""
        generator = ChipGenerator(session_id="det-session", test_mode=True)
        ctx1 = create_mock_chip_context(phase="ordering", payment_status="pending")
        ctx2 = create_mock_chip_context(phase="ordering", payment_status="pending")

        res1 = generator._generate_chips_sync(ctx1)
        res2 = generator._generate_chips_sync(ctx2)

        assert res1 is not None and res2 is not None
        assert res1.model_dump() == res2.model_dump()

    def test_test_mode_phase_specific_chips(self):
        """test_mode must generate appropriate chips tailored to each conversation phase."""
        generator = ChipGenerator(session_id="phase-test-session", test_mode=True)

        # Greeting phase
        greeting_ctx = create_mock_chip_context(phase="greeting")
        greeting_res = generator._generate_chips_sync(greeting_ctx)
        assert greeting_res is not None
        assert any("menu" in chip.text.lower() or chip.action_id == ActionID.MENU for chip in greeting_res.chips)

        # Ordering phase
        ordering_ctx = create_mock_chip_context(phase="ordering")
        ordering_res = generator._generate_chips_sync(ordering_ctx)
        assert ordering_res is not None
        assert any(chip.action_id == ActionID.ORDER_ANOTHER for chip in ordering_res.chips)

        # Describing phase
        describing_ctx = create_mock_chip_context(phase="describing")
        describing_res = generator._generate_chips_sync(describing_ctx)
        assert describing_res is not None
        dialogue_count = sum(1 for c in describing_res.chips if c.type == ChipType.DIALOGUE)
        assert dialogue_count >= 2

        # Payment phase with pending status
        payment_ctx = create_mock_chip_context(phase="payment", payment_status="pending")
        payment_res = generator._generate_chips_sync(payment_ctx)
        assert payment_res is not None
        assert payment_res.chips[0].type == ChipType.ACTION
        assert payment_res.chips[0].action_id == ActionID.PAYMENT


class TestDependencyInjection:
    """Tests for LLM client dependency injection (Requirement 12.2, Property 44)."""

    def test_dependency_injection_custom_client(self):
        """ChipGenerator must use injected client instead of default client."""
        mock_client = MagicMock()
        generator = ChipGenerator(session_id="di-session", llm_client=mock_client)
        assert generator.llm_client is mock_client

    @patch("src.conversation.chip_generator.get_genai_client")
    def test_default_client_uses_get_genai_client(self, mock_get_client):
        """When llm_client is None, ChipGenerator must retrieve the global client via get_genai_client()."""
        sentinel_client = MagicMock()
        mock_get_client.return_value = sentinel_client

        generator = ChipGenerator(session_id="default-client-session")
        assert generator.llm_client is sentinel_client
        mock_get_client.assert_called_once()


class TestMockContextFactory:
    """Tests for mock conversation context factory (Requirement 12.1, 12.5)."""

    def test_create_mock_chip_context_defaults(self):
        """Factory must return a valid ChipGenerationContext with defaults."""
        ctx = create_mock_chip_context()
        assert isinstance(ctx, ChipGenerationContext)
        assert ctx.conversation_phase == "greeting"
        assert ctx.payment_status is None
        assert len(ctx.conversation_turns) <= 4
        assert len(ctx.recent_user_messages) <= 2

    def test_create_mock_chip_context_custom_values(self):
        """Factory must correctly accept custom turns, phase, payment_status, and messages."""
        turns = [
            {"role": "user", "content": "I'd like an Old Fashioned"},
            {"role": "assistant", "content": "Excellent choice! Crafted with bourbon and bitters."},
        ]
        recent = ["I'd like an Old Fashioned"]
        ctx = create_mock_chip_context(
            phase="ordering",
            payment_status="pending",
            turns=turns,
            recent_user_messages=recent,
        )
        assert ctx.conversation_phase == "ordering"
        assert ctx.payment_status == "pending"
        assert ctx.conversation_turns == turns
        assert ctx.recent_user_messages == recent


class TestProgrammaticChipInjection:
    """Tests for UI programmatic chip injection (Requirement 12.5)."""

    def test_inject_chips_programmatically_updates_session_and_ui(self):
        """inject_chips_programmatically must store chips in session state and return updated button configs."""
        session_id = "test-inject-session"
        app_state = {}
        initialize_state(session_id, app_state)

        chip_set = SuggestionChipSet(
            chips=[
                SuggestionChip(text="Injected Dialogue", type=ChipType.DIALOGUE, action_id=None),
                SuggestionChip(text="Injected Action", type=ChipType.ACTION, action_id=ActionID.PAYMENT),
                SuggestionChip(text="Another Option", type=ChipType.DIALOGUE, action_id=None),
            ]
        )

        buttons = [gr.Button(value="", visible=False) for _ in range(6)]
        updated_buttons = inject_chips_programmatically(
            session_id=session_id,
            chip_set=chip_set,
            chip_buttons=buttons,
            app_state=app_state,
        )

        # Session state verified
        state = get_session_state(session_id, app_state)
        stored_chips = state.get("chip_state", {}).get("current_chips")
        assert stored_chips is not None
        assert len(stored_chips.chips) == 3

        # UI buttons verified
        assert len(updated_buttons) == 6
        assert updated_buttons[0].visible is True
        assert "Injected Dialogue" in updated_buttons[0].value
        assert updated_buttons[1].visible is True
        assert "Injected Action" in updated_buttons[1].value
        assert updated_buttons[3].visible is False


class TestDebugLogging:
    """Tests for chip generation debug logging (Requirement 12.4)."""

    def test_debug_logging_emits_context_and_results(self, caplog):
        """Chip generation must emit debug-level logs containing context details and results."""
        generator = ChipGenerator(session_id="debug-log-session", test_mode=True)
        context = create_mock_chip_context(phase="greeting")

        with caplog.at_level(logging.DEBUG):
            result = generator._generate_chips_sync(context)

        assert result is not None
        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_records) > 0

        debug_messages = " ".join(r.message for r in debug_records)
        assert "context" in debug_messages.lower() or "greeting" in debug_messages.lower()
