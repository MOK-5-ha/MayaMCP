import pytest
import re
from unittest.mock import MagicMock, patch
from src.conversation import processor as proc
from src.llm import prompts

def test_build_order_context_empty():
    """Verify order context string builder with empty order."""
    session_id = "test_session_empty"
    app_state = {}
    
    # Empty order state
    with patch("src.conversation.processor.get_current_order_state", return_value=[]):
        context = proc._build_order_context(session_id, app_state)
        assert context == "CURRENT ORDER: Empty."

def test_build_order_context_non_empty():
    """Verify order context string builder with drinks and modifiers."""
    session_id = "test_session_drinks"
    app_state = {}
    
    order_state = [
        {"name": "Martini", "price": 13.0, "modifiers": "no modifiers", "quantity": 1},
        {"name": "Old Fashioned", "price": 12.0, "modifiers": "on the rocks", "quantity": 2}
    ]
    
    with patch("src.conversation.processor.get_current_order_state", return_value=order_state):
        context = proc._build_order_context(session_id, app_state)
        assert "1x Martini" in context
        assert "2x Old Fashioned with on the rocks" in context
        assert "CURRENT ORDER ALREADY CONTAINS:" in context
        assert "DO NOT re-add these items unless requested." in context

@patch("src.conversation.processor.call_gemini_api")
@patch("src.conversation.processor.get_all_tools")
@patch("src.conversation.processor.scan_input")
@patch("src.conversation.processor.scan_output")
def test_tip_input_bypasses_intent_detection(mock_scan_output, mock_scan_input, mock_tools, mock_call_api):
    """Verify that inputs with the word 'tip' bypass the hardcoded intent detector."""
    # Mock scanning
    mock_scan_input.return_value.is_valid = True
    mock_scan_input.return_value.sanitized_text = "close my tab and add a tip"
    mock_scan_output.return_value.is_valid = True
    mock_scan_output.return_value.sanitized_text = "processed"
    
    # Mock standard tools to avoid key errors during testing
    mock_get_bill = MagicMock()
    mock_get_bill.name = "get_bill"
    mock_pay_bill = MagicMock()
    mock_pay_bill.name = "pay_bill"
    mock_get_order = MagicMock()
    mock_get_order.name = "get_order"
    mock_tools.return_value = [mock_get_bill, mock_pay_bill, mock_get_order]
    
    # Mock LLM API call response
    mock_response = MagicMock()
    mock_response.text = "[STATE: happy] Sure, I can add a tip for you."
    mock_response.content = "[STATE: happy] Sure, I can add a tip for you."
    mock_response.tool_calls = []
    mock_call_api.return_value = mock_response
    
    # Even though "close my tab" is in the input, "tip" is also there.
    # It should not trigger the traditional intent detection bypass (which directly returns pay_bill output),
    # but instead call the Gemini API.
    proc.process_order(
        user_input_text="close my tab and add a 20% tip",
        current_session_history=[],
        llm=None,
        api_key="fake-key"
    )
    
    # Gemini API must have been called!
    mock_call_api.assert_called()

@patch("src.conversation.processor.call_gemini_api")
@patch("src.conversation.processor.get_all_tools")
@patch("src.conversation.processor.scan_input")
@patch("src.conversation.processor.scan_output")
def test_no_tip_input_triggers_intent_detection(mock_scan_output, mock_scan_input, mock_tools, mock_call_api):
    """Verify that inputs without 'tip' still trigger the fallback intent bypass."""
    mock_scan_input.return_value.is_valid = True
    mock_scan_input.return_value.sanitized_text = "close my tab"
    mock_scan_output.return_value.is_valid = True
    mock_scan_output.return_value.sanitized_text = "processed"
    
    # Mock all standard tools
    mock_get_bill = MagicMock()
    mock_get_bill.name = "get_bill"
    mock_get_bill.invoke.return_value = "Get bill output."
    mock_pay_bill = MagicMock()
    mock_pay_bill.name = "pay_bill"
    mock_pay_bill.invoke.return_value = "Closing tab."
    mock_get_order = MagicMock()
    mock_get_order.name = "get_order"
    mock_tools.return_value = [mock_get_bill, mock_pay_bill, mock_get_order]
    
    # "close my tab" matches get_bill or pay_bill, triggering the intent bypass tool invoke directly,
    # bypassing Gemini API.
    response, _, _, _, _, _ = proc.process_order(
        user_input_text="close my tab",
        current_session_history=[],
        llm=None,
        api_key="fake-key"
    )
    
    # Verify we bypass the LLM and get the tool output directly
    assert "bill" in response or "Closing" in response
    # Gemini API must NOT have been called!
    mock_call_api.assert_not_called()

def test_system_prompt_identity_preservation():
    """Verify that identity preservation instructions are present in the system prompt."""
    assert "identity as Maya the bartender" in prompts.MAYA_SYSTEM_INSTRUCTIONS
    assert "different persona" in prompts.MAYA_SYSTEM_INSTRUCTIONS
    assert "stay in character" in prompts.MAYA_SYSTEM_INSTRUCTIONS
