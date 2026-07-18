import os
import pytest
from unittest.mock import MagicMock, patch
from src.config.logging_config import should_log_sensitive
from src.conversation.processor import process_order

def test_should_log_sensitive():
    with patch.dict(os.environ, {"LOG_SENSITIVE_RESPONSES": "true"}):
        assert should_log_sensitive() is True
    
    with patch.dict(os.environ, {"LOG_SENSITIVE_RESPONSES": "false"}):
        assert should_log_sensitive() is False
        
    # Targeted unset of LOG_SENSITIVE_RESPONSES
    with patch.dict(os.environ, {}, clear=True):
        assert should_log_sensitive() is False

    # Edge cases
    with patch.dict(os.environ, {"LOG_SENSITIVE_RESPONSES": "TRUE"}):
        assert should_log_sensitive() is True
        
    with patch.dict(os.environ, {"LOG_SENSITIVE_RESPONSES": "1"}):
        assert should_log_sensitive() is False
        
    with patch.dict(os.environ, {"LOG_SENSITIVE_RESPONSES": "not_a_bool"}):
        assert should_log_sensitive() is False

from google.adk.models import Gemini
from google.adk.models.llm_response import LlmResponse
from google.genai import types

class DummyLLM(Gemini):
    def __init__(self, should_call_tool=False, **kwargs):
        super().__init__(model="gemini-2.5-flash", **kwargs)
        self._should_call_tool = should_call_tool
        self._call_count = 0
        
    async def generate_content_async(self, request, stream=False):
        class MockCandidate:
            def __init__(self, text=None, function_calls=None):
                self.finish_reason = types.FinishReason.STOP
                self.finish_message = ""
                parts = []
                if text:
                    parts.append(types.Part.from_text(text=text))
                if function_calls:
                    for fc in function_calls:
                        parts.append(types.Part.from_function_call(name=fc["name"], args=fc["args"]))
                self.content = types.Content(role="model", parts=parts)
            def __getattr__(self, name):
                return None

        class MockResponse:
            def __init__(self, text=None, function_calls=None):
                self.candidates = [MockCandidate(text, function_calls)]
                from types import SimpleNamespace as NS
                self.usage_metadata = NS(prompt_token_count=10, candidates_token_count=10, total_token_count=20)
                self.grounding_metadata = None
                self.citation_metadata = None
            def __getattr__(self, name):
                return None

        self._call_count += 1
        if self._should_call_tool and self._call_count == 1:
            yield LlmResponse.create(MockResponse(function_calls=[{"name": "get_menu", "args": {}}]))
        else:
            yield LlmResponse.create(MockResponse(text="Final response"))


@patch("src.llm.tools.logger")
@patch("src.conversation.processor.get_all_tools")
@patch("src.conversation.processor.should_log_sensitive")
@patch("src.conversation.processor.logger")
def test_processor_logging_gated(mock_logger, mock_should_log, mock_get_tools, mock_tools_logger):
    # Setup mocks
    mock_should_log.return_value = False
    mock_get_tools.return_value = []
    llm = DummyLLM(should_call_tool=False)
    
    # Run processor
    process_order(
        user_input_text="hello",
        current_session_history=[],
        llm=llm
    )
    
    # Verify sensitive logs were NOT called
    for call in mock_logger.debug.call_args_list + mock_tools_logger.debug.call_args_list:
        msg = call[0][0]
        assert "Original response" not in msg
        assert "RAG-enhanced response" not in msg
        assert "LLM requested tool calls" not in msg
        assert "Executed tool" not in msg

    # Enable sensitive log
    mock_logger.debug.reset_mock()
    mock_tools_logger.debug.reset_mock()
    mock_should_log.return_value = True
    
    with patch.dict(os.environ, {"LOG_SENSITIVE_RESPONSES": "true"}):
        # Configure LLM to return a tool call followed by a final response
        llm = DummyLLM(should_call_tool=True)
        
        # Use the real get_menu function
        from src.llm.tools import get_menu
        mock_get_tools.return_value = [get_menu]
        
        process_order(
            user_input_text="hello",
            current_session_history=[],
            llm=llm
        )
        
        # Verify sensitive logs WERE called in debug
        debug_messages = [call[0][0] for call in mock_logger.debug.call_args_list] + \
                         [call[0][0] for call in mock_tools_logger.debug.call_args_list]
        assert any("Executed tool" in m for m in debug_messages)
