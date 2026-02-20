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
        
    with patch.dict(os.environ, {}, clear=True):
        assert should_log_sensitive() is False

@patch("src.conversation.processor.get_all_tools")
@patch("src.conversation.processor.should_log_sensitive")
@patch("src.conversation.processor.logger")
def test_processor_logging_gated(mock_logger, mock_should_log, mock_get_tools):
    # Setup mocks
    mock_should_log.return_value = False
    mock_get_tools.return_value = []
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content="test response", tool_calls=[])
    
    # Run processor
    process_order(
        user_input_text="hello",
        current_session_history=[],
        llm=llm
    )
    
    # Verify sensitive logs were NOT called
    for call in mock_logger.debug.call_args_list:
        msg = call[0][0]
        assert "Original response" not in msg
        assert "RAG-enhanced response" not in msg
        assert "LLM requested tool calls" not in msg

    # Enable sensitive log
    mock_should_log.return_value = True
    
    # Configure LLM to return a tool call followed by a final response to prevent infinite loop
    llm.invoke.side_effect = [
        MagicMock(content="", tool_calls=[{"name": "get_menu", "args": {}, "id": "1"}]),
        MagicMock(content="Final response", tool_calls=[])
    ]
    
    process_order(
        user_input_text="hello",
        current_session_history=[],
        llm=llm
    )
    
    # Verify sensitive logs WERE called in debug
    debug_messages = [call[0][0] for call in mock_logger.debug.call_args_list]
    assert any("LLM requested tool calls" in m for m in debug_messages)
