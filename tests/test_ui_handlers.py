"""Unit tests for UI handlers."""

from unittest.mock import Mock, patch, MagicMock
from src.ui.handlers import handle_gradio_input, clear_chat_state


class TestHandleGradioInput:
    """Test cases for handle_gradio_input function."""

    @patch('src.ui.handlers.get_current_order_state')
    @patch('src.ui.handlers.get_voice_audio')
    @patch('src.ui.handlers.process_order')
    def test_handle_gradio_input_successful_processing(
        self, mock_process_order, mock_get_voice_audio, mock_get_current_order_state
    ):
        """Test successful input processing with TTS."""
        # Setup mocks
        mock_process_order.return_value = (
            "Here's your drink!",  # response_text
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],  # updated_history
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],  # updated_history_for_gradio
            [{'name': 'Martini', 'price': 13.0}],  # updated_order
            None  # additional return value
        )
        
        mock_get_voice_audio.return_value = b'audio_data'
        mock_get_current_order_state.return_value = [{'name': 'Martini', 'price': 13.0}]

        # Execute function
        mock_cartesia_client = Mock()
        mock_request = Mock()
        mock_request.session_hash = "test_session"
        test_state = {}
        
        result = handle_gradio_input(
            user_input="I'd like a Martini",
            session_history_state=[{'role': 'user', 'content': 'Hi'}],
            request=mock_request,
            llm=Mock(),
            cartesia_client=mock_cartesia_client,
            rag_index=None,
            rag_documents=None,
            rag_retriever=None,
            api_key="test_key",
            app_state=test_state
        )

        # Verify process_order was called with correct parameters
        mock_process_order.assert_called_once()
        call_args = mock_process_order.call_args
        assert call_args[1]['user_input_text'] == "I'd like a Martini"
        assert call_args[1]['current_session_history'] == [{'role': 'user', 'content': 'Hi'}]
        assert call_args[1]['api_key'] == "test_key"
        assert call_args[1]['session_id'] == "test_session"
        assert call_args[1]['app_state'] is test_state

        # Verify TTS was called
        mock_get_voice_audio.assert_called_once_with("Here's your drink!", mock_cartesia_client)

        # Note: get_current_order_state is NOT called in the happy path anymore,
        # since the implementation now uses updated_order from process_order() directly

        # Verify return value structure
        expected_result = (
            "",  # empty_input
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],  # updated_history
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],  # updated_history_for_gradio
            [{'name': 'Martini', 'price': 13.0}],  # updated_order
            b'audio_data'  # audio_data
        )
        assert result == expected_result

    @patch('src.ui.handlers.get_current_order_state')
    @patch('src.ui.handlers.get_voice_audio')
    @patch('src.ui.handlers.process_order')
    def test_handle_gradio_input_no_tts_client(
        self, mock_process_order, mock_get_voice_audio, mock_get_current_order_state
    ):
        """Test input processing when TTS client is not available."""
        # Setup mocks
        mock_process_order.return_value = (
            "Here's your drink!",
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'name': 'Martini', 'price': 13.0}],
            None
        )
        
        mock_get_current_order_state.return_value = [{'name': 'Martini', 'price': 13.0}]

        # Execute function without TTS client
        mock_request = Mock()
        mock_request.session_hash = "test_session"
        
        result = handle_gradio_input(
            user_input="I'd like a Martini",
            session_history_state=[{'role': 'user', 'content': 'Hi'}],
            request=mock_request,
            llm=Mock(),
            cartesia_client=None,  # No TTS client
            rag_index=None,
            rag_documents=None,
            rag_retriever=None,
            api_key="test_key",
            app_state={}
        )

        # Verify TTS was not called
        mock_get_voice_audio.assert_not_called()

        # Verify return value has None for audio
        assert result[4] is None  # audio_data should be None

    @patch('src.ui.handlers.get_current_order_state')
    @patch('src.ui.handlers.get_voice_audio')
    @patch('src.ui.handlers.process_order')
    def test_handle_gradio_input_empty_response_text(
        self, mock_process_order, mock_get_voice_audio, mock_get_current_order_state
    ):
        """Test input processing when response text is empty."""
        # Setup mocks
        mock_process_order.return_value = (
            "",  # empty response_text
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'name': 'Martini', 'price': 13.0}],
            None
        )
        
        mock_get_current_order_state.return_value = [{'name': 'Martini', 'price': 13.0}]

        # Execute function
        mock_request = Mock()
        mock_request.session_hash = "test_session"

        result = handle_gradio_input(
            user_input="I'd like a Martini",
            session_history_state=[{'role': 'user', 'content': 'Hi'}],
            request=mock_request,
            llm=Mock(),
            cartesia_client=Mock(),
            rag_index=None,
            rag_documents=None,
            rag_retriever=None,
            api_key="test_key",
            app_state={}
        )

        # Verify TTS was not called due to empty response
        mock_get_voice_audio.assert_not_called()

        # Verify return value has None for audio
        assert result[4] is None

    @patch('src.ui.handlers.get_current_order_state')
    @patch('src.ui.handlers.get_voice_audio')
    @patch('src.ui.handlers.process_order')
    def test_handle_gradio_input_tts_failure(
        self, mock_process_order, mock_get_voice_audio, mock_get_current_order_state
    ):
        """Test input processing when TTS generation fails."""
        # Setup mocks
        mock_process_order.return_value = (
            "Here's your drink!",
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'name': 'Martini', 'price': 13.0}],
            None
        )
        
        mock_get_voice_audio.side_effect = Exception("TTS failed")
        mock_get_current_order_state.return_value = [{'name': 'Martini', 'price': 13.0}]

        # Execute function
        mock_request = Mock()
        mock_request.session_hash = "test_session"
        
        result = handle_gradio_input(
            user_input="I'd like a Martini",
            session_history_state=[{'role': 'user', 'content': 'Hi'}],
            request=mock_request,
            llm=Mock(),
            cartesia_client=Mock(),
            rag_index=None,
            rag_documents=None,
            rag_retriever=None,
            api_key="test_key",
            app_state={}
        )

        # Verify TTS was called but failed
        mock_get_voice_audio.assert_called_once()

        # Verify return value has None for audio due to failure
        assert result[4] is None

    @patch('src.ui.handlers.get_current_order_state')
    @patch('src.ui.handlers.get_voice_audio')
    @patch('src.ui.handlers.process_order')
    def test_handle_gradio_input_process_order_exception(
        self, mock_process_order, mock_get_voice_audio, mock_get_current_order_state
    ):
        """Test input processing when process_order raises exception."""
        # Setup mocks
        mock_process_order.side_effect = Exception("Processing failed")
        mock_get_current_order_state.return_value = [{'name': 'Martini', 'price': 13.0}]

        # Execute function
        mock_request = Mock()
        mock_request.session_hash = "test_session"

        result = handle_gradio_input(
            user_input="I'd like a Martini",
            session_history_state=[{'role': 'user', 'content': 'Hi'}],
            request=mock_request,
            llm=Mock(),
            cartesia_client=Mock(),
            rag_index=None,
            rag_documents=None,
            rag_retriever=None,
            api_key="test_key",
            app_state={}
        )

        # Verify process_order was called
        mock_process_order.assert_called_once()

        # Verify TTS was not called due to exception
        mock_get_voice_audio.assert_not_called()

        # Verify return value structure for error case
        assert result[0] == ""  # empty_input
        assert len(result[1]) == 3  # safe_history with error message
        assert "I'm having a small hiccup" in result[1][2]['content']
        assert result[2] == result[1]  # same history for gradio
        assert result[3] == [{'name': 'Martini', 'price': 13.0}]  # current order state
        assert result[4] is None  # no audio

    @patch('src.ui.handlers.get_current_order_state')
    @patch('src.ui.handlers.get_voice_audio')
    @patch('src.ui.handlers.process_order')
    def test_handle_gradio_input_with_rag_components(
        self, mock_process_order, mock_get_voice_audio, mock_get_current_order_state
    ):
        """Test input processing with RAG components provided."""
        # Setup mocks
        mock_process_order.return_value = (
            "Here's your drink!",
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'name': 'Martini', 'price': 13.0}],
            None
        )
        
        mock_get_voice_audio.return_value = b'audio_data'
        mock_get_current_order_state.return_value = [{'name': 'Martini', 'price': 13.0}]

        # Execute function with RAG components
        mock_request = Mock()
        mock_request.session_hash = "test_session"

        result = handle_gradio_input(
            user_input="I'd like a Martini",
            session_history_state=[{'role': 'user', 'content': 'Hi'}],
            request=mock_request,
            llm=Mock(),
            cartesia_client=Mock(),
            rag_index=Mock(),
            rag_documents=["doc1", "doc2"],
            rag_retriever=Mock(),
            api_key="test_key",
            app_state={}
        )

        # Verify process_order was called with RAG parameters
        mock_process_order.assert_called_once()
        call_args = mock_process_order.call_args
        assert call_args[1]['rag_index'] is not None
        assert call_args[1]['rag_documents'] == ["doc1", "doc2"]
        assert call_args[1]['rag_retriever'] is not None

        # Verify return value structure
        expected_result = (
            "",  # empty_input
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],  # updated_history
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],  # updated_history_for_gradio
            [{'name': 'Martini', 'price': 13.0}],  # updated_order
            b'audio_data'  # audio_data
        )
        assert result == expected_result

    @patch('src.ui.handlers.get_current_order_state')
    @patch('src.ui.handlers.get_voice_audio')
    @patch('src.ui.handlers.process_order')
    def test_handle_gradio_input_whitespace_only_response(
        self, mock_process_order, mock_get_voice_audio, mock_get_current_order_state
    ):
        """Test input processing when response text is only whitespace."""
        # Setup mocks
        mock_process_order.return_value = (
            "   ",  # whitespace-only response_text
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'name': 'Martini', 'price': 13.0}],
            None
        )
        
        mock_get_current_order_state.return_value = [{'name': 'Martini', 'price': 13.0}]

        # Execute function
        mock_request = Mock()
        mock_request.session_hash = "test_session"

        result = handle_gradio_input(
            user_input="I'd like a Martini",
            session_history_state=[{'role': 'user', 'content': 'Hi'}],
            request=mock_request,
            llm=Mock(),
            cartesia_client=Mock(),
            rag_index=None,
            rag_documents=None,
            rag_retriever=None,
            api_key="test_key",
            app_state={}
        )

        # Verify TTS was not called due to whitespace-only response
        mock_get_voice_audio.assert_not_called()

        # Verify return value has None for audio
        assert result[4] is None


