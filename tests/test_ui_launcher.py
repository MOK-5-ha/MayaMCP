"""Unit tests for UI launcher."""

from unittest.mock import Mock, patch, MagicMock, call
import gradio as gr
from src.ui.launcher import launch_bartender_interface
import pytest


@pytest.fixture
def ui_mocks():
    """Fixture providing preconfigured Gradio component mocks for UI tests."""
    theme_instance = Mock()
    blocks_instance = Mock()
    markdown_instance = Mock()
    state_instance = Mock()
    row_instance = Mock()
    column_instance = Mock()
    chatbot_instance = Mock()
    audio_instance = Mock()
    textbox_instance = Mock()
    submit_button_instance = Mock()
    clear_button_instance = Mock()
    start_chatting_button_instance = Mock()
    accordion_instance = Mock()

    blocks_context = Mock()
    blocks_context.__enter__ = Mock(return_value=blocks_instance)
    blocks_context.__exit__ = Mock(return_value=None)

    row_context = Mock()
    row_context.__enter__ = Mock(return_value=row_instance)
    row_context.__exit__ = Mock(return_value=None)

    column_context = Mock()
    column_context.__enter__ = Mock(return_value=column_instance)
    column_context.__exit__ = Mock(return_value=None)

    accordion_context = Mock()
    accordion_context.__enter__ = Mock(return_value=accordion_instance)
    accordion_context.__exit__ = Mock(return_value=None)

    return {
        'theme_instance': theme_instance,
        'blocks_instance': blocks_instance,
        'blocks_context': blocks_context,
        'markdown_instance': markdown_instance,
        'state_instance': state_instance,
        'row_instance': row_instance,
        'row_context': row_context,
        'column_instance': column_instance,
        'column_context': column_context,
        'chatbot_instance': chatbot_instance,
        'audio_instance': audio_instance,
        'textbox_instance': textbox_instance,
        'submit_button_instance': submit_button_instance,
        'clear_button_instance': clear_button_instance,
        'start_chatting_button_instance': start_chatting_button_instance,
        'accordion_instance': accordion_instance,
        'accordion_context': accordion_context,
    }


def _setup_launcher_mocks(
    ui_mocks, mock_blocks, mock_ocean_theme, mock_markdown, mock_state,
    mock_row, mock_column, mock_html, mock_chatbot, mock_audio, mock_textbox,
    mock_button, mock_create_overlay, mock_accordion=None
):
    """Common helper to wire up all Gradio mocks for launcher tests."""
    mock_create_overlay.return_value = '<div>overlay</div>'
    mock_ocean_theme.return_value = ui_mocks['theme_instance']
    mock_blocks.return_value = ui_mocks['blocks_context']
    mock_markdown.return_value = ui_mocks['markdown_instance']
    mock_state.return_value = ui_mocks['state_instance']
    mock_row.return_value = ui_mocks['row_context']
    mock_column.return_value = ui_mocks['column_context']
    mock_html.return_value = Mock()
    mock_chatbot.return_value = ui_mocks['chatbot_instance']
    mock_audio.return_value = ui_mocks['audio_instance']
    mock_textbox.return_value = ui_mocks['textbox_instance']
    # 3 buttons now: "Start Chatting", "Clear Conversation", "Send"
    mock_button.side_effect = [
        ui_mocks['start_chatting_button_instance'],
        ui_mocks['clear_button_instance'],
        ui_mocks['submit_button_instance'],
    ]
    if mock_accordion is not None:
        mock_accordion.return_value = ui_mocks['accordion_context']



