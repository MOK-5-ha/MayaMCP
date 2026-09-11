"""Unit tests for suggestion chips update and click handlers.

Validates Requirements 5.1, 5.2, 5.3, 5.4, 9.1, 11.5, 11.6.
"""

from unittest.mock import MagicMock, Mock, patch

import gradio as gr
import pytest

from src.schemas.chips import ActionID, ChipType, SuggestionChip, SuggestionChipSet
from src.ui.chips import (
    ACTION_ICONS,
    create_chip_row,
    get_chip_aria_label,
    handle_chip_click,
    register_chip_handlers,
    update_chips,
)
from src.utils.state_manager import get_session_state


class TestChipClickHandlers:
    """Tests for handle_chip_click interaction and routing logic."""

    def test_dialogue_chip_click_populates_textbox_without_submit(self):
        """Dialogue chips should populate the textbox with clean text and return None for submit."""
        clean_text, submit_trigger = handle_chip_click(
            chip_text="Tell me more",
            chip_type="dialogue",
            action_id=None,
            session_id="test_session",
            textbox=Mock(),
        )
        assert clean_text == "Tell me more"
        assert submit_trigger is None

    def test_action_chip_click_populates_and_auto_submits(self):
        """Valid action chips should populate the textbox and trigger auto-submit."""
        clean_text, submit_trigger = handle_chip_click(
            chip_text="Complete payment",
            chip_type="action",
            action_id="payment",
            session_id="test_session",
            textbox=Mock(),
        )
        assert clean_text == "Complete payment"
        assert submit_trigger == "submit"

    def test_action_chip_with_enum_types(self):
        """Handler should accept ChipType and ActionID enum instances seamlessly."""
        clean_text, submit_trigger = handle_chip_click(
            chip_text="Order another drink",
            chip_type=ChipType.ACTION,
            action_id=ActionID.ORDER_ANOTHER,
            session_id="test_session",
            textbox=Mock(),
        )
        assert clean_text == "Order another drink"
        assert submit_trigger == "submit"

    def test_unrecognized_action_id_falls_back_to_dialogue_behavior(self, caplog):
        """Unrecognized action_id must log a warning and fall back to dialogue behavior without auto-submit."""
        with caplog.at_level("WARNING"):
            clean_text, submit_trigger = handle_chip_click(
                chip_text="Mystery button",
                chip_type="action",
                action_id="unrecognized_action_id",
                session_id="test_session",
                textbox=Mock(),
            )
        assert clean_text == "Mystery button"
        assert submit_trigger is None
        assert any("Unrecognized action_id" in record.message for record in caplog.records)

    def test_icon_prefix_stripped_on_click(self):
        """Any matching action icon prefix should be stripped from the populated textbox text."""
        for action_id, icon in ACTION_ICONS.items():
            raw_text = f"{icon}Perform action"
            clean_text, _ = handle_chip_click(
                chip_text=raw_text,
                chip_type="action",
                action_id=action_id,
                session_id="test_session",
            )
            assert clean_text == "Perform action"
            assert not clean_text.startswith(icon)

    def test_none_or_empty_text_handled_safely(self):
        """None or empty text strings should not crash the click handler."""
        clean_text, submit_trigger = handle_chip_click(
            chip_text="",
            chip_type="dialogue",
            action_id=None,
            session_id="test_session",
        )
        assert clean_text == ""
        assert submit_trigger is None


class TestChipAriaLabelGeneration:
    """Tests for ARIA label generation on suggestion chips."""

    def test_dialogue_chip_aria_label(self):
        """Dialogue chips should produce 'dialogue chip: <text>' ARIA labels."""
        chip = SuggestionChip(text="Tell me more", type=ChipType.DIALOGUE)
        aria_label = get_chip_aria_label(chip)
        assert aria_label == "dialogue chip: Tell me more"

    def test_action_chip_aria_label(self):
        """Action chips should produce 'action chip: <text>' ARIA labels."""
        chip = SuggestionChip(
            text="Complete payment",
            type=ChipType.ACTION,
            action_id=ActionID.PAYMENT,
        )
        aria_label = get_chip_aria_label(chip)
        assert aria_label == "action chip: Complete payment"