class TestClearChatState:
    """Test cases for clear_chat_state function."""

    @patch('src.ui.handlers.reset_session_state')
    def test_clear_chat_state_success(self, mock_reset_session_state):
        """Test successful chat state clearing."""
        # Execute function (no arguments needed)
        mock_request = Mock()
        mock_request.session_hash = "test_session"
        result = clear_chat_state(request=mock_request, app_state={})

        # Verify reset_session_state was called
        mock_reset_session_state.assert_called_once()

        # Verify return value structure (should be cleared)
        expected_result = ([], [], [], None)
        assert result == expected_result

    @patch('src.ui.handlers.reset_session_state')
    def test_clear_chat_state_with_exception(self, mock_reset_session_state):
        """Test chat state clearing when reset_session_state raises exception."""
        # Setup mock to raise exception
        mock_reset_session_state.side_effect = Exception("Reset failed")

        # Execute function (no arguments needed)
        mock_request = Mock()
        mock_request.session_hash = "test_session"
        result = clear_chat_state(request=mock_request, app_state={})

        # Verify reset_session_state was still called
        mock_reset_session_state.assert_called_once()

        # Verify return value is still empty lists even on error
        # (user requested clear, so we clear regardless of backend error)
        expected_result = ([], [], [], None)
        assert result == expected_result
