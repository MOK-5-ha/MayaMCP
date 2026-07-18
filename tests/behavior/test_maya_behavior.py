import re
from typing import Dict, Any, List
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from types import SimpleNamespace as NS

from src.conversation.processor import process_order
from src.utils.state_manager import (
    get_payment_state,
    reset_session_state,
    get_current_order_state,
    initialize_state,
    update_payment_state,
    update_order_state
)

# Load scenarios from feature file
scenarios('features/maya_agent.feature')

# Shared test state
class BehaviorTestContext:
    def __init__(self):
        self.session_id = "test_bdd_session"
        self.app_state = {}
        self.response = ""
        self.history = []
        self.order = []
        self.emotion = "neutral"

@pytest.fixture
def ctx():
    return BehaviorTestContext()

class MockEvent:
    def __init__(self, author, text, partial=False):
        from google.genai import types
        self.author = author
        self.partial = partial
        self.content = types.Content(role=author, parts=[types.Part.from_text(text=text)])
    
    def is_final_response(self):
        return not self.partial

@pytest.fixture(autouse=True)
def mock_external_apis(monkeypatch):
    from google.adk.runners import Runner
    
    async def mock_run_async(self, user_id, session_id, new_message, **kwargs):
        from src.llm.tools import set_current_session
        set_current_session(session_id)
        
        # Extract prompt text
        prompt_text = "".join(p.text for p in new_message.parts if p.text)
        
        # Tools are on self.agent.tools
        tools = self.agent.tools
        tool_map = {getattr(t, "__name__", getattr(t, "name", None)): t for t in tools}
        
        if "stressful" in prompt_text or "stress" in prompt_text:
            text = "Man, that sounds tough. [EMOTION: neutral] I'm here to listen."
            yield MockEvent(author="model", text=text)
        elif "tip" in prompt_text:
            if "add_tip" in tool_map:
                tool_output = tool_map["add_tip"](percentage=20)
            else:
                tool_output = tool_map["set_tip"](percentage=20)
            yield MockEvent(author="model", text=str(tool_output))
        elif "martini" in prompt_text.lower():
            if "add_to_order" in tool_map:
                # The BDD tests configure balance, and add_to_order will check it
                tool_output = tool_map["add_to_order"](item_name="Martini", quantity=1)
            else:
                tool_output = "Error: add_to_order not found"
            
            yield MockEvent(author="model", text=str(tool_output))
        else:
            yield MockEvent(author="model", text="Here you go. [EMOTION: happy]")

    monkeypatch.setattr(Runner, 'run_async', mock_run_async)
    
    # Mock TTS
    monkeypatch.setattr('src.ui.handlers.get_session_tts', lambda *args, **kwargs: None)



@given(parsers.parse("the session is initialized with a balance of {balance:f}"))
def step_init_session(ctx, balance):
    ctx.app_state = {}
    from src.llm.tools import set_global_store
    set_global_store(ctx.app_state)
    reset_session_state(ctx.session_id, ctx.app_state)
    initialize_state(ctx.session_id, ctx.app_state)
    
    # Override balance in payment state
    update_payment_state(ctx.session_id, ctx.app_state, {"balance": balance})

@given(parsers.parse("the current order contains \"{item}\""))
def step_order_contains(ctx, item):
    # Add item to state manually
    # Prices: Martini is 13.00
    price = 13.00 if item.lower() == "martini" else 10.00
    update_order_state(ctx.session_id, ctx.app_state, "add_item", {
        "name": item,
        "price": price,
        "modifiers": "no modifiers",
        "quantity": 1
    })
    # also update tab total
    payment = get_payment_state(ctx.session_id, ctx.app_state)
    update_payment_state(ctx.session_id, ctx.app_state, {
        "tab_total": payment["tab_total"] + price,
        "balance": payment["balance"] - price
    })

@when(parsers.parse("the user says \"{message}\""))
def step_user_says(ctx, message):
    from google.adk.models import Gemini
    res = process_order(
        user_input_text=message,
        current_session_history=ctx.history,
        llm=Gemini(model="gemini-2.5-flash"),
        rag_retriever=None,
        api_key="mock_key",
        session_id=ctx.session_id,
        app_state=ctx.app_state
    )
    ctx.response, ctx.history, _, ctx.order, _, ctx.emotion = res

@then("Maya should respond empathetically")
def step_respond_empathetically(ctx):
    assert len(ctx.response) > 0
    # Empathetic check (rough)
    assert any(word in ctx.response.lower() for word in ["sorry", "tough", "listen", "empathy", "bartender", "stressful", "hear"])

@then(parsers.parse("Maya's emotional state should be \"{emotion1}\" or \"{emotion2}\""))
def step_check_emotion(ctx, emotion1, emotion2):
    assert ctx.emotion in [emotion1, emotion2]

@then(parsers.parse("Maya should call the order tool for \"{item}\""))
def step_call_order_tool(ctx, item):
    # Since we use intent matching for "I'll have a martini", it directly adds it
    assert any(i["name"].lower() == item.lower() for i in ctx.order)

@then(parsers.parse("the item \"{item}\" should be in the current order"))
def step_item_in_order(ctx, item):
    assert any(i["name"].lower() == item.lower() for i in ctx.order)

@then(parsers.parse("the customer tab should be {tab:f}"))
def step_check_tab(ctx, tab):
    payment = get_payment_state(ctx.session_id, ctx.app_state)
    assert abs(payment["tab_total"] - tab) < 0.01

@then(parsers.parse("the customer balance should be {balance:f}"))
def step_check_balance(ctx, balance):
    payment = get_payment_state(ctx.session_id, ctx.app_state)
    assert abs(payment["balance"] - balance) < 0.01

@then("Maya should inform the user of insufficient funds")
def step_insufficient_funds(ctx):
    assert "insufficient" in ctx.response.lower() or "funds" in ctx.response.lower() or "balance" in ctx.response.lower() or "not enough" in ctx.response.lower()

@then("the current order should be empty")
def step_order_empty(ctx):
    assert len(ctx.order) == 0

@then(parsers.parse("Maya should set the tip percentage to {percentage:d}"))
def step_set_tip(ctx, percentage):
    payment = get_payment_state(ctx.session_id, ctx.app_state)
    assert payment["tip_percentage"] == percentage

@then(parsers.parse("the tip amount should be {amount:f}"))
def step_check_tip_amount(ctx, amount):
    payment = get_payment_state(ctx.session_id, ctx.app_state)
    assert abs(payment["tip_amount"] - amount) < 0.01

@then(parsers.parse("the final total should be {total:f}"))
def step_check_final_total(ctx, total):
    payment = get_payment_state(ctx.session_id, ctx.app_state)
    from src.utils.state_manager import get_payment_total
    actual_total = get_payment_total(ctx.session_id, ctx.app_state)
    assert abs(actual_total - total) < 0.01