class TestUpdateChips:
    """Tests for update_chips UI component synchronization."""

    def test_update_chips_with_empty_or_none_state(self):
        """When no chips are stored in session state, all buttons should be hidden."""
        app_state = {}
        session_id = "test_empty_session"
        _, buttons = create_chip_row(session_id)

        updates = update_chips(session_id, buttons, app_state=app_state)

        assert len(updates) == 6
        for btn in updates:
            assert btn.visible is False

    def test_update_chips_populates_active_chips_with_icons(self):
        """Active chips should be populated with display text, icon prefixes, variants, and elem_classes."""
        app_state = {}
        session_id = "test_active_session"
        _, buttons = create_chip_row(session_id)

        session_state = get_session_state(session_id, app_state)
        test_chips = SuggestionChipSet(
            chips=[
                SuggestionChip(text="Surprise me", type=ChipType.DIALOGUE),
                SuggestionChip(text="Show me the menu", type=ChipType.ACTION, action_id=ActionID.MENU),
                SuggestionChip(text="What's popular?", type=ChipType.DIALOGUE),
            ]
        )
        session_state["chip_state"] = {"current_chips": test_chips}

        updates = update_chips(session_id, buttons, app_state=app_state)

        assert len(updates) == 6

        # Chip 0: Dialogue
        assert updates[0].visible is True
        assert updates[0].value == "Surprise me"
        assert updates[0].variant == "secondary"
        assert "chip-dialogue" in updates[0].elem_classes
        assert getattr(updates[0], "aria_label", None) == "dialogue chip: Surprise me"

        # Chip 1: Action with icon prefix
        assert updates[1].visible is True
        assert updates[1].value == f"{ACTION_ICONS[ActionID.MENU]}Show me the menu"
        assert updates[1].variant == "primary"
        assert "chip-action" in updates[1].elem_classes
        assert "menu" in updates[1].elem_id
        assert getattr(updates[1], "aria_label", None) == "action chip: Show me the menu"

        # Chip 2: Dialogue
        assert updates[2].visible is True
        assert updates[2].value == "What's popular?"
        assert updates[2].variant == "secondary"
        assert getattr(updates[2], "aria_label", None) == "dialogue chip: What's popular?"

        # Chips 3-5: Inactive (hidden)
        for i in range(3, 6):
            assert updates[i].visible is False


class TestRegisterChipHandlers:
    """Tests for register_chip_handlers wiring."""

    def test_register_chip_handlers_wires_all_six_buttons(self):
        """register_chip_handlers must attach click listeners to all 6 buttons."""
        mock_buttons = [Mock(spec=gr.Button) for _ in range(6)]
        mock_textbox = Mock(spec=gr.Textbox)
        mock_submit_btn = Mock(spec=gr.Button)

        register_chip_handlers(
            chip_buttons=mock_buttons,
            textbox=mock_textbox,
            submit_btn=mock_submit_btn,
            session_id="test_reg_session",
        )

        for btn in mock_buttons:
            btn.click.assert_called_once()
            call_kwargs = btn.click.call_args[1]
            assert callable(call_kwargs.get("fn"))
            assert call_kwargs.get("inputs") == [btn]
            assert call_kwargs.get("outputs") == [mock_textbox, mock_submit_btn]
            # Verify action auto-submission is chained strictly after textbox update via .then()
            ev = btn.click.return_value
            ev.then.assert_called_once()
            then_kwargs = ev.then.call_args[1]
            assert then_kwargs.get("inputs") == [mock_submit_btn]
            assert "sendBtn" in then_kwargs.get("js", "")

    def test_registered_callback_distinguishes_action_and_dialogue(self):
        """Callback attached by register_chip_handlers must resolve action vs dialogue chips properly."""
        mock_buttons = [Mock(spec=gr.Button) for _ in range(6)]
        mock_textbox = Mock(spec=gr.Textbox)
        mock_submit_btn = Mock(spec=gr.Button)

        app_state = {}
        session_id = "test_callback_session"
        session_state = get_session_state(session_id, app_state)
        session_state["chip_state"] = {
            "current_chips": SuggestionChipSet(
                chips=[
                    SuggestionChip(text="Surprise me", type=ChipType.DIALOGUE),
                    SuggestionChip(text="Show menu", type=ChipType.ACTION, action_id=ActionID.MENU),
                    SuggestionChip(text="Pay tab", type=ChipType.ACTION, action_id=ActionID.PAYMENT),
                ]
            )
        }

        register_chip_handlers(
            chip_buttons=mock_buttons,
            textbox=mock_textbox,
            submit_btn=mock_submit_btn,
            session_id=session_id,
            app_state=app_state,
        )

        # Dialogue chip callback (index 0)
        dialogue_fn = mock_buttons[0].click.call_args[1]["fn"]
        text, trigger = dialogue_fn("Surprise me")
        assert text == "Surprise me"
        assert trigger is None

        # Action chip callback (index 1)
        action_fn = mock_buttons[1].click.call_args[1]["fn"]
        text, trigger = action_fn(f"{ACTION_ICONS[ActionID.MENU]}Show menu")
        assert text == "Show menu"
        assert trigger == "submit"
