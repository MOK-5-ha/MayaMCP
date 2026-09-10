"""
Unit tests for determine_conversation_phase() in src/conversation/processor.py.

Covers:
- Payment phase detection (pending, processing)
- Complete phase detection (completed)
- Greeting phase detection (early conversations < 3 turns, or greeting keywords)
- Describing phase detection (recipe keywords in response)
- Ordering phase detection (order keywords in response)
- Default to greeting when conversation history < 3 turns

Requirements: 3.1, 3.2, 3.3, 3.4, 3.6
"""

import pytest

# ---------------------------------------------------------------------------
# Helper: import target under test
# ---------------------------------------------------------------------------
from src.conversation.processor import determine_conversation_phase

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def empty_state():
    """Session state with no conversation history and no payment."""
    return {"conversation_history": [], "payment": {}}


@pytest.fixture
def three_turn_state():
    """Session state with exactly 3 conversation turns (not 'early')."""
    return {
        "conversation_history": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "What do you have?"},
        ],
        "payment": {},
    }


@pytest.fixture
def five_turn_state():
    """Session state with 5 turns — well past the 'early' threshold."""
    turns = []
    for i in range(5):
        turns.append({"role": "user", "content": f"message {i}"})
        turns.append({"role": "assistant", "content": f"response {i}"})
    return {"conversation_history": turns, "payment": {}}


# ---------------------------------------------------------------------------
# Payment phase
# ---------------------------------------------------------------------------

class TestPaymentPhaseDetection:
    """Payment status drives phase, regardless of response content."""

    def test_pending_payment_returns_payment_phase(self, empty_state):
        empty_state["payment"] = {"status": "pending"}
        result = determine_conversation_phase(empty_state, "Here is your order!")
        assert result == "payment"

    def test_processing_payment_returns_payment_phase(self, empty_state):
        empty_state["payment"] = {"status": "processing"}
        result = determine_conversation_phase(empty_state, "Processing your payment now.")
        assert result == "payment"

    def test_payment_phase_overrides_greeting_keywords(self, empty_state):
        """Even if response says 'welcome', pending payment wins."""
        empty_state["payment"] = {"status": "pending"}
        result = determine_conversation_phase(empty_state, "Hello! Welcome to the bar!")
        assert result == "payment"

    def test_payment_phase_overrides_recipe_keywords(self, empty_state):
        """Even if response has 'ingredients', pending payment wins."""
        empty_state["payment"] = {"status": "pending"}
        result = determine_conversation_phase(empty_state, "This drink contains lime and tequila.")
        assert result == "payment"

    def test_payment_phase_overrides_order_keywords(self, five_turn_state):
        five_turn_state["payment"] = {"status": "processing"}
        result = determine_conversation_phase(five_turn_state, "I'll prepare that for you right away.")
        assert result == "payment"


# ---------------------------------------------------------------------------
# Complete phase
# ---------------------------------------------------------------------------

class TestCompletePhaseDetection:
    """Completed payment status maps to 'complete' phase."""

    def test_completed_payment_returns_complete_phase(self, three_turn_state):
        three_turn_state["payment"] = {"status": "completed"}
        result = determine_conversation_phase(three_turn_state, "Enjoy your drink!")
        assert result == "complete"

    def test_complete_phase_overrides_content_keywords(self, five_turn_state):
        five_turn_state["payment"] = {"status": "completed"}
        result = determine_conversation_phase(five_turn_state, "Coming right up! Here's the recipe.")
        assert result == "complete"


# ---------------------------------------------------------------------------
# Greeting phase
# ---------------------------------------------------------------------------

class TestGreetingPhaseDetection:
    """Greeting phase: response contains greeting keywords, or early conversation."""

    def test_hello_keyword_returns_greeting(self, three_turn_state):
        result = determine_conversation_phase(three_turn_state, "Hello! Welcome to the bar.")
        assert result == "greeting"

    def test_hi_keyword_returns_greeting(self, three_turn_state):
        result = determine_conversation_phase(three_turn_state, "Hi! Great to meet you.")
        assert result == "greeting"

    def test_welcome_keyword_returns_greeting(self, three_turn_state):
        result = determine_conversation_phase(three_turn_state, "Welcome to Maya's Bar!")
        assert result == "greeting"

    def test_good_to_see_you_keyword_returns_greeting(self, three_turn_state):
        result = determine_conversation_phase(three_turn_state, "Good to see you again!")
        assert result == "greeting"

    def test_early_conversation_fewer_than_3_turns_returns_greeting(self, empty_state):
        """0 turns → greeting by default (< 3 turns check)."""
        result = determine_conversation_phase(empty_state, "What would you like?")
        assert result == "greeting"

    def test_two_turns_returns_greeting_as_default(self):
        """2 turns: still early conversation, neutral response → greeting."""
        state = {
            "conversation_history": [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hey there!"},
            ],
            "payment": {},
        }
        result = determine_conversation_phase(state, "What can I get you?")
        assert result == "greeting"


