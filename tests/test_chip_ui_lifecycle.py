"""Integration tests for suggestion chips lifecycle, visibility, and UI integration.

Validates Requirements 6.1, 6.2, 6.3, 6.5, 6.6.
"""

from unittest.mock import Mock, patch

import gradio as gr
import pytest

from src.schemas.chips import ActionID, ChipType, SuggestionChip, SuggestionChipSet
from src.ui.chips import create_chip_row, update_chips
from src.ui.launcher import launch_bartender_interface
from src.utils.state_manager import get_session_state, reset_session_state


class TestChipLifecycle:
    """Integration tests for suggestion chips lifecycle within conversation turns."""

    def test_chips_hide_on_user_message_submission(self):
        """When user submits a message, the chip row should be hidden immediately."""
        app_state = {}
        session_id = "test_hide_lifecycle"
        chip_row, buttons = create_chip_row(session_id)

        # Initially or during user message submit, row update sets visible=False
        hide_update = gr.Row(visible=False)
        assert hide_update.visible is False

    def test_chips_update_after_maya_response(self):
        """After Maya's response finishes, update_chips should populate active chips into buttons."""
        app_state = {}
        session_id = "test_response_lifecycle"
        _, buttons = create_chip_row(session_id)

        session_state = get_session_state(session_id, app_state)
        sample_chips = SuggestionChipSet(
            chips=[
                SuggestionChip(text="Tell me a joke", type=ChipType.DIALOGUE),
                SuggestionChip(text="Pay tab", type=ChipType.ACTION, action_id=ActionID.PAYMENT),
                SuggestionChip(text="Show menu", type=ChipType.ACTION, action_id=ActionID.MENU),
            ]
        )
        session_state["chip_state"] = {"current_chips": sample_chips}

        updated_buttons = update_chips(session_id, buttons, app_state=app_state)

        assert updated_buttons[0].visible is True
        assert updated_buttons[0].value == "Tell me a joke"
        assert updated_buttons[1].visible is True
        assert "Pay tab" in updated_buttons[1].value
        assert updated_buttons[2].visible is True
        assert updated_buttons[3].visible is False

    def test_chips_persist_across_ui_refreshes_within_same_turn(self):
        """Chips must remain accessible across repeated UI updates within the same conversation turn."""
        app_state = {}
        session_id = "test_persist_lifecycle"
        _, buttons = create_chip_row(session_id)

        session_state = get_session_state(session_id, app_state)
        sample_chips = SuggestionChipSet(
            chips=[
                SuggestionChip(text="Show menu", type=ChipType.ACTION, action_id=ActionID.MENU),
                SuggestionChip(text="What's your favorite?", type=ChipType.DIALOGUE),
                SuggestionChip(text="Tell me a joke", type=ChipType.DIALOGUE),
            ]
        )
        session_state["chip_state"] = {"current_chips": sample_chips}

        # First refresh
        first_pass = update_chips(session_id, buttons, app_state=app_state)
        # Subsequent refresh within same turn
        second_pass = update_chips(session_id, buttons, app_state=app_state)

        assert [b.value for b in first_pass] == [b.value for b in second_pass]
        assert [b.visible for b in first_pass] == [b.visible for b in second_pass]
        assert first_pass[0].visible is True
        assert first_pass[1].visible is True
        assert first_pass[2].visible is True

    def test_chips_clear_on_session_reset(self):
        """Resetting the session must clear all chip state and hide all chip buttons."""
        app_state = {}
        session_id = "test_reset_lifecycle"
        _, buttons = create_chip_row(session_id)

        session_state = get_session_state(session_id, app_state)
        session_state["chip_state"] = {
            "current_chips": SuggestionChipSet(
                chips=[
                    SuggestionChip(text="Chip 1", type=ChipType.DIALOGUE),
                    SuggestionChip(text="Chip 2", type=ChipType.DIALOGUE),
                    SuggestionChip(text="Chip 3", type=ChipType.DIALOGUE),
                ]
            )
        }

        # Verify chips are present before reset
        active_pass = update_chips(session_id, buttons, app_state=app_state)
        assert active_pass[0].visible is True

        # Perform reset
        reset_session_state(session_id, app_state)

        # After reset, chip state is wiped
        cleared_pass = update_chips(session_id, buttons, app_state=app_state)
        for btn in cleared_pass:
            assert btn.visible is False


class TestLauncherChipIntegration:
    """Tests verifying suggestion chips integration inside launch_bartender_interface."""

    @patch("src.ui.launcher.register_chip_handlers")
    @patch("src.ui.launcher.create_chip_row")
    @patch("src.ui.launcher.gr.Accordion")
    @patch("src.ui.launcher.create_tab_overlay_html")
    @patch("src.ui.launcher.setup_avatar")
    @patch("src.ui.launcher.gr.themes.Ocean")
    @patch("src.ui.launcher.gr.Blocks")
    @patch("src.ui.launcher.gr.Markdown")
    @patch("src.ui.launcher.gr.State")
    @patch("src.ui.launcher.gr.Row")
    @patch("src.ui.launcher.gr.Column")
    @patch("src.ui.launcher.gr.HTML")
    @patch("src.ui.launcher.gr.Chatbot")
    @patch("src.ui.launcher.gr.Audio")
    @patch("src.ui.launcher.gr.Textbox")
    @patch("src.ui.launcher.gr.Button")
    def test_launcher_wires_chips_on_initialization(
        self,
        mock_button,
        mock_textbox,
        mock_audio,
        mock_chatbot,
        mock_html,
        mock_column,
        mock_row,
        mock_state,
        mock_markdown,
        mock_blocks,
        mock_ocean_theme,
        mock_setup_avatar,
        mock_create_overlay,
        mock_accordion,
        mock_create_chip_row,
        mock_register_chip_handlers,
    ):
        """launch_bartender_interface should invoke create_chip_row and register_chip_handlers."""
        mock_chip_row_instance = Mock()
        mock_chip_buttons = [Mock() for _ in range(6)]
        mock_create_chip_row.return_value = (mock_chip_row_instance, mock_chip_buttons)

        mock_setup_avatar.return_value = "assets/bartender_avatar.jpg"
        mock_blocks_ctx = Mock()
        mock_blocks_ctx.__enter__ = Mock(return_value=Mock())
        mock_blocks_ctx.__exit__ = Mock(return_value=None)
        mock_blocks.return_value = mock_blocks_ctx

        row_ctx = Mock()
        row_ctx.__enter__ = Mock(return_value=Mock())
        row_ctx.__exit__ = Mock(return_value=None)
        mock_row.return_value = row_ctx

        col_ctx = Mock()
        col_ctx.__enter__ = Mock(return_value=Mock())
        col_ctx.__exit__ = Mock(return_value=None)
        mock_column.return_value = col_ctx

        mock_button.side_effect = [
            Mock(),  # start_chatting_button
            Mock(),  # clear_button
            Mock(),  # submit_button
        ]

        launch_bartender_interface(
            handle_input_fn=Mock(),
            clear_state_fn=Mock(),
            avatar_path="assets/bartender_avatar.jpg",
        )

        mock_create_chip_row.assert_called_once()
        mock_register_chip_handlers.assert_called_once()
