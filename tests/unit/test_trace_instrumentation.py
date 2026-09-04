"""Unit tests for OpenTelemetry GenAI semantic span instrumentation across LLM client and processor."""

from unittest.mock import MagicMock, patch

import pytest

from src.conversation.processor import process_order, process_order_stream
from src.llm.client import call_gemini_api, stream_gemini_api


class TestLLMClientTraceInstrumentation:
    """Test trace instrumentation in LLM client sync and streaming calls."""

    @patch("src.llm.client.get_genai_client")
    @patch("src.llm.client.get_model_name")
    @patch("src.llm.client.build_generate_config")
    @patch("src.llm.client.get_tracer")
    def test_call_gemini_api_creates_span_with_attributes(
        self, mock_get_tracer, mock_build_config, mock_get_model_name, mock_get_client
    ):
        """Test call_gemini_api creates llm.generate_content span with GenAI attributes."""
        mock_get_model_name.return_value = "gemini-3.5-flash-lite"
        mock_config = MagicMock()
        mock_config.temperature = 0.8
        mock_config.max_output_tokens = 2048
        mock_build_config.return_value = mock_config

        mock_candidate = MagicMock()
        mock_candidate.finish_reason.name = "STOP"
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]
        mock_response.usage_metadata.prompt_token_count = 120
        mock_response.usage_metadata.candidates_token_count = 60

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        prompt_content = [{"role": "user", "content": "Hello Maya"}]
        config = {"temperature": 0.8, "max_output_tokens": 2048}

        res = call_gemini_api(prompt_content, config)

        assert res is mock_response
        mock_tracer.start_as_current_span.assert_called_once_with("llm.generate_content")
        mock_span.set_attribute.assert_any_call("gen_ai.system", "gemini")
        mock_span.set_attribute.assert_any_call("gen_ai.request.model", "gemini-3.5-flash-lite")
        mock_span.set_attribute.assert_any_call("gen_ai.request.temperature", 0.8)
        mock_span.set_attribute.assert_any_call("gen_ai.request.max_tokens", 2048)
        mock_span.set_attribute.assert_any_call("gen_ai.usage.input_tokens", 120)
        mock_span.set_attribute.assert_any_call("gen_ai.usage.output_tokens", 60)
        mock_span.set_attribute.assert_any_call("gen_ai.response.finish_reasons", ["STOP"])

    @patch("src.llm.client.get_genai_client")
    @patch("src.llm.client.get_model_name")
    @patch("src.llm.client.build_generate_config")
    @patch("src.llm.client.get_tracer")
    def test_stream_gemini_api_creates_span_with_attributes(
        self, mock_get_tracer, mock_build_config, mock_get_model_name, mock_get_client
    ):
        """Test stream_gemini_api creates llm.generate_content_stream span with GenAI attributes."""
        mock_get_model_name.return_value = "gemini-3.5-flash-lite"
        mock_config = MagicMock()
        mock_config.temperature = 0.5
        mock_config.max_output_tokens = 1024
        mock_build_config.return_value = mock_config

        chunk1 = MagicMock()
        chunk1.candidates = []
        chunk1.usage_metadata = None

        chunk2 = MagicMock()
        mock_candidate = MagicMock()
        mock_candidate.finish_reason.name = "STOP"
        chunk2.candidates = [mock_candidate]
        chunk2.usage_metadata.prompt_token_count = 80
        chunk2.usage_metadata.candidates_token_count = 40

        mock_client = MagicMock()
        mock_client.models.generate_content_stream.return_value = iter([chunk1, chunk2])
        mock_get_client.return_value = mock_client

        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        prompt_content = [{"role": "user", "content": "Stream drink recipes"}]
        config = {"temperature": 0.5, "max_output_tokens": 1024}

        chunks = list(stream_gemini_api(prompt_content, config))

        assert len(chunks) == 2
        mock_tracer.start_as_current_span.assert_called_once_with("llm.generate_content_stream")
        mock_span.set_attribute.assert_any_call("gen_ai.system", "gemini")
        mock_span.set_attribute.assert_any_call("gen_ai.request.model", "gemini-3.5-flash-lite")
        mock_span.set_attribute.assert_any_call("gen_ai.usage.input_tokens", 80)
        mock_span.set_attribute.assert_any_call("gen_ai.usage.output_tokens", 40)
        mock_span.set_attribute.assert_any_call("gen_ai.response.finish_reasons", ["STOP"])


class TestProcessorTraceInstrumentation:
    """Test trace instrumentation and context propagation in conversation processor."""

    @patch("src.conversation.processor.get_tracer")
    def test_process_order_creates_chat_turn_span(self, mock_get_tracer):
        """Test process_order instruments turn with chat.turn span and session attributes."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        mock_llm = MagicMock()
        app_state = {}

        # User asks for menu or simple order inquiry
        resp, history, _, order, _ = process_order(
            user_input_text="Show me the menu",
            current_session_history=[],
            llm=mock_llm,
            session_id="session-trace-test",
            app_state=app_state,
        )

        assert resp is not None
        mock_tracer.start_as_current_span.assert_called_once_with("chat.turn")
        mock_span.set_attribute.assert_any_call("gen_ai.system", "gemini")
        mock_span.set_attribute.assert_any_call("session.id", "session-trace-test")
        mock_span.set_attribute.assert_any_call("bartender.phase", "greeting")

    @patch("src.conversation.processor.get_tracer")
    def test_process_order_stream_creates_chat_turn_stream_span(self, mock_get_tracer):
        """Test process_order_stream instruments turn with chat.turn.stream span and session attributes."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        mock_llm = MagicMock()
        app_state = {}

        # Trigger stream with empty/blocked input or quick response
        events = list(process_order_stream(
            user_input_text="Hello",
            current_session_history=[],
            llm=mock_llm,
            session_id="session-stream-trace",
            app_state=app_state,
        ))

        assert events is not None
        mock_tracer.start_as_current_span.assert_called_once_with("chat.turn.stream")
        mock_span.set_attribute.assert_any_call("gen_ai.system", "gemini")
        mock_span.set_attribute.assert_any_call("session.id", "session-stream-trace")
        mock_span.set_attribute.assert_any_call("bartender.phase", "greeting")

    @patch("src.conversation.processor.otel_context")
    @patch("src.conversation.processor.get_tracer")
    def test_process_order_propagates_otel_context_to_thread(self, mock_get_tracer, mock_otel_context):
        """Test process_order propagates active OpenTelemetry context across thread boundary."""
        mock_span = MagicMock()
        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        fake_ctx = MagicMock()
        mock_otel_context.get_current.return_value = fake_ctx

        mock_llm = MagicMock()
        app_state = {}

        resp, _, _, _, _ = process_order(
            user_input_text="Show me the menu",
            current_session_history=[],
            llm=mock_llm,
            session_id="session-ctx-prop",
            app_state=app_state,
        )

        assert resp is not None
        mock_otel_context.get_current.assert_called()
