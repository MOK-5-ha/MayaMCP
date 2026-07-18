import pytest
from unittest.mock import MagicMock, patch
from src.conversation import processor as proc
class DummyResponse:
    def __init__(self, text):
        self.text = text
        self.content = text
        self.tool_calls = []

from google.adk.models import Gemini
from google.adk.models.llm_response import LlmResponse
from google.genai import types

class DummyLLM(Gemini):
    def __init__(self, content="base response", **kwargs):
        super().__init__(model="gemini-2.5-flash", **kwargs)
        self._content = content
        
    async def generate_content_async(self, request, stream=False):
        class MockCandidate:
            def __init__(self, text):
                self.finish_reason = types.FinishReason.STOP
                self.finish_message = ""
                self.content = types.Content(role="model", parts=[types.Part.from_text(text=text)])
            def __getattr__(self, name):
                return None

        class MockResponse:
            def __init__(self, text):
                self.candidates = [MockCandidate(text)]
                from types import SimpleNamespace as NS
                self.usage_metadata = NS(prompt_token_count=10, candidates_token_count=10, total_token_count=20)
                self.grounding_metadata = None
                self.citation_metadata = None
            def __getattr__(self, name):
                return None

        yield LlmResponse.create(MockResponse(self._content))

@pytest.fixture
def mock_security():
    with patch("src.conversation.processor.scan_input") as mock_input, \
         patch("src.conversation.processor.scan_output") as mock_output, \
         patch("src.conversation.processor.check_rate_limits") as mock_rate_limit:
        
        # Default valid
        mock_input.return_value.is_valid = True
        mock_input.return_value.sanitized_text = "valid input"
        
        mock_output.return_value.is_valid = True
        mock_output.return_value.sanitized_text = "valid output"
        
        mock_rate_limit.return_value = (True, "")
        
        yield mock_input, mock_output

def test_processor_blocks_injection(mock_security):
    mock_input, mock_output = mock_security
    
    # Setup injection blocking
    mock_input.return_value.is_valid = False
    mock_input.return_value.blocked_reason = "Blocked!"
    
    llm = DummyLLM("should not see this")
    response, _, _, _, _ = proc.process_order(
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
    
    response, _, _, _, _ = proc.process_order(
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
    
    response, _, _, _, _ = proc.process_order(
        user_input_text="hello",
        current_session_history=[],
        llm=llm
    )
    
    assert response == "ok response"
    mock_input.assert_called()
    mock_output.assert_called()
