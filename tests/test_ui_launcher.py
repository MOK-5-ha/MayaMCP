"""Unit tests for UI launcher."""

from unittest.mock import Mock, patch, MagicMock
import gradio as gr
from src.ui.launcher import launch_bartender_interface
import pytest


@pytest.fixture
def ui_mocks():
    """Fixture providing preconfigured Gradio component mocks for UI tests.
    
    Returns:
        dict: Dictionary containing all mocked Gradio components and their instances.
    """
    # Create mock instances
    theme_instance = Mock()
    blocks_instance = Mock()
    markdown_instance = Mock()
    state_instance = Mock()
    row_instance = Mock()
    column_instance = Mock()
    image_instance = Mock()
    chatbot_instance = Mock()
    audio_instance = Mock()
    textbox_instance = Mock()
    submit_button_instance = Mock()
    clear_button_instance = Mock()
    
    # Setup context managers
    blocks_context = Mock()
    blocks_context.__enter__ = Mock(return_value=blocks_instance)
    blocks_context.__exit__ = Mock(return_value=None)
    
    row_context = Mock()
    row_context.__enter__ = Mock(return_value=row_instance)
    row_context.__exit__ = Mock(return_value=None)
    
    column_context = Mock()
    column_context.__enter__ = Mock(return_value=column_instance)
    column_context.__exit__ = Mock(return_value=None)
    
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
        'image_instance': image_instance,
        'chatbot_instance': chatbot_instance,
        'audio_instance': audio_instance,
        'textbox_instance': textbox_instance,
        'submit_button_instance': submit_button_instance,
        'clear_button_instance': clear_button_instance,
    }