# ---------------------------------------------------------------------------
# Describing phase
# ---------------------------------------------------------------------------

class TestDescribingPhaseDetection:
    """Describing phase detected by recipe-related keywords in response."""

    def test_recipe_keyword_returns_describing(self, five_turn_state):
        result = determine_conversation_phase(five_turn_state, "Here's the recipe for an Old Fashioned.")
        assert result == "describing"

    def test_ingredients_keyword_returns_describing(self, five_turn_state):
        result = determine_conversation_phase(five_turn_state, "The ingredients are bourbon, bitters, and sugar.")
        assert result == "describing"

    def test_made_with_keyword_returns_describing(self, five_turn_state):
        result = determine_conversation_phase(five_turn_state, "This cocktail is made with fresh lime juice.")
        assert result == "describing"

    def test_contains_keyword_returns_describing(self, five_turn_state):
        result = determine_conversation_phase(five_turn_state, "This drink contains triple sec and orange juice.")
        assert result == "describing"

    def test_describing_detection_is_case_insensitive(self, five_turn_state):
        result = determine_conversation_phase(five_turn_state, "It's MADE WITH premium vodka.")
        assert result == "describing"

    def test_describing_phase_priority_over_order_keyword(self, five_turn_state):
        """'ingredients' appears before 'order' in keyword priority."""
        result = determine_conversation_phase(
            five_turn_state,
            "Let me describe the ingredients before you order.",
        )
        assert result == "describing"


# ---------------------------------------------------------------------------
# Ordering phase
# ---------------------------------------------------------------------------

class TestOrderingPhaseDetection:
    """Ordering phase detected by order-completion keywords in response."""

    def test_order_keyword_returns_ordering(self, five_turn_state):
        result = determine_conversation_phase(five_turn_state, "Your order has been placed!")
        assert result == "ordering"

    def test_prepare_keyword_returns_ordering(self, five_turn_state):
        result = determine_conversation_phase(five_turn_state, "I'll prepare that cocktail for you now.")
        assert result == "ordering"

    def test_make_you_keyword_returns_ordering(self, five_turn_state):
        result = determine_conversation_phase(five_turn_state, "Let me make you a classic Negroni.")
        assert result == "ordering"

    def test_coming_right_up_keyword_returns_ordering(self, five_turn_state):
        result = determine_conversation_phase(five_turn_state, "Coming right up! One Mojito.")
        assert result == "ordering"

    def test_ordering_detection_is_case_insensitive(self, five_turn_state):
        result = determine_conversation_phase(five_turn_state, "COMING RIGHT UP, one gin and tonic!")
        assert result == "ordering"


# ---------------------------------------------------------------------------
# Default / fallback behaviour
# ---------------------------------------------------------------------------

class TestDefaultPhase:
    """When no payment status and no keyword matches, fall back to greeting for
    early conversations, and 'ordering' otherwise."""

    def test_neutral_response_with_many_turns_returns_ordering(self, five_turn_state):
        """No keyword match, >= 3 turns → ordering (final default)."""
        result = determine_conversation_phase(five_turn_state, "Sure, anything else?")
        assert result == "ordering"

    def test_neutral_response_with_zero_turns_returns_greeting(self, empty_state):
        """No keyword match, 0 turns → greeting (early conversation default)."""
        result = determine_conversation_phase(empty_state, "Sure, anything else?")
        assert result == "greeting"

    def test_missing_payment_key_treated_as_none(self):
        """State with no 'payment' key at all should not raise."""
        state = {"conversation_history": [], "payment": {}}
        result = determine_conversation_phase(state, "Anything else for you?")
        assert result == "greeting"

    def test_missing_conversation_history_key_treated_as_empty(self):
        """State dict with no 'conversation_history' key at all should not raise."""
        state = {}
        result = determine_conversation_phase(state, "What would you like?")
        assert result == "greeting"

    def test_unknown_payment_status_falls_through_to_content_check(self, five_turn_state):
        """An unrecognised payment status should NOT trigger payment/complete."""
        five_turn_state["payment"] = {"status": "unknown_status"}
        result = determine_conversation_phase(five_turn_state, "Sure, anything else?")
        # No keyword match + >=3 turns → ordering
        assert result == "ordering"
