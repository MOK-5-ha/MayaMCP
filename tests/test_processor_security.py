import pytest
from unittest.mock import MagicMock, patch
from src.conversation import processor as proc
from langchain_core.messages import AIMessage

class DummyLLM:
    def __init__(self, content="base response"):
        self._content = content
    def invoke(self, messages):
        return AIMessage(content=self._content)

@pytest.fixture
def mock_security():
    with patch("src.conversation.processor.scan_input") as mock_input, \
         patch("src.conversation.processor.scan_output") as mock_output:
        
        # Default valid
        mock_input.return_value.is_valid = True
        mock_input.return_value.sanitized_text = "valid input"
        
        mock_output.return_value.is_valid = True
        mock_output.return_value.sanitized_text = "valid output"
        
        yield mock_input, mock_output

def test_processor_blocks_injection(mock_security):
    mock_input, mock_output = mock_security
    
    # Setup injection blocking
    mock_input.return_value.is_valid = False
    mock_input.return_value.blocked_reason = "Blocked!"
    
    llm = DummyLLM("should not see this")
    response, _, _, _, _, _ = proc.process_order(
        user_input_text="injection",
        current_session_history=[],
        llm=llm
    )
    
    assert response == "Blocked!"
    mock_input.assert_called_with("injection")

def test_processor_replaces_toxic_output(mock_security):
    mock_input, mock_output = mock_security
    
    # Input valid
    mock_input.return_value.is_valid = True
    
    # Output toxic
    mock_output.return_value.is_valid = False
    mock_output.return_value.sanitized_text = "Restricted content."
    
    llm = DummyLLM("toxic response")
    
    response, _, _, _, _, _ = proc.process_order(
        user_input_text="hello",
        current_session_history=[],
        llm=llm
    )
    
    assert response == "Restricted content."
    mock_output.assert_called()
    # Check that called with original response
    args, _ = mock_output.call_args
    assert args[0] == "toxic response"

def test_processor_allows_valid_interaction(mock_security):
    mock_input, mock_output = mock_security
    
    llm = DummyLLM("ok response")
    
    response, _, _, _, _, _ = proc.process_order(
        user_input_text="hello",
        current_session_history=[],
        llm=llm
    )
    
    assert response == "ok response"
    mock_input.assert_called()
    mock_output.assert_called()
