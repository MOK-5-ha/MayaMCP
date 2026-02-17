"""Unit tests for UI handlers."""

from unittest.mock import Mock, patch, MagicMock
from src.ui.handlers import handle_gradio_input, clear_chat_state


def _make_request(session_id="test_session"):
    """Helper to create a mock Gradio Request."""
    r = Mock()
    r.session_hash = session_id
    return r


def _seed_session_keys(app_state, session_id="test_session"):
    """Populate app_state with validated BYOK keys for the given session."""
    import copy
    from src.utils.state_manager import _deep_copy_defaults
    defaults = _deep_copy_defaults()
    defaults['api_keys'] = {
        'gemini_key': 'test_gemini_key',
        'cartesia_key': 'test_cartesia_key',
        'keys_validated': True,
    }
    app_state[session_id] = defaults


class TestHandleGradioInput:
    """Test cases for handle_gradio_input function."""

    @patch('src.ui.handlers.create_tab_overlay_html')
    @patch('src.ui.handlers.get_payment_state')
    @patch('src.ui.handlers.get_current_order_state')
    @patch('src.ui.handlers.get_voice_audio')
    @patch('src.ui.handlers.process_order')
    @patch('src.ui.handlers.get_session_tts')
    @patch('src.ui.handlers.get_session_llm')
    def test_handle_gradio_input_successful_processing(
        self, mock_get_llm, mock_get_tts, mock_process_order, mock_get_voice_audio,
        mock_get_current_order_state, mock_get_payment_state, mock_create_overlay
    ):
        """Test successful input processing with TTS."""
        mock_llm = Mock()
        mock_tts = Mock()
        mock_get_llm.return_value = mock_llm
        mock_get_tts.return_value = mock_tts

        mock_process_order.return_value = (
            "Here's your drink!",
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'name': 'Martini', 'price': 13.0}],
            None,
            None,  # emotion_state
        )
        mock_get_voice_audio.return_value = b'audio_data'
        mock_get_current_order_state.return_value = [{'name': 'Martini', 'price': 13.0}]
        mock_get_payment_state.return_value = {
            'tab_total': 13.0, 'balance': 987.0,
            'tip_percentage': None, 'tip_amount': 0.0
        }
        mock_create_overlay.return_value = '<div>overlay</div>'

        test_state = {}
        _seed_session_keys(test_state)

        result = handle_gradio_input(
            user_input="I'd like a Martini",
            session_history_state=[{'role': 'user', 'content': 'Hi'}],
            current_tab=0.0,
            current_balance=1000.0,
            current_tip_percentage=None,
            current_tip_amount=0.0,
            request=_make_request(),
            tools=[],
            rag_index=None,
            rag_documents=None,
            rag_retriever=None,
            rag_api_key="test_rag_key",
            app_state=test_state
        )

        mock_process_order.assert_called_once()
        call_args = mock_process_order.call_args
        assert call_args[1]['user_input_text'] == "I'd like a Martini"
        assert call_args[1]['llm'] is mock_llm

        mock_get_voice_audio.assert_called_once_with("Here's your drink!", mock_tts)

        assert result[0] == ""           # empty_input
        assert result[4] == b'audio_data'  # audio
        assert result[5] == '<div>overlay</div>'  # overlay
        assert result[6] == 13.0         # new_tab
        assert result[7] == 987.0        # new_balance
        assert result[13] == ""          # quota_error_html (empty on success)

    @patch('src.ui.handlers.create_tab_overlay_html')
    @patch('src.ui.handlers.get_payment_state')
    @patch('src.ui.handlers.get_current_order_state')
    @patch('src.ui.handlers.get_voice_audio')
    @patch('src.ui.handlers.process_order')
    @patch('src.ui.handlers.get_session_tts')
    @patch('src.ui.handlers.get_session_llm')
    def test_handle_gradio_input_no_tts_client(
        self, mock_get_llm, mock_get_tts, mock_process_order, mock_get_voice_audio,
        mock_get_current_order_state, mock_get_payment_state, mock_create_overlay
    ):
        """Test input processing when TTS client is not available."""
        mock_get_llm.return_value = Mock()
        mock_get_tts.return_value = None  # No TTS

        mock_process_order.return_value = (
            "Here's your drink!",
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'name': 'Martini', 'price': 13.0}],
            None, None,
        )
        mock_get_current_order_state.return_value = [{'name': 'Martini', 'price': 13.0}]
        mock_get_payment_state.return_value = {
            'tab_total': 13.0, 'balance': 987.0,
            'tip_percentage': None, 'tip_amount': 0.0
        }
        mock_create_overlay.return_value = '<div>overlay</div>'

        test_state = {}
        _seed_session_keys(test_state)

        result = handle_gradio_input(
            user_input="I'd like a Martini",
            session_history_state=[{'role': 'user', 'content': 'Hi'}],
            current_tab=0.0, current_balance=1000.0,
            current_tip_percentage=None, current_tip_amount=0.0,
            request=_make_request(),
            tools=[], app_state=test_state
        )

        mock_get_voice_audio.assert_not_called()
        assert result[4] is None

    @patch('src.ui.handlers.create_tab_overlay_html')
    @patch('src.ui.handlers.get_payment_state')
    @patch('src.ui.handlers.get_current_order_state')
    @patch('src.ui.handlers.get_voice_audio')
    @patch('src.ui.handlers.process_order')
    @patch('src.ui.handlers.get_session_tts')
    @patch('src.ui.handlers.get_session_llm')
    def test_handle_gradio_input_empty_response_text(
        self, mock_get_llm, mock_get_tts, mock_process_order, mock_get_voice_audio,
        mock_get_current_order_state, mock_get_payment_state, mock_create_overlay
    ):
        """Test input processing when response text is empty."""
        mock_get_llm.return_value = Mock()
        mock_get_tts.return_value = Mock()

        mock_process_order.return_value = (
            "",
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'name': 'Martini', 'price': 13.0}],
            None, None,
        )
        mock_get_current_order_state.return_value = [{'name': 'Martini', 'price': 13.0}]
        mock_get_payment_state.return_value = {
            'tab_total': 13.0, 'balance': 987.0,
            'tip_percentage': None, 'tip_amount': 0.0
        }
        mock_create_overlay.return_value = '<div>overlay</div>'

        test_state = {}
        _seed_session_keys(test_state)

        result = handle_gradio_input(
            user_input="I'd like a Martini",
            session_history_state=[{'role': 'user', 'content': 'Hi'}],
            current_tab=0.0, current_balance=1000.0,
            current_tip_percentage=None, current_tip_amount=0.0,
            request=_make_request(),
            tools=[], app_state=test_state
        )

        mock_get_voice_audio.assert_not_called()
        assert result[4] is None

    @patch('src.ui.handlers.create_tab_overlay_html')
    @patch('src.ui.handlers.get_payment_state')
    @patch('src.ui.handlers.get_current_order_state')
    @patch('src.ui.handlers.get_voice_audio')
    @patch('src.ui.handlers.process_order')
    @patch('src.ui.handlers.get_session_tts')
    @patch('src.ui.handlers.get_session_llm')
    def test_handle_gradio_input_tts_failure(
        self, mock_get_llm, mock_get_tts, mock_process_order, mock_get_voice_audio,
        mock_get_current_order_state, mock_get_payment_state, mock_create_overlay
    ):
        """Test input processing when TTS generation fails."""
        mock_get_llm.return_value = Mock()
        mock_tts = Mock()
        mock_get_tts.return_value = mock_tts

        mock_process_order.return_value = (
            "Here's your drink!",
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'name': 'Martini', 'price': 13.0}],
            None, None,
        )
        mock_get_voice_audio.side_effect = Exception("TTS failed")
        mock_get_current_order_state.return_value = [{'name': 'Martini', 'price': 13.0}]
        mock_get_payment_state.return_value = {
            'tab_total': 13.0, 'balance': 987.0,
            'tip_percentage': None, 'tip_amount': 0.0
        }
        mock_create_overlay.return_value = '<div>overlay</div>'

        test_state = {}
        _seed_session_keys(test_state)

        result = handle_gradio_input(
            user_input="I'd like a Martini",
            session_history_state=[{'role': 'user', 'content': 'Hi'}],
            current_tab=0.0, current_balance=1000.0,
            current_tip_percentage=None, current_tip_amount=0.0,
            request=_make_request(),
            tools=[], app_state=test_state
        )

        mock_get_voice_audio.assert_called_once()
        assert result[4] is None

    @patch('src.ui.handlers.create_tab_overlay_html')
    @patch('src.ui.handlers.get_current_order_state')
    @patch('src.ui.handlers.get_voice_audio')
    @patch('src.ui.handlers.process_order')
    @patch('src.ui.handlers.get_session_tts')
    @patch('src.ui.handlers.get_session_llm')
    def test_handle_gradio_input_process_order_exception(
        self, mock_get_llm, mock_get_tts, mock_process_order, mock_get_voice_audio,
        mock_get_current_order_state, mock_create_overlay
    ):
        """Test input processing when process_order raises exception."""
        mock_get_llm.return_value = Mock()
        mock_get_tts.return_value = Mock()

        mock_process_order.side_effect = Exception("Processing failed")
        mock_get_current_order_state.return_value = [{'name': 'Martini', 'price': 13.0}]
        mock_create_overlay.return_value = '<div>overlay</div>'

        test_state = {}
        _seed_session_keys(test_state)

        result = handle_gradio_input(
            user_input="I'd like a Martini",
            session_history_state=[{'role': 'user', 'content': 'Hi'}],
            current_tab=0.0, current_balance=1000.0,
            current_tip_percentage=None, current_tip_amount=0.0,
            request=_make_request(),
            tools=[], app_state=test_state
        )

        mock_process_order.assert_called_once()
        mock_get_voice_audio.assert_not_called()

        assert result[0] == ""
        assert len(result[1]) == 3
        assert "hiccup" in result[1][2]['content']
        assert result[4] is None
        assert result[5] == '<div>overlay</div>'

    @patch('src.ui.handlers.create_tab_overlay_html')
    @patch('src.ui.handlers.get_payment_state')
    @patch('src.ui.handlers.get_current_order_state')
    @patch('src.ui.handlers.get_voice_audio')
    @patch('src.ui.handlers.process_order')
    @patch('src.ui.handlers.get_session_tts')
    @patch('src.ui.handlers.get_session_llm')
    def test_handle_gradio_input_with_rag_components(
        self, mock_get_llm, mock_get_tts, mock_process_order, mock_get_voice_audio,
        mock_get_current_order_state, mock_get_payment_state, mock_create_overlay
    ):
        """Test input processing with RAG components provided."""
        mock_get_llm.return_value = Mock()
        mock_get_tts.return_value = Mock()

        mock_process_order.return_value = (
            "Here's your drink!",
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'name': 'Martini', 'price': 13.0}],
            None, None,
        )
        mock_get_voice_audio.return_value = b'audio_data'
        mock_get_current_order_state.return_value = [{'name': 'Martini', 'price': 13.0}]
        mock_get_payment_state.return_value = {
            'tab_total': 13.0, 'balance': 987.0,
            'tip_percentage': None, 'tip_amount': 0.0
        }
        mock_create_overlay.return_value = '<div>overlay</div>'

        test_state = {}
        _seed_session_keys(test_state)

        result = handle_gradio_input(
            user_input="I'd like a Martini",
            session_history_state=[{'role': 'user', 'content': 'Hi'}],
            current_tab=0.0, current_balance=1000.0,
            current_tip_percentage=None, current_tip_amount=0.0,
            request=_make_request(),
            tools=[],
            rag_index=Mock(),
            rag_documents=["doc1", "doc2"],
            rag_retriever=Mock(),
            rag_api_key="test_rag_key",
            app_state=test_state
        )

        mock_process_order.assert_called_once()
        call_args = mock_process_order.call_args
        assert call_args[1]['rag_index'] is not None
        assert call_args[1]['rag_documents'] == ["doc1", "doc2"]
        assert call_args[1]['rag_retriever'] is not None

        assert result[0] == ""
        assert result[4] == b'audio_data'
        assert result[5] == '<div>overlay</div>'

    @patch('src.ui.handlers.create_tab_overlay_html')
    @patch('src.ui.handlers.get_payment_state')
    @patch('src.ui.handlers.get_current_order_state')
    @patch('src.ui.handlers.get_voice_audio')
    @patch('src.ui.handlers.process_order')
    @patch('src.ui.handlers.get_session_tts')
    @patch('src.ui.handlers.get_session_llm')
    def test_handle_gradio_input_whitespace_only_response(
        self, mock_get_llm, mock_get_tts, mock_process_order, mock_get_voice_audio,
        mock_get_current_order_state, mock_get_payment_state, mock_create_overlay
    ):
        """Test input processing when response text is only whitespace."""
        mock_get_llm.return_value = Mock()
        mock_get_tts.return_value = Mock()

        mock_process_order.return_value = (
            "   ",
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'role': 'user', 'content': 'Hi'}, {'role': 'assistant', 'content': 'Hello!'}],
            [{'name': 'Martini', 'price': 13.0}],
            None, None,
        )
        mock_get_current_order_state.return_value = [{'name': 'Martini', 'price': 13.0}]
        mock_get_payment_state.return_value = {
            'tab_total': 13.0, 'balance': 987.0,
            'tip_percentage': None, 'tip_amount': 0.0
        }
        mock_create_overlay.return_value = '<div>overlay</div>'

        test_state = {}
        _seed_session_keys(test_state)

        result = handle_gradio_input(
            user_input="I'd like a Martini",
            session_history_state=[{'role': 'user', 'content': 'Hi'}],
            current_tab=0.0, current_balance=1000.0,
            current_tip_percentage=None, current_tip_amount=0.0,
            request=_make_request(),
            tools=[], app_state=test_state
        )

        mock_get_voice_audio.assert_not_called()
        assert result[4] is None

    @patch('src.ui.handlers.create_tab_overlay_html')
    @patch('src.ui.handlers.get_current_order_state')
    def test_handle_gradio_input_no_keys(
        self, mock_get_current_order_state, mock_create_overlay
    ):
        """Test that handler rejects requests without validated keys."""
        mock_get_current_order_state.return_value = []
        mock_create_overlay.return_value = '<div>overlay</div>'

        test_state = {}  # No keys seeded

        result = handle_gradio_input(
            user_input="Hi",
            session_history_state=[],
            current_tab=0.0, current_balance=1000.0,
            current_tip_percentage=None, current_tip_amount=0.0,
            request=_make_request(),
            tools=[], app_state=test_state
        )

        assert result[0] == ""
        assert "API keys" in result[1][-1]['content']


class TestClearChatState:
    """Test cases for clear_chat_state function."""

    @patch('src.ui.handlers.reset_session_state')
    def test_clear_chat_state_success(self, mock_reset_session_state):
        """Test successful chat state clearing."""
        result = clear_chat_state(request=_make_request(), app_state={})
        mock_reset_session_state.assert_called_once()
        assert result == ([], [], [], None)

    @patch('src.ui.handlers.reset_session_state')
    def test_clear_chat_state_with_exception(self, mock_reset_session_state):
        """Test chat state clearing when reset_session_state raises exception."""
        mock_reset_session_state.side_effect = Exception("Reset failed")
        result = clear_chat_state(request=_make_request(), app_state={})
        mock_reset_session_state.assert_called_once()
        assert result == ([], [], [], None)
