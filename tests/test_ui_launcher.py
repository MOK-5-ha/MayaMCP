"""Unit tests for UI launcher."""

from unittest.mock import Mock, patch, MagicMock
import gradio as gr
from src.ui.launcher import launch_bartender_interface


class TestLaunchBartenderInterface:
    """Test cases for launch_bartender_interface function."""

    @patch('src.ui.launcher.setup_avatar')
    @patch('src.ui.launcher.gr.themes.Ocean')
    @patch('src.ui.launcher.gr.Blocks')
    @patch('src.ui.launcher.gr.Markdown')
    @patch('src.ui.launcher.gr.State')
    @patch('src.ui.launcher.gr.Row')
    @patch('src.ui.launcher.gr.Column')
    @patch('src.ui.launcher.gr.Image')
    @patch('src.ui.launcher.gr.Chatbot')
    @patch('src.ui.launcher.gr.Audio')
    @patch('src.ui.launcher.gr.Textbox')
    @patch('src.ui.launcher.gr.Button')
    def test_launch_bartender_interface_with_default_avatar(
        self, mock_button, mock_textbox, mock_audio, mock_chatbot, mock_image,
        mock_column, mock_row, mock_state, mock_markdown, mock_blocks, mock_ocean_theme
    ):
        """Test interface creation with default avatar setup."""
        # Setup mocks
        mock_setup_avatar = Mock()
        mock_setup_avatar.return_value = "assets/bartender_avatar.jpg"
        
        mock_theme_instance = Mock()
        mock_ocean_theme.return_value = mock_theme_instance
        
        mock_blocks_instance = Mock()
        mock_blocks.return_value.__enter__.return_value = mock_blocks_instance
        mock_blocks.return_value.__exit__.return_value = None
        
        mock_markdown_instance = Mock()
        mock_markdown.return_value = mock_markdown_instance
        
        mock_state_instance = Mock()
        mock_state.return_value = mock_state_instance
        
        mock_row_instance = Mock()
        mock_row.return_value.__enter__.return_value = mock_row_instance
        mock_row.return_value.__exit__.return_value = None
        
        mock_column_instance = Mock()
        mock_column.return_value.__enter__.return_value = mock_column_instance
        mock_column.return_value.__exit__.return_value = None
        
        mock_image_instance = Mock()
        mock_image.return_value = mock_image_instance
        
        mock_chatbot_instance = Mock()
        mock_chatbot.return_value = mock_chatbot_instance
        
        mock_audio_instance = Mock()
        mock_audio.return_value = mock_audio_instance
        
        mock_textbox_instance = Mock()
        mock_textbox.return_value = mock_textbox_instance
        
        mock_button_instance = Mock()
        mock_button.return_value = mock_button_instance

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
        mock_blocks.assert_called_once_with(theme=mock_theme_instance)

        # Verify Markdown components were created
        assert mock_markdown.call_count == 2  # Two markdown elements
        mock_markdown.assert_any_call("# MOK 5-ha - Meet Maya the Bartender 🍹👋")
        mock_markdown.assert_any_call("Welcome to MOK 5-ha! I'm Maya, your virtual bartender. Ask me for a drink or check your order.")

        # Verify State components were created
        assert mock_state.call_count == 2  # history_state and order_state

        # Verify Row and Column structure was created
        mock_row.assert_called_once()
        assert mock_column.call_count == 2  # Two columns (avatar and chat)

        # Verify UI components were created
        mock_image.assert_called_once()
        mock_chatbot.assert_called_once()
        mock_audio.assert_called_once()
        mock_textbox.assert_called_once()
        assert mock_button.call_count == 2  # Clear and Submit buttons

        # Verify return value is the blocks instance
        assert result == mock_blocks_instance

    @patch('src.ui.launcher.setup_avatar')
    @patch('src.ui.launcher.gr.themes.Ocean')
    @patch('src.ui.launcher.gr.Blocks')
    @patch('src.ui.launcher.gr.Markdown')
    @patch('src.ui.launcher.gr.State')
    @patch('src.ui.launcher.gr.Row')
    @patch('src.ui.launcher.gr.Column')
    @patch('src.ui.launcher.gr.Image')
    @patch('src.ui.launcher.gr.Chatbot')
    @patch('src.ui.launcher.gr.Audio')
    @patch('src.ui.launcher.gr.Textbox')
    @patch('src.ui.launcher.gr.Button')
    def test_launch_bartender_interface_with_custom_avatar(
        self, mock_button, mock_textbox, mock_audio, mock_chatbot, mock_image,
        mock_column, mock_row, mock_state, mock_markdown, mock_blocks, mock_ocean_theme, mock_setup_avatar
    ):
        """Test interface creation with custom avatar path."""
        # Setup mocks
        custom_avatar_path = "custom/avatar/path.jpg"
        
        mock_theme_instance = Mock()
        mock_ocean_theme.return_value = mock_theme_instance
        
        mock_blocks_instance = Mock()
        mock_blocks.return_value.__enter__.return_value = mock_blocks_instance
        mock_blocks.return_value.__exit__.return_value = None
        
        mock_markdown_instance = Mock()
        mock_markdown.return_value = mock_markdown_instance
        
        mock_state_instance = Mock()
        mock_state.return_value = mock_state_instance
        
        mock_row_instance = Mock()
        mock_row.return_value.__enter__.return_value = mock_row_instance
        mock_row.return_value.__exit__.return_value = None
        
        mock_column_instance = Mock()
        mock_column.return_value.__enter__.return_value = mock_column_instance
        mock_column.return_value.__exit__.return_value = None
        
        mock_image_instance = Mock()
        mock_image.return_value = mock_image_instance
        
        mock_chatbot_instance = Mock()
        mock_chatbot.return_value = mock_chatbot_instance
        
        mock_audio_instance = Mock()
        mock_audio.return_value = mock_audio_instance
        
        mock_textbox_instance = Mock()
        mock_textbox.return_value = mock_textbox_instance
        
        mock_button_instance = Mock()
        mock_button.return_value = mock_button_instance

        # Execute function with custom avatar
        result = launch_bartender_interface(
            handle_input_fn=Mock(),
            clear_state_fn=Mock(),
            avatar_path=custom_avatar_path
        )

        # Verify setup_avatar was NOT called (custom path provided)
        mock_setup_avatar.assert_not_called()

        # Verify image was created with custom path
        mock_image.assert_called_once_with(
            value=custom_avatar_path,
            label="Bartender Avatar",
            show_label=False,
            interactive=False,
            height=600,
            elem_classes=["avatar-image"]
        )

    @patch('src.ui.launcher.setup_avatar')
    @patch('src.ui.launcher.gr.themes.Ocean')
    @patch('src.ui.launcher.gr.Blocks')
    @patch('src.ui.launcher.gr.Markdown')
    @patch('src.ui.launcher.gr.State')
    @patch('src.ui.launcher.gr.Row')
    @patch('src.ui.launcher.gr.Column')
    @patch('src.ui.launcher.gr.Image')
    @patch('src.ui.launcher.gr.Chatbot')
    @patch('src.ui.launcher.gr.Audio')
    @patch('src.ui.launcher.gr.Textbox')
    @patch('src.ui.launcher.gr.Button')
    def test_launch_bartender_interface_component_properties(
        self, mock_button, mock_textbox, mock_audio, mock_chatbot, mock_image,
        mock_column, mock_row, mock_state, mock_markdown, mock_blocks, mock_ocean_theme, mock_setup_avatar
    ):
        """Test that UI components are created with correct properties."""
        # Setup mocks
        mock_setup_avatar.return_value = "assets/bartender_avatar.jpg"
        
        mock_theme_instance = Mock()
        mock_ocean_theme.return_value = mock_theme_instance
        
        mock_blocks_instance = Mock()
        mock_blocks.return_value.__enter__.return_value = mock_blocks_instance
        mock_blocks.return_value.__exit__.return_value = None
        
        mock_markdown_instance = Mock()
        mock_markdown.return_value = mock_markdown_instance
        
        mock_state_instance = Mock()
        mock_state.return_value = mock_state_instance
        
        mock_row_instance = Mock()
        mock_row.return_value.__enter__.return_value = mock_row_instance
        mock_row.return_value.__exit__.return_value = None
        
        mock_column_instance = Mock()
        mock_column.return_value.__enter__.return_value = mock_column_instance
        mock_column.return_value.__exit__.return_value = None
        
        mock_image_instance = Mock()
        mock_image.return_value = mock_image_instance
        
        mock_chatbot_instance = Mock()
        mock_chatbot.return_value = mock_chatbot_instance
        
        mock_audio_instance = Mock()
        mock_audio.return_value = mock_audio_instance
        
        mock_textbox_instance = Mock()
        mock_textbox.return_value = mock_textbox_instance
        
        mock_button_instance = Mock()
        mock_button.return_value = mock_button_instance

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
        assert clear_button_call[1]['value'] == "Clear Conversation"

        submit_button_call = mock_button.call_args_list[1]
        assert submit_button_call[1]['value'] == "Send"
        assert submit_button_call[1]['variant'] == "primary"

    @patch('src.ui.launcher.setup_avatar')
    @patch('src.ui.launcher.gr.themes.Ocean')
    @patch('src.ui.launcher.gr.Blocks')
    @patch('src.ui.launcher.gr.Markdown')
    @patch('src.ui.launcher.gr.State')
    @patch('src.ui.launcher.gr.Row')
    @patch('src.ui.launcher.gr.Column')
    @patch('src.ui.launcher.gr.Image')
    @patch('src.ui.launcher.gr.Chatbot')
    @patch('src.ui.launcher.gr.Audio')
    @patch('src.ui.launcher.gr.Textbox')
    @patch('src.ui.launcher.gr.Button')
    def test_launch_bartender_interface_event_handlers(
        self, mock_button, mock_textbox, mock_audio, mock_chatbot, mock_image,
        mock_column, mock_row, mock_state, mock_markdown, mock_blocks, mock_ocean_theme, mock_setup_avatar
    ):
        """Test that event handlers are properly configured."""
        # Setup mocks
        mock_setup_avatar.return_value = "assets/bartender_avatar.jpg"
        
        mock_theme_instance = Mock()
        mock_ocean_theme.return_value = mock_theme_instance
        
        mock_blocks_instance = Mock()
        mock_blocks.return_value.__enter__.return_value = mock_blocks_instance
        mock_blocks.return_value.__exit__.return_value = None
        
        mock_markdown_instance = Mock()
        mock_markdown.return_value = mock_markdown_instance
        
        mock_state_instance = Mock()
        mock_state.return_value = mock_state_instance
        
        mock_row_instance = Mock()
        mock_row.return_value.__enter__.return_value = mock_row_instance
        mock_row.return_value.__exit__.return_value = None
        
        mock_column_instance = Mock()
        mock_column.return_value.__enter__.return_value = mock_column_instance
        mock_column.return_value.__exit__.return_value = None
        
        mock_image_instance = Mock()
        mock_image.return_value = mock_image_instance
        
        mock_chatbot_instance = Mock()
        mock_chatbot.return_value = mock_chatbot_instance
        
        mock_audio_instance = Mock()
        mock_audio.return_value = mock_audio_instance
        
        mock_textbox_instance = Mock()
        mock_textbox.return_value = mock_textbox_instance
        
        mock_button_instance = Mock()
        mock_button.return_value = mock_button_instance

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
        # that the submit and click methods were called on the UI components
        mock_textbox_instance.submit.assert_called()
        mock_button_instance.click.assert_called()

        # Verify the submit handler was configured with correct inputs/outputs
        submit_call = mock_textbox_instance.submit.call_args
        assert submit_call[0][0] == mock_handle_input  # handler function
        assert len(submit_call[0][1]) == 2  # submit_inputs count
        assert len(submit_call[0][2]) == 5  # submit_outputs count

        # Verify the click handler was configured for submit button
        submit_button_click = mock_button_instance.click.call_args_list[0]
        assert submit_button_click[0][0] == mock_handle_input

        # Verify the clear button click handler
        clear_button_click = mock_button_instance.click.call_args_list[1]
        assert clear_button_click[0][0] == mock_clear_state

    @patch('src.ui.launcher.setup_avatar')
    @patch('src.ui.launcher.gr.themes.Ocean')
    @patch('src.ui.launcher.gr.Blocks')
    @patch('src.ui.launcher.gr.Markdown')
    @patch('src.ui.launcher.gr.State')
    @patch('src.ui.launcher.gr.Row')
    @patch('src.ui.launcher.gr.Column')
    @patch('src.ui.launcher.gr.Image')
    @patch('src.ui.launcher.gr.Chatbot')
    @patch('src.ui.launcher.gr.Audio')
    @patch('src.ui.launcher.gr.Textbox')
    @patch('src.ui.launcher.gr.Button')
    def test_launch_bartender_interface_setup_avatar_exception(
        self, mock_button, mock_textbox, mock_audio, mock_chatbot, mock_image,
        mock_column, mock_row, mock_state, mock_markdown, mock_blocks, mock_ocean_theme, mock_setup_avatar
    ):
        """Test interface creation when setup_avatar raises exception."""
        # Setup mocks
        mock_setup_avatar.side_effect = Exception("Avatar setup failed")
        
        mock_theme_instance = Mock()
        mock_ocean_theme.return_value = mock_theme_instance
        
        mock_blocks_instance = Mock()
        mock_blocks.return_value.__enter__.return_value = mock_blocks_instance
        mock_blocks.return_value.__exit__.return_value = None
        
        mock_markdown_instance = Mock()
        mock_markdown.return_value = mock_markdown_instance
        
        mock_state_instance = Mock()
        mock_state.return_value = mock_state_instance
        
        mock_row_instance = Mock()
        mock_row.return_value.__enter__.return_value = mock_row_instance
        mock_row.return_value.__exit__.return_value = None
        
        mock_column_instance = Mock()
        mock_column.return_value.__enter__.return_value = mock_column_instance
        mock_column.return_value.__exit__.return_value = None
        
        mock_image_instance = Mock()
        mock_image.return_value = mock_image_instance
        
        mock_chatbot_instance = Mock()
        mock_chatbot.return_value = mock_chatbot_instance
        
        mock_audio_instance = Mock()
        mock_audio.return_value = mock_audio_instance
        
        mock_textbox_instance = Mock()
        mock_textbox.return_value = mock_textbox_instance
        
        mock_button_instance = Mock()
        mock_button.return_value = mock_button_instance

        # Execute function - should still work even if avatar setup fails
        result = launch_bartender_interface(
            handle_input_fn=Mock(),
            clear_state_fn=Mock(),
            avatar_path=None
        )

        # Verify setup_avatar was called despite exception
        mock_setup_avatar.assert_called_once()

        # Verify interface was still created successfully
        assert result == mock_blocks_instance