class TestLaunchBartenderInterface:
    """Test cases for launch_bartender_interface function."""

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
        mock_column, mock_row, mock_state, mock_markdown, mock_blocks, mock_ocean_theme,
        mock_setup_avatar, mock_create_overlay, ui_mocks
    ):
        """Test interface creation with default avatar setup."""
        # Setup mocks using fixture
        mock_setup_avatar.return_value = "assets/bartender_avatar.jpg"
        mock_create_overlay.return_value = '<div>overlay</div>'
        mock_ocean_theme.return_value = ui_mocks['theme_instance']
        mock_blocks.return_value = ui_mocks['blocks_context']
        mock_markdown.return_value = ui_mocks['markdown_instance']
        mock_state.return_value = ui_mocks['state_instance']
        mock_row.return_value = ui_mocks['row_context']
        mock_column.return_value = ui_mocks['column_context']
        html_instance = Mock()
        mock_html.return_value = html_instance
        mock_chatbot.return_value = ui_mocks['chatbot_instance']
        mock_audio.return_value = ui_mocks['audio_instance']
        mock_textbox.return_value = ui_mocks['textbox_instance']
        mock_button.side_effect = [
            ui_mocks['clear_button_instance'],
            ui_mocks['submit_button_instance']
        ]

        # Execute function
        result = launch_bartender_interface(
            handle_input_fn=Mock(),
            clear_state_fn=Mock(),
            avatar_path=None  # Use default avatar
        )

        # Verify setup_avatar was called with no arguments (default behavior)
        mock_setup_avatar.assert_called_once_with()

        # Verify theme was set up
        mock_ocean_theme.assert_called_once()

        # Verify Blocks context manager was used
        mock_blocks.assert_called_once_with(theme=ui_mocks['theme_instance'])

        # Verify Markdown components were created
        assert mock_markdown.call_count == 2  # Two markdown elements

        # Verify State components were created (now 6: history, order, tab, balance, prev_tab, prev_balance)
        assert mock_state.call_count == 6

        # Verify Row and Column structure was created
        assert mock_row.call_count == 2
        assert mock_column.call_count == 2  # Two columns (avatar and chat)

        # Verify HTML component was created for avatar overlay (instead of Image)
        mock_html.assert_called_once()
        mock_chatbot.assert_called_once()
        mock_audio.assert_called_once()
        mock_textbox.assert_called_once()
        assert mock_button.call_count == 2  # Clear and Submit buttons

        # Verify return value is the blocks instance
        assert result == ui_mocks['blocks_instance']

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
        mock_column, mock_row, mock_state, mock_markdown, mock_blocks, mock_ocean_theme,
        mock_setup_avatar, mock_create_overlay, ui_mocks
    ):
        """Test interface creation with custom avatar path."""
        # Setup mocks using fixture
        custom_avatar_path = "custom/avatar/path.jpg"
        mock_create_overlay.return_value = '<div>overlay</div>'
        mock_ocean_theme.return_value = ui_mocks['theme_instance']
        mock_blocks.return_value = ui_mocks['blocks_context']
        mock_markdown.return_value = ui_mocks['markdown_instance']
        mock_state.return_value = ui_mocks['state_instance']
        mock_row.return_value = ui_mocks['row_context']
        mock_column.return_value = ui_mocks['column_context']
        html_instance = Mock()
        mock_html.return_value = html_instance
        mock_chatbot.return_value = ui_mocks['chatbot_instance']
        mock_audio.return_value = ui_mocks['audio_instance']
        mock_textbox.return_value = ui_mocks['textbox_instance']
        mock_button.side_effect = [
            ui_mocks['clear_button_instance'],
            ui_mocks['submit_button_instance']
        ]

        # Execute function with custom avatar
        result = launch_bartender_interface(
            handle_input_fn=Mock(),
            clear_state_fn=Mock(),
            avatar_path=custom_avatar_path
        )

        # Verify setup_avatar was NOT called (custom path provided)
        mock_setup_avatar.assert_not_called()

        # Verify HTML component was created (instead of Image)
        mock_html.assert_called_once()

        # Verify create_tab_overlay_html was called with custom avatar path
        mock_create_overlay.assert_called()

        # Verify return value is the blocks instance
        assert result == ui_mocks['blocks_instance']


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
        mock_column, mock_row, mock_state, mock_markdown, mock_blocks, mock_ocean_theme,
        mock_setup_avatar, mock_create_overlay, ui_mocks
    ):
        """Test that UI components are created with correct properties."""
        # Setup mocks using fixture
        mock_setup_avatar.return_value = "assets/bartender_avatar.jpg"
        mock_create_overlay.return_value = '<div>overlay</div>'
        mock_ocean_theme.return_value = ui_mocks['theme_instance']
        mock_blocks.return_value = ui_mocks['blocks_context']
        mock_markdown.return_value = ui_mocks['markdown_instance']
        mock_state.return_value = ui_mocks['state_instance']
        mock_row.return_value = ui_mocks['row_context']
        mock_column.return_value = ui_mocks['column_context']
        html_instance = Mock()
        mock_html.return_value = html_instance
        mock_chatbot.return_value = ui_mocks['chatbot_instance']
        mock_audio.return_value = ui_mocks['audio_instance']
        mock_textbox.return_value = ui_mocks['textbox_instance']
        mock_button.side_effect = [
            ui_mocks['clear_button_instance'],
            ui_mocks['submit_button_instance']
        ]

        # Execute function
        launch_bartender_interface(
            handle_input_fn=Mock(),
            clear_state_fn=Mock(),
            avatar_path=None
        )

        # Verify avatar column properties
        avatar_column_call = mock_column.call_args_list[0]
        assert avatar_column_call[1]['scale'] == 1
        assert avatar_column_call[1]['min_width'] == 200

        # Verify chat column properties
        chat_column_call = mock_column.call_args_list[1]
        assert chat_column_call[1]['scale'] == 1

        # Verify chatbot properties
        mock_chatbot.assert_called_once_with(
            [],
            elem_id="chatbot",
            label="Conversation",
            height=489,
            type="messages"
        )

        # Verify audio properties
        mock_audio.assert_called_once_with(
            label="Agent Voice",
            autoplay=True,
            streaming=False,
            format="wav",
            show_label=True,
            interactive=False
        )

        # Verify textbox properties
        mock_textbox.assert_called_once_with(
            label="Your Order / Message",
            placeholder="What can I get for you? (e.g., 'I'd like a Margarita', 'Show my order')"
        )

        # Verify button properties
        clear_button_call = mock_button.call_args_list[0]
        # Check first positional arg OR keyword arg for value
        clear_btn_value = clear_button_call[1].get('value') if 'value' in clear_button_call[1] else clear_button_call[0][0]
        assert clear_btn_value == "Clear Conversation"

        submit_button_call = mock_button.call_args_list[1]
        submit_btn_value = submit_button_call[1].get('value') if 'value' in submit_button_call[1] else submit_button_call[0][0]
        assert submit_btn_value == "Send"
        assert submit_button_call[1]['variant'] == "primary"

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
        mock_column, mock_row, mock_state, mock_markdown, mock_blocks, mock_ocean_theme,
        mock_setup_avatar, mock_create_overlay, ui_mocks
    ):
        """Test that event handlers are properly configured."""
        # Setup mocks using fixture
        mock_setup_avatar.return_value = "assets/bartender_avatar.jpg"
        mock_create_overlay.return_value = '<div>overlay</div>'
        mock_ocean_theme.return_value = ui_mocks['theme_instance']
        mock_blocks.return_value = ui_mocks['blocks_context']
        mock_markdown.return_value = ui_mocks['markdown_instance']
        mock_state.return_value = ui_mocks['state_instance']
        mock_row.return_value = ui_mocks['row_context']
        mock_column.return_value = ui_mocks['column_context']
        html_instance = Mock()
        mock_html.return_value = html_instance
        mock_chatbot.return_value = ui_mocks['chatbot_instance']
        mock_audio.return_value = ui_mocks['audio_instance']
        mock_textbox.return_value = ui_mocks['textbox_instance']
        mock_button.side_effect = [
            ui_mocks['clear_button_instance'],
            ui_mocks['submit_button_instance']
        ]

        # Create mock handler functions
        mock_handle_input = Mock()
        mock_clear_state = Mock()

        # Execute function
        launch_bartender_interface(
            handle_input_fn=mock_handle_input,
            clear_state_fn=mock_clear_state,
            avatar_path=None
        )

        # Verify event handlers were configured
        # The event handlers are set up in the context manager, so we verify
        # that the submit method was called on the textbox component
        ui_mocks['textbox_instance'].submit.assert_called()

        # Verify the submit handler was configured with correct inputs/outputs
        submit_call = ui_mocks['textbox_instance'].submit.call_args
        assert submit_call[0][0] == mock_handle_input  # handler function
        # Now 4 inputs: msg_input, history_state, tab_state, balance_state
        assert len(submit_call[0][1]) == 4
        # Now 10 outputs: msg_input, chatbot, history, order, audio, overlay, tab, balance, prev_tab, prev_balance
        assert len(submit_call[0][2]) == 10

        # Verify the submit button click handler independently
        submit_click = ui_mocks['submit_button_instance'].click
        submit_click.assert_called_once()
        assert submit_click.call_args[0][0] == mock_handle_input

        # Verify the clear button click handler independently
        # Note: clear button now uses a wrapper function, not the original clear_state_fn
        clear_click = ui_mocks['clear_button_instance'].click
        clear_click.assert_called_once()

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
        self, mock_logger, mock_button, mock_textbox, mock_audio, mock_chatbot, mock_html,
        mock_column, mock_row, mock_state, mock_markdown, mock_blocks, mock_ocean_theme,
        mock_setup_avatar, mock_create_overlay, ui_mocks
    ):
        """Test interface creation when setup_avatar raises exception."""
        # Setup mocks using fixture
        mock_setup_avatar.side_effect = Exception("Avatar setup failed")
        mock_create_overlay.return_value = '<div>overlay</div>'
        mock_ocean_theme.return_value = ui_mocks['theme_instance']
        mock_blocks.return_value = ui_mocks['blocks_context']
        mock_markdown.return_value = ui_mocks['markdown_instance']
        mock_state.return_value = ui_mocks['state_instance']
        mock_row.return_value = ui_mocks['row_context']
        mock_column.return_value = ui_mocks['column_context']
        html_instance = Mock()
        mock_html.return_value = html_instance
        mock_chatbot.return_value = ui_mocks['chatbot_instance']
        mock_audio.return_value = ui_mocks['audio_instance']
        mock_textbox.return_value = ui_mocks['textbox_instance']
        mock_button.side_effect = [
            ui_mocks['clear_button_instance'],
            ui_mocks['submit_button_instance']
        ]

        # Execute function - should still work even if avatar setup fails
        result = launch_bartender_interface(
            handle_input_fn=Mock(),
            clear_state_fn=Mock(),
            avatar_path=None
        )

        # Verify setup_avatar was called despite exception
        mock_setup_avatar.assert_called_once()

        # Verify exception was logged
        mock_logger.exception.assert_called_once()
        assert "Failed to setup avatar" in mock_logger.exception.call_args[0][0]

        # Verify HTML component was created (fallback uses default path)
        mock_html.assert_called_once()

        # Verify interface was still created successfully
        assert result == ui_mocks['blocks_instance']
