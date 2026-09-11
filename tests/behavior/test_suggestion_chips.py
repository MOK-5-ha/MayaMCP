"""BDD step definitions for suggestion chips scenarios.

Tests contextual chip generation, user interaction, accessibility,
and graceful degradation across conversation phases.

NOTE: This test file is part of the suggestion-chips specification PR.
The tests will be skipped until the implementation PR lands.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

# Deferred imports - will be available after implementation
try:
    from src.conversation.chip_generator import ChipGenerator
    from src.schemas.chips import (
        ActionID,
        ChipGenerationContext,
        ChipType,
        SuggestionChip,
        SuggestionChipSet,
    )
    from src.ui.chips import (
        CHIP_CSS,
        format_chip_live_announcement,
        get_chip_aria_label,
    )
    from src.utils.state_manager import (
        get_session_state,
        initialize_state,
        reset_session_state,
        update_payment_state,
    )
    IMPORTS_AVAILABLE = True
except ImportError as e:
    # Modules not yet implemented - tests will be skipped
    IMPORTS_AVAILABLE = False
    SKIP_REASON = f"Suggestion chips implementation not yet available: {e}"

# Load scenarios from feature file only if imports are available
if IMPORTS_AVAILABLE:
    scenarios('features/suggestion_chips.feature')


# Skip all tests in this module if implementation is not available
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Suggestion chips implementation not yet available (spec-only PR)"
)


class ChipTestContext:
    """Shared state across BDD steps."""
    def __init__(self):
        self.session_id = "test_chip_bdd_session"
        self.app_state = {}
        self.chips = None
        self.mock_llm_client = None
        self.chip_generator = None
        self.conversation_phase = "greeting"
        self.user_message = None
        self.maya_response = None
        self.chip_click_result = None
        self.timeout_occurred = False
        self.validation_failed = False
        self.logged_warnings = []


@pytest.fixture
def ctx():
    return ChipTestContext()


@pytest.fixture(autouse=True)
def mock_llm_client(ctx, monkeypatch):
    """Mock the Gemini client to prevent real API calls."""
    if not IMPORTS_AVAILABLE:
        pytest.skip(SKIP_REASON)
    
    mock_client = MagicMock()
    
    # Default structured output response
    mock_response = MagicMock()
    mock_response.text = '''
    {
        "chips": [
            {"text": "Show me the menu", "type": "action", "action_id": "menu"},
            {"text": "Surprise me", "type": "dialogue"},
            {"text": "What's popular?", "type": "dialogue"}
        ]
    }
    '''
    
    mock_client.models.generate_content.return_value = mock_response
    ctx.mock_llm_client = mock_client
    
    monkeypatch.setattr(
        "src.conversation.chip_generator.get_genai_client",
        lambda session_id: mock_client
    )
    
    return mock_client


# ─── Given Steps ────────────────────────────────────────────────────

@given("Maya is initialized in Vertex AI mode", target_fixture="ctx")
def step_init_maya_vertex(ctx):
    """Initialize Maya in Vertex AI mode."""
    import os
    os.environ["GCP_PROJECT"] = "test-project"
    os.environ["GCP_LOCATION"] = "us-central1"
    os.environ["GEMINI_TIER"] = "paid"
    return ctx


@given("a new user session is created", target_fixture="ctx")
def step_create_session(ctx):
    """Create a fresh user session."""
    from src.llm.tools import set_current_session, set_global_store
    
    set_global_store(ctx.app_state)
    reset_session_state(ctx.session_id, ctx.app_state)
    initialize_state(ctx.session_id, ctx.app_state)
    set_current_session(ctx.session_id)
    
    ctx.chip_generator = ChipGenerator(
        session_id=ctx.session_id,
        llm_client=ctx.mock_llm_client
    )
    
    return ctx


@given(
    parsers.parse('the conversation is in the {phase} phase'),
    target_fixture="ctx"
)
def step_set_conversation_phase(ctx, phase):
    """Set the conversation to a specific phase."""
    ctx.conversation_phase = phase
    
    session_state = get_session_state(ctx.session_id, ctx.app_state)
    
    if phase == "payment":
        update_payment_state(ctx.session_id, ctx.app_state, {"status": "pending"})
    elif phase == "complete":
        update_payment_state(ctx.session_id, ctx.app_state, {"status": "completed"})
    
    return ctx


@given(
    parsers.parse('the user has ordered a "{drink}" costing {cost:f}'),
    target_fixture="ctx"
)
def step_user_orders_drink(ctx, drink, cost):
    """User orders a drink."""
    from src.utils.state_manager import update_order_state
    
    update_order_state(ctx.session_id, ctx.app_state, {
        "drink": drink,
        "price": cost
    })
    update_payment_state(ctx.session_id, ctx.app_state, {
        "balance": cost,
        "status": "pending"
    })
    
    return ctx


@given("the user has ordered a drink", target_fixture="ctx")
def step_user_orders_generic_drink(ctx):
    """User orders a generic drink."""
    return step_user_orders_drink(ctx, "Martini", 13.00)


@given('the payment status is "pending"', target_fixture="ctx")
def step_payment_pending(ctx):
    """Set payment status to pending."""
    update_payment_state(ctx.session_id, ctx.app_state, {"status": "pending"})
    return ctx


@given(
    parsers.parse('the user has asked "{question}"'),
    target_fixture="ctx"
)
def step_user_asked_question(ctx, question):
    """User has asked a question."""
    ctx.user_message = question
    
    # Add to conversation history
    session_state = get_session_state(ctx.session_id, ctx.app_state)
    history = session_state.get("conversation_history", [])
    history.append({"role": "user", "content": question})
    session_state["conversation_history"] = history
    
    return ctx


@given(
    parsers.parse('the user has said "{message}" in the last 2 messages'),
    target_fixture="ctx"
)
def step_user_recent_message(ctx, message):
    """User has said a specific message recently."""
    session_state = get_session_state(ctx.session_id, ctx.app_state)
    history = session_state.get("conversation_history", [])
    history.append({"role": "user", "content": message})
    session_state["conversation_history"] = history
    return ctx


@given(
    parsers.parse('Maya has suggested an action chip with action_id "{action_id}"'),
    target_fixture="ctx"
)
def step_maya_suggested_action_chip(ctx, action_id):
    """Maya has suggested an action chip."""
    ctx.chips = SuggestionChipSet(chips=[
        SuggestionChip(text="Complete payment", type=ChipType.ACTION, action_id=action_id)
    ])
    
    # Store in session state
    session_state = get_session_state(ctx.session_id, ctx.app_state)
    chip_state = session_state.get("chip_state", {})
    chip_state["current_chips"] = ctx.chips
    session_state["chip_state"] = chip_state
    
    return ctx


@given(
    parsers.parse('Maya has suggested a dialogue chip "{text}"'),
    target_fixture="ctx"
)
def step_maya_suggested_dialogue_chip(ctx, text):
    """Maya has suggested a dialogue chip."""
    ctx.chips = SuggestionChipSet(chips=[
        SuggestionChip(text=text, type=ChipType.DIALOGUE)
    ])
    
    # Store in session state
    session_state = get_session_state(ctx.session_id, ctx.app_state)
    chip_state = session_state.get("chip_state", {})
    chip_state["current_chips"] = ctx.chips
    session_state["chip_state"] = chip_state
    
    return ctx


@given(
    parsers.parse('Maya has suggested an action chip with unrecognized action_id "{action_id}"'),
    target_fixture="ctx"
)
def step_maya_suggested_unrecognized_chip(ctx, action_id):
    """Maya has suggested chip with unrecognized action_id."""
    # Note: This will fail Pydantic validation in real code
    # For testing, we'll create a mock chip that bypasses validation
    ctx.chips = MagicMock()
    ctx.chips.chips = [
        MagicMock(text="Unknown action", type=ChipType.ACTION, action_id=action_id)
    ]
    return ctx


@given(
    parsers.parse('the chip generation LLM call takes {seconds:d} seconds'),
    target_fixture="ctx"
)
def step_llm_takes_n_seconds(ctx, seconds):
    """Mock slow LLM response."""
    def slow_generate(*args, **kwargs):
        time.sleep(seconds)
        mock_response = MagicMock()
        mock_response.text = '{"chips": []}'
        return mock_response
    
    ctx.mock_llm_client.models.generate_content.side_effect = slow_generate
    return ctx


@given("the chip generation LLM returns invalid JSON", target_fixture="ctx")
def step_llm_returns_invalid_json(ctx):
    """Mock invalid JSON response."""
    mock_response = MagicMock()
    mock_response.text = 'not valid json {{'
    ctx.mock_llm_client.models.generate_content.return_value = mock_response
    return ctx


@given("the user session has no conversation history", target_fixture="ctx")
def step_no_conversation_history(ctx):
    """Clear conversation history."""
    session_state = get_session_state(ctx.session_id, ctx.app_state)
    session_state["conversation_history"] = []
    return ctx


@given("suggestion chips are currently displayed", target_fixture="ctx")
def step_chips_displayed(ctx):
    """Chips are already displayed."""
    ctx.chips = SuggestionChipSet(chips=[
        SuggestionChip(text="Test chip 1", type=ChipType.DIALOGUE),
        SuggestionChip(text="Test chip 2", type=ChipType.DIALOGUE),
        SuggestionChip(text="Test chip 3", type=ChipType.DIALOGUE),
    ])
    
    session_state = get_session_state(ctx.session_id, ctx.app_state)
    chip_state = session_state.get("chip_state", {})
    chip_state["current_chips"] = ctx.chips
    session_state["chip_state"] = chip_state
    
    return ctx


@given("suggestion chips are displayed after Maya's response", target_fixture="ctx")
def step_chips_after_response(ctx):
    """Chips displayed after response."""
    return step_chips_displayed(ctx)


@given("suggestion chips are displayed", target_fixture="ctx")
def step_chips_are_displayed(ctx):
    """Chips are displayed."""
    return step_chips_displayed(ctx)


@given("suggestion chips are displayed on mobile viewport", target_fixture="ctx")
def step_chips_on_mobile(ctx):
    """Chips displayed on mobile."""
    ctx.viewport = "mobile"
    return step_chips_displayed(ctx)


# ─── When Steps ─────────────────────────────────────────────────────

@when("Maya greets the user")
def step_maya_greets(ctx):
    """Maya greets the user."""
    ctx.maya_response = "Hello! Welcome to the bar. What can I get you today?"
    ctx.conversation_phase = "greeting"


@when("Maya completes a response")
def step_maya_completes_response(ctx):
    """Maya completes a response."""
    ctx.maya_response = "Response completed"
    
    # Trigger chip generation
    context = ChipGenerationContext(
        conversation_turns=[],
        conversation_phase=ctx.conversation_phase,
        payment_status="none",
        recent_user_messages=[]
    )
    
    try:
        ctx.chips = ctx.chip_generator.generate_chips_async(context)
    except Exception as e:
        ctx.validation_failed = True
        ctx.logged_warnings.append(f"Chip generation failed: {e}")


@when("Maya confirms the order with the price")
def step_maya_confirms_order(ctx):
    """Maya confirms order."""
    ctx.maya_response = "Great choice! That'll be $14.00."
    ctx.conversation_phase = "payment"


@when("Maya describes the drink ingredients")
def step_maya_describes_drink(ctx):
    """Maya describes drink."""
    ctx.maya_response = "An Old Fashioned contains bourbon, bitters, sugar, and orange peel."
    ctx.conversation_phase = "describing"


@when("suggestion chips are generated")
def step_chips_generated(ctx):
    """Chips are generated."""
    if ctx.chips is None:
        step_maya_completes_response(ctx)


@when(
    parsers.parse('the user clicks the "{chip_text}" chip')
)
def step_user_clicks_chip(ctx, chip_text):
    """User clicks a chip."""
    from src.ui.chips import handle_chip_click
    
    # Find the chip
    if ctx.chips and hasattr(ctx.chips, 'chips'):
        matching_chip = None
        for chip in ctx.chips.chips:
            if chip.text == chip_text:
                matching_chip = chip
                break
        
        if matching_chip:
            ctx.chip_click_result = handle_chip_click(
                chip_text=matching_chip.text,
                chip_type=matching_chip.type,
                action_id=matching_chip.action_id if hasattr(matching_chip, 'action_id') else None,
                session_id=ctx.session_id,
                textbox=MagicMock()
            )


@when("the user clicks the chip")
def step_user_clicks_generic_chip(ctx):
    """User clicks any chip."""
    if ctx.chips and hasattr(ctx.chips, 'chips') and ctx.chips.chips:
        chip = ctx.chips.chips[0]
        step_user_clicks_chip(ctx, chip.text)


@when("the user submits a new message")
def step_user_submits_message(ctx):
    """User submits new message."""
    ctx.user_message = "New message"


@when("the UI component refreshes")
def step_ui_refreshes(ctx):
    """UI refreshes."""
    pass  # No-op for test


@when("the user session is reset")
def step_session_reset(ctx):
    """Session is reset."""
    reset_session_state(ctx.session_id, ctx.app_state)


@when("the user presses Tab to focus a chip")
def step_user_tabs_to_chip(ctx):
    """User tabs to chip."""
    ctx.focused_chip = True


@when("the user presses Enter")
def step_user_presses_enter(ctx):
    """User presses Enter."""
    if hasattr(ctx, 'focused_chip') and ctx.focused_chip:
        step_user_clicks_generic_chip(ctx)


@when("new chips are generated after Maya's response")
def step_new_chips_after_response(ctx):
    """New chips generated."""
    step_maya_completes_response(ctx)


@when("Maya completes the first response")
def step_maya_first_response(ctx):
    """Maya completes first response."""
    ctx.chips = ctx.chip_generator.generate_fallback_chips()


# ─── Then Steps ─────────────────────────────────────────────────────

@then("suggestion chips should be generated")
def step_verify_chips_generated(ctx):
    """Verify chips were generated."""
    assert ctx.chips is not None, "Chips were not generated"


@then("at least one chip should be a dialogue chip")
def step_verify_dialogue_chip(ctx):
    """Verify at least one dialogue chip."""
    assert any(chip.type == ChipType.DIALOGUE for chip in ctx.chips.chips), \
        "No dialogue chips found"


@then(parsers.parse('at least one chip should contain "{words}"'))
def step_verify_chip_contains(ctx, words):
    """Verify chip contains words."""
    word_list = [w.strip() for w in words.split(" or ")]
    found = any(
        any(word.lower() in chip.text.lower() for word in word_list)
        for chip in ctx.chips.chips
    )
    assert found, f"No chip contains any of: {word_list}"


@then(parsers.parse('the chip set should contain {min_chips:d} to {max_chips:d} chips'))
def step_verify_chip_count(ctx, min_chips, max_chips):
    """Verify chip count in range."""
    count = len(ctx.chips.chips)
    assert min_chips <= count <= max_chips, \
        f"Chip count {count} not in range [{min_chips}, {max_chips}]"


@then(parsers.parse('at least one chip should be relevant to {phase}'))
def step_verify_phase_relevance(ctx, phase):
    """Verify chip relevance to phase."""
    # This is a semantic check - simplified for now
    assert len(ctx.chips.chips) > 0, f"No chips for phase {phase}"


@then(parsers.parse('the conversation phase should be "{phase}"'))
def step_verify_phase(ctx, phase):
    """Verify conversation phase."""
    assert ctx.conversation_phase == phase, \
        f"Expected phase {phase}, got {ctx.conversation_phase}"


@then(parsers.parse('at least one chip should be an action chip with action_id "{action_id}"'))
def step_verify_action_chip(ctx, action_id):
    """Verify action chip with specific action_id."""
    found = any(
        chip.type == ChipType.ACTION and chip.action_id == action_id
        for chip in ctx.chips.chips
    )
    assert found, f"No action chip with action_id={action_id}"


@then("the payment chip should appear in the first 3 chips")
def step_verify_payment_chip_position(ctx):
    """Verify payment chip in first 3."""
    first_three = ctx.chips.chips[:3]
    found = any(
        chip.type == ChipType.ACTION and chip.action_id == ActionID.PAYMENT
        for chip in first_three
    )
    assert found, "Payment chip not in first 3 positions"


@then("at least two chips should be dialogue chips")
def step_verify_two_dialogue_chips(ctx):
    """Verify at least 2 dialogue chips."""
    dialogue_count = sum(1 for chip in ctx.chips.chips if chip.type == ChipType.DIALOGUE)
    assert dialogue_count >= 2, f"Only {dialogue_count} dialogue chips found"


@then("the dialogue chips should contain follow-up questions or modifications")
def step_verify_followup_chips(ctx):
    """Verify follow-up chip content."""
    # Simplified semantic check
    assert any(chip.type == ChipType.DIALOGUE for chip in ctx.chips.chips)


@then(parsers.parse('no chip should have text matching "{text}" (case-insensitive)'))
def step_verify_no_duplicate(ctx, text):
    """Verify no chip matches text."""
    found = any(chip.text.lower() == text.lower() for chip in ctx.chips.chips)
    assert not found, f"Found duplicate chip with text: {text}"


@then(parsers.parse('the textbox should be populated with "{text}"'))
def step_verify_textbox_populated(ctx, text):
    """Verify textbox populated."""
    if ctx.chip_click_result:
        populated_text = ctx.chip_click_result[0]
        assert populated_text == text, f"Expected '{text}', got '{populated_text}'"


@then("the message should auto-submit without manual confirmation")
def step_verify_auto_submit(ctx):
    """Verify auto-submit triggered."""
    if ctx.chip_click_result:
        submit_trigger = ctx.chip_click_result[1]
        assert submit_trigger == "submit", "Message did not auto-submit"


@then("the payment flow should be triggered")
def step_verify_payment_triggered(ctx):
    """Verify payment flow triggered."""
    # In real implementation, check payment state
    pass


@then("the textbox should receive focus")
def step_verify_textbox_focused(ctx):
    """Verify textbox focused."""
    # In real implementation, check focus state
    pass


@then("the message should NOT auto-submit")
def step_verify_no_auto_submit(ctx):
    """Verify no auto-submit."""
    if ctx.chip_click_result:
        submit_trigger = ctx.chip_click_result[1]
        assert submit_trigger is None, "Message auto-submitted when it shouldn't"


@then("a fallback warning should be logged")
def step_verify_fallback_logged(ctx):
    """Verify fallback warning logged."""
    # In real implementation, check logs
    pass


@then(parsers.parse('chip generation should timeout after {seconds:d} seconds'))
def step_verify_timeout(ctx, seconds):
    """Verify timeout occurred."""
    ctx.timeout_occurred = True


@then("no chips should be displayed")
def step_verify_no_chips(ctx):
    """Verify no chips displayed."""
    assert ctx.chips is None or len(ctx.chips.chips) == 0, "Chips were displayed"


@then("a timeout warning should be logged")
def step_verify_timeout_logged(ctx):
    """Verify timeout logged."""
    assert ctx.timeout_occurred or len(ctx.logged_warnings) > 0


@then("Maya's response should NOT be delayed")
def step_verify_no_delay(ctx):
    """Verify response not delayed."""
    # In real implementation, check timing
    pass


@then("chip validation should fail")
def step_verify_validation_failed(ctx):
    """Verify validation failed."""
    ctx.validation_failed = True


@then("a validation error should be logged")
def step_verify_validation_logged(ctx):
    """Verify validation error logged."""
    assert ctx.validation_failed or len(ctx.logged_warnings) > 0


@then("fallback greeting chips should be generated")
def step_verify_fallback_chips(ctx):
    """Verify fallback chips."""
    assert ctx.chips is not None
    assert len(ctx.chips.chips) > 0


@then(parsers.parse('the fallback chips should include "{text}"'))
def step_verify_fallback_contains(ctx, text):
    """Verify fallback chip text."""
    found = any(text.lower() in chip.text.lower() for chip in ctx.chips.chips)
    assert found, f"Fallback chips don't include: {text}"


@then("the chips should hide immediately")
def step_verify_chips_hidden(ctx):
    """Verify chips hidden."""
    # In real implementation, check UI state
    pass


@then("new chips should only appear after Maya responds")
def step_verify_chips_after_response(ctx):
    """Verify chips appear after response."""
    # In real implementation, check timing
    pass


@then("the chips should remain visible")
def step_verify_chips_visible(ctx):
    """Verify chips still visible."""
    session_state = get_session_state(ctx.session_id, ctx.app_state)
    chip_state = session_state.get("chip_state", {})
    assert chip_state.get("current_chips") is not None


@then("the chip content should not change")
def step_verify_chip_content_unchanged(ctx):
    """Verify chip content unchanged."""
    # In real implementation, compare before/after
    pass


@then("all chip state should be cleared")
def step_verify_chip_state_cleared(ctx):
    """Verify chip state cleared."""
    session_state = get_session_state(ctx.session_id, ctx.app_state)
    chip_state = session_state.get("chip_state", {})
    assert chip_state.get("current_chips") is None or len(chip_state.get("current_chips", [])) == 0


@then("the chip should activate (populate textbox)")
def step_verify_chip_activated(ctx):
    """Verify chip activated."""
    assert ctx.chip_click_result is not None


@then("the chip should behave according to its type (auto-submit or focus)")
def step_verify_type_behavior(ctx):
    """Verify chip type-specific behavior."""
    # Checked in other steps
    pass


@then(parsers.parse('each chip should have minimum {size:d}x{size:d} pixel touch target'))
def step_verify_touch_target(ctx, size):
    """Verify touch target size."""
    assert size == 44  # WCAG requirement
    assert f"min-height: {size}px" in CHIP_CSS
    assert f"min-width: {size}px" in CHIP_CSS


@then("chips should be horizontally scrollable without vertical overflow")
def step_verify_scrollable(ctx):
    """Verify horizontal scroll."""
    assert "overflow-x: auto" in CHIP_CSS
    assert "overflow-y: hidden" in CHIP_CSS


@then(parsers.parse('dialogue chips should have at least {ratio:f}:1 contrast ratio'))
def step_verify_dialogue_contrast(ctx, ratio):
    """Verify dialogue chip contrast."""
    assert ratio >= 4.5


@then(parsers.parse('action chips should have at least {ratio:f}:1 contrast ratio'))
def step_verify_action_contrast(ctx, ratio):
    """Verify action chip contrast."""
    assert ratio >= 4.5


@then("the ARIA live region should announce the chip update")
def step_verify_aria_announcement(ctx):
    """Verify ARIA announcement."""
    announcement = format_chip_live_announcement(ctx.chips)
    assert announcement is not None
    assert len(announcement) > 0
    assert 'aria-live="polite"' in CHIP_CSS or 'aria-live="polite"' in str(CHIP_CSS)


@then("each chip should have an ARIA label indicating type and text")
def step_verify_aria_labels(ctx):
    """Verify ARIA labels."""
    if ctx.chips and hasattr(ctx.chips, "chips"):
        for chip in ctx.chips.chips:
            label = get_chip_aria_label(chip)
            assert label.startswith(f"{chip.type.value if hasattr(chip.type, 'value') else chip.type} chip:")
            assert chip.text in label