class TestLaunchBartenderInterface:
    """Test cases for launch_bartender_interface function."""

    @patch('src.ui.launcher.gr.Accordion')
    @patch('src.ui.launcher.create_tab_overlay_html')
    @patch('src.ui.launcher.setup_avatar')
    @patch('src.ui.launcher.gr.themes.Ocean')
    @patch('src.ui.launcher.gr.Blocks')
    @patch('src.ui.launcher.gr.Markdown')
    @patch('src.ui.launcher.gr.State')
    @patch('src.ui.launcher.gr.Row')
    @patch('src.ui.launcher.gr.Column')
    @patch('src.ui.launcher.gr.HTML')
    @patch('src.ui.launcher.gr.Chatbot')
    @patch('src.ui.launcher.gr.Audio')
    @patch('src.ui.launcher.gr.Textbox')
    @patch('src.ui.launcher.gr.Button')
    def test_launch_bartender_interface_with_default_avatar(
        self, mock_button, mock_textbox, mock_audio, mock_chatbot, mock_html,
        mock_column, mock_row, mock_state, mock_markdown, mock_blocks,
        mock_ocean_theme, mock_setup_avatar, mock_create_overlay,
        mock_accordion, ui_mocks
    ):
        """Test interface creation with default avatar setup."""
        mock_setup_avatar.return_value = "assets/bartender_avatar.jpg"
        _setup_launcher_mocks(
            ui_mocks, mock_blocks, mock_ocean_theme, mock_markdown, mock_state,
            mock_row, mock_column, mock_html, mock_chatbot, mock_audio,
            mock_textbox, mock_button, mock_create_overlay, mock_accordion
        )

        result = launch_bartender_interface(
            handle_input_fn=Mock(),
            clear_state_fn=Mock(),
            avatar_path=None,
        )

        mock_setup_avatar.assert_called_once_with()
        mock_ocean_theme.assert_called_once()
        mock_blocks.assert_called_once_with(theme=ui_mocks['theme_instance'])
        assert result == ui_mocks['blocks_instance']

    @patch('src.ui.launcher.gr.Accordion')
    @patch('src.ui.launcher.create_tab_overlay_html')
    @patch('src.ui.launcher.setup_avatar')
    @patch('src.ui.launcher.gr.themes.Ocean')
    @patch('src.ui.launcher.gr.Blocks')
    @patch('src.ui.launcher.gr.Markdown')
    @patch('src.ui.launcher.gr.State')
    @patch('src.ui.launcher.gr.Row')
    @patch('src.ui.launcher.gr.Column')
    @patch('src.ui.launcher.gr.HTML')
    @patch('src.ui.launcher.gr.Chatbot')
    @patch('src.ui.launcher.gr.Audio')
    @patch('src.ui.launcher.gr.Textbox')
    @patch('src.ui.launcher.gr.Button')
    def test_launch_bartender_interface_with_custom_avatar(
        self, mock_button, mock_textbox, mock_audio, mock_chatbot, mock_html,
        mock_column, mock_row, mock_state, mock_markdown, mock_blocks,
        mock_ocean_theme, mock_setup_avatar, mock_create_overlay,
        mock_accordion, ui_mocks
    ):
        """Test interface creation with custom avatar path."""
        _setup_launcher_mocks(
            ui_mocks, mock_blocks, mock_ocean_theme, mock_markdown, mock_state,
            mock_row, mock_column, mock_html, mock_chatbot, mock_audio,
            mock_textbox, mock_button, mock_create_overlay, mock_accordion
        )

        result = launch_bartender_interface(
            handle_input_fn=Mock(),
            clear_state_fn=Mock(),
            avatar_path="custom/avatar/path.jpg",
        )

        mock_setup_avatar.assert_not_called()
        mock_create_overlay.assert_called()
        assert result == ui_mocks['blocks_instance']

    @patch('src.ui.launcher.gr.Accordion')
    @patch('src.ui.launcher.create_tab_overlay_html')
    @patch('src.ui.launcher.setup_avatar')
    @patch('src.ui.launcher.gr.themes.Ocean')
    @patch('src.ui.launcher.gr.Blocks')
    @patch('src.ui.launcher.gr.Markdown')
    @patch('src.ui.launcher.gr.State')
    @patch('src.ui.launcher.gr.Row')
    @patch('src.ui.launcher.gr.Column')
    @patch('src.ui.launcher.gr.HTML')
    @patch('src.ui.launcher.gr.Chatbot')
    @patch('src.ui.launcher.gr.Audio')
    @patch('src.ui.launcher.gr.Textbox')
    @patch('src.ui.launcher.gr.Button')
    def test_launch_bartender_interface_component_properties(
        self, mock_button, mock_textbox, mock_audio, mock_chatbot, mock_html,
        mock_column, mock_row, mock_state, mock_markdown, mock_blocks,
        mock_ocean_theme, mock_setup_avatar, mock_create_overlay,
        mock_accordion, ui_mocks
    ):
        """Test that core UI components are created with correct properties."""
        mock_setup_avatar.return_value = "assets/bartender_avatar.jpg"
        _setup_launcher_mocks(
            ui_mocks, mock_blocks, mock_ocean_theme, mock_markdown, mock_state,
            mock_row, mock_column, mock_html, mock_chatbot, mock_audio,
            mock_textbox, mock_button, mock_create_overlay, mock_accordion
        )

        launch_bartender_interface(
            handle_input_fn=Mock(),
            clear_state_fn=Mock(),
            avatar_path=None,
        )

        # Chatbot properties
        mock_chatbot.assert_called_once_with(
            [],
            elem_id="chatbot",
            label="Conversation",
            height=489,
            type="messages"
        )

        # Audio properties
        mock_audio.assert_called_once_with(
            label="Agent Voice",
            autoplay=True,
            streaming=False,
            format="wav",
            show_label=True,
            interactive=False
        )

        # At least 3 buttons: Start Chatting, Clear, Send
        assert mock_button.call_count >= 3

    @patch('src.ui.launcher.gr.Accordion')
    @patch('src.ui.launcher.create_tab_overlay_html')
    @patch('src.ui.launcher.setup_avatar')
    @patch('src.ui.launcher.gr.themes.Ocean')
    @patch('src.ui.launcher.gr.Blocks')
    @patch('src.ui.launcher.gr.Markdown')
    @patch('src.ui.launcher.gr.State')
    @patch('src.ui.launcher.gr.Row')
    @patch('src.ui.launcher.gr.Column')
    @patch('src.ui.launcher.gr.HTML')
    @patch('src.ui.launcher.gr.Chatbot')
    @patch('src.ui.launcher.gr.Audio')
    @patch('src.ui.launcher.gr.Textbox')
    @patch('src.ui.launcher.gr.Button')
    def test_launch_bartender_interface_event_handlers(
        self, mock_button, mock_textbox, mock_audio, mock_chatbot, mock_html,
        mock_column, mock_row, mock_state, mock_markdown, mock_blocks,
        mock_ocean_theme, mock_setup_avatar, mock_create_overlay,
        mock_accordion, ui_mocks
    ):
        """Test that event handlers are properly configured."""
        mock_setup_avatar.return_value = "assets/bartender_avatar.jpg"
        _setup_launcher_mocks(
            ui_mocks, mock_blocks, mock_ocean_theme, mock_markdown, mock_state,
            mock_row, mock_column, mock_html, mock_chatbot, mock_audio,
            mock_textbox, mock_button, mock_create_overlay, mock_accordion
        )

        mock_handle_input = Mock()
        mock_clear_state = Mock()

        launch_bartender_interface(
            handle_input_fn=mock_handle_input,
            clear_state_fn=mock_clear_state,
            avatar_path=None,
        )

        # Chat input submit handler configured
        ui_mocks['textbox_instance'].submit.assert_called()
        submit_call = ui_mocks['textbox_instance'].submit.call_args
        assert submit_call[0][0] == mock_handle_input

        # Send button click handler configured
        ui_mocks['submit_button_instance'].click.assert_called_once()
        assert ui_mocks['submit_button_instance'].click.call_args[0][0] == mock_handle_input

        # Clear button click handler configured
        ui_mocks['clear_button_instance'].click.assert_called_once()

        # Start Chatting button (BYOK key submission) click handler configured
        ui_mocks['start_chatting_button_instance'].click.assert_called_once()

    @patch('src.ui.launcher.gr.Accordion')
    @patch('src.ui.launcher.create_tab_overlay_html')
    @patch('src.ui.launcher.setup_avatar')
    @patch('src.ui.launcher.gr.themes.Ocean')
    @patch('src.ui.launcher.gr.Blocks')
    @patch('src.ui.launcher.gr.Markdown')
    @patch('src.ui.launcher.gr.State')
    @patch('src.ui.launcher.gr.Row')
    @patch('src.ui.launcher.gr.Column')
    @patch('src.ui.launcher.gr.HTML')
    @patch('src.ui.launcher.gr.Chatbot')
    @patch('src.ui.launcher.gr.Audio')
    @patch('src.ui.launcher.gr.Textbox')
    @patch('src.ui.launcher.gr.Button')
    @patch('src.ui.launcher.logger')
    def test_launch_bartender_interface_setup_avatar_exception(
        self, mock_logger, mock_button, mock_textbox, mock_audio, mock_chatbot,
        mock_html, mock_column, mock_row, mock_state, mock_markdown,
        mock_blocks, mock_ocean_theme, mock_setup_avatar, mock_create_overlay,
        mock_accordion, ui_mocks
    ):
        """Test interface creation when setup_avatar raises exception."""
        mock_setup_avatar.side_effect = Exception("Avatar setup failed")
        _setup_launcher_mocks(
            ui_mocks, mock_blocks, mock_ocean_theme, mock_markdown, mock_state,
            mock_row, mock_column, mock_html, mock_chatbot, mock_audio,
            mock_textbox, mock_button, mock_create_overlay, mock_accordion
        )

        result = launch_bartender_interface(
            handle_input_fn=Mock(),
            clear_state_fn=Mock(),
            avatar_path=None,
        )

        mock_setup_avatar.assert_called_once()
        mock_logger.exception.assert_called_once()
        assert "Failed to setup avatar" in mock_logger.exception.call_args[0][0]
        assert result == ui_mocks['blocks_instance']
