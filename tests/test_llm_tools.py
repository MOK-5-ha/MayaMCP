"""Unit tests for LLM tools."""

from unittest.mock import Mock, patch, MagicMock
from typing import Optional
import pytest
from src.llm.tools import (
    get_menu, get_recommendation, add_to_order, get_order, confirm_order,
    place_order, clear_order, get_bill, pay_bill, add_tip, get_all_tools
)


def assert_contains_any(result: str, phrases: list[str], msg: Optional[str] = None) -> None:
    """Assert that result contains at least one of the given phrases.
    
    This helper reduces test brittleness by allowing alternative phrasings
    for descriptive text while still enforcing semantic requirements.
    
    Args:
        result: The string to search in
        phrases: List of alternative phrases, any one of which should match
        msg: Optional custom error message
    """
    if not any(phrase in result for phrase in phrases):
        error_msg = msg or f"Expected one of {phrases} in result, got: {result[:200]}..."
        raise AssertionError(error_msg)


class TestGetMenu:
    """Test cases for get_menu function."""

    def test_get_menu_returns_expected_menu_string(self):
        """Test that get_menu returns the expected menu content."""
        menu = get_menu.invoke({})

        # Verify menu contains expected sections
        assert "MENU:" in menu
        assert "Cocktails with Liquor:" in menu
        assert "Beer:" in menu
        assert "Spirits" in menu
        assert "Non-Alcoholic Beverages:" in menu
        assert "Modifiers:" in menu
        assert "Drink Term Explanations:" in menu
        assert "Preference Guide:" in menu

        # Verify some specific items are present
        assert "Daiquiri - $10.00" in menu
        assert "Martini - $13.00" in menu
        assert "Tap Beer - $5.00" in menu
        assert "Water - $1.00" in menu

        # Verify modifiers are listed
        assert "neat" in menu
        assert "on the rocks" in menu
        assert "shaken" in menu
        assert "stirred" in menu


class TestGetRecommendation:
    """Test cases for get_recommendation function."""

    def test_get_recommendation_sobering(self):
        """Test recommendation for sobering drinks."""
        result = get_recommendation.invoke({"preference": "sobering"})
        # Flexible check for descriptive phrasing
        assert_contains_any(result, ["non-alcoholic", "sober", "hydrat"])
        # Strict checks for recommended drink names
        assert "Water" in result
        assert "Iced Tea" in result

    def test_get_recommendation_classy(self):
        """Test recommendation for classy drinks."""
        result = get_recommendation.invoke({"preference": "classy"})
        # Flexible check for descriptive phrasing
        assert_contains_any(result, ["sophisticated", "classic", "elegant", "refined"])
        # Strict checks for recommended drink names
        assert "Martini" in result
        assert "Old Fashioned" in result

    def test_get_recommendation_fruity(self):
        """Test recommendation for fruity drinks."""
        result = get_recommendation.invoke({"preference": "fruity"})
        # Flexible check for descriptive phrasing
        assert_contains_any(result, ["fruit", "refreshing", "tropical", "sweet"])
        # Strict checks for recommended drink names
        assert "Daiquiri" in result
        assert "Cosmopolitan" in result

    def test_get_recommendation_strong(self):
        """Test recommendation for strong drinks."""
        result = get_recommendation.invoke({"preference": "strong"})
        # Flexible check for descriptive phrasing
        assert_contains_any(result, ["alcohol", "strong", "potent", "spirit"])
        # Strict checks for recommended drink names
        assert "Long Island" in result
        assert "Old Fashioned" in result

    def test_get_recommendation_burning(self):
        """Test recommendation for burning drinks."""
        result = get_recommendation.invoke({"preference": "burning"})
        # Flexible check for descriptive phrasing
        assert_contains_any(result, ["burn", "neat", "straight", "pure"])
        # Strict checks for recommended drink names
        assert "Whiskey (neat)" in result
        assert "Tequila (neat)" in result

    def test_get_recommendation_case_insensitive(self):
        """Test that preference matching is case insensitive."""
        result1 = get_recommendation.invoke({"preference": "SOBERING"})
        result2 = get_recommendation.invoke({"preference": "sobering"})
        assert result1 == result2

    def test_get_recommendation_unknown_preference(self):
        """Test recommendation for unknown preference."""
        result = get_recommendation.invoke({"preference": "unknown_preference"})
        # Flexible check for descriptive phrasing
        assert_contains_any(result, ["not familiar", "don't recognize", "unknown", "try"])
        assert_contains_any(result, ["popular", "recommend", "suggest", "favorite"])
        # Strict check for recommended drink name
        assert "Martini" in result


class TestAddToOrder:
    """Test cases for add_to_order function."""

    @patch('src.llm.tools.get_menu')
    @patch('src.llm.tools.update_order_state')
    def test_add_to_order_successful(self, mock_update_order_state, mock_get_menu):
        """Test successful item addition to order."""
        # Setup mocks
        mock_get_menu.invoke.return_value = """
        MENU:
        Martini - $13.00
        Daiquiri - $10.00
        """

        # Execute function using invoke
        result = add_to_order.invoke({"item_name": "Martini", "modifiers": ["shaken"], "quantity": 1})

        # Verify get_menu was called
        mock_get_menu.invoke.assert_called_once()

        # Verify update_order_state was called
        mock_update_order_state.assert_called_once()
        call_args = mock_update_order_state.call_args[0]
        assert call_args[0] == "add_item"

        item = call_args[1]
        assert item["name"] == "Martini"
        assert item["price"] == 13.0
        assert item["modifiers"] == "shaken"
        assert item["quantity"] == 1

        # Verify return message
        assert "Successfully added" in result
        assert "Martini" in result
        assert "shaken" in result

    @patch('src.llm.tools.get_menu')
    @patch('src.llm.tools.update_order_state')
    def test_add_to_order_with_multiple_modifiers(self, mock_update_order_state, mock_get_menu):
        """Test adding item with multiple modifiers."""
        # Setup mocks
        mock_get_menu.invoke.return_value = """
        MENU:
        Old Fashioned - $12.00
        """

        # Execute function using invoke
        result = add_to_order.invoke({"item_name": "Old Fashioned", "modifiers": ["on the rocks", "with cherry"], "quantity": 1})

        # Verify modifiers were combined
        mock_update_order_state.assert_called_once()
        call_args = mock_update_order_state.call_args[0]
        item = call_args[1]
        assert item["modifiers"] == "on the rocks, with cherry"

        # Verify return message
        assert "on the rocks, with cherry" in result

    @patch('src.llm.tools.get_menu')
    @patch('src.llm.tools.update_order_state')
    def test_add_to_order_with_quantity(self, mock_update_order_state, mock_get_menu):
        """Test adding multiple quantities of an item."""
        # Setup mocks
        mock_get_menu.invoke.return_value = """
        MENU:
        Beer - $5.00
        """

        # Execute function using invoke
        result = add_to_order.invoke({"item_name": "Beer", "modifiers": [], "quantity": 3})

        # Verify quantity and price calculation
        mock_update_order_state.assert_called_once()
        call_args = mock_update_order_state.call_args[0]
        item = call_args[1]
        assert item["quantity"] == 3
        assert item["price"] == 15.0  # 3 * 5.00

        # Verify return message (accepts both "3 x" and "3x" formats)
        assert "3 x Beer" in result or "3x Beer" in result

    @patch('src.llm.tools.get_menu')
    @patch('src.llm.tools.update_order_state')
    def test_add_to_order_no_modifiers(self, mock_update_order_state, mock_get_menu):
        """Test adding item without modifiers."""
        # Setup mocks
        mock_get_menu.invoke.return_value = """
        MENU:
        Water - $1.00
        """

        # Execute function using invoke
        result = add_to_order.invoke({"item_name": "Water"})

        # Verify no modifiers
        mock_update_order_state.assert_called_once()
        call_args = mock_update_order_state.call_args[0]
        item = call_args[1]
        assert item["modifiers"] == "no modifiers"

        # Verify return message
        assert "Successfully added" in result
        assert "Water" in result

    @patch('src.llm.tools.get_menu')
    def test_add_to_order_item_not_found(self, mock_get_menu):
        """Test adding item not found in menu."""
        # Setup mocks
        mock_get_menu.invoke.return_value = """
        MENU:
        Martini - $13.00
        """

        # Execute function using invoke
        result = add_to_order.invoke({"item_name": "Unknown Drink"})

        # Verify error message
        assert "Error:" in result
        assert "could not be found" in result
        assert "Unknown Drink" in result

    @patch('src.llm.tools.get_menu')
    @patch('src.llm.tools.update_order_state')
    def test_add_to_order_case_insensitive(self, mock_update_order_state, mock_get_menu):
        """Test that item matching is case insensitive."""
        # Setup mocks
        mock_get_menu.invoke.return_value = """
        MENU:
        martini - $13.00
        """

        # Execute function with different case using invoke
        result = add_to_order.invoke({"item_name": "MARTINI", "modifiers": ["shaken"]})

        # Verify it was found and added
        mock_update_order_state.assert_called_once()
        assert "Successfully added" in result


class TestGetOrder:
    """Test cases for get_order function."""

    @patch('src.llm.tools.get_current_order_state')
    def test_get_order_empty(self, mock_get_current_order_state):
        """Test getting empty order."""
        # Setup mocks
        mock_get_current_order_state.return_value = []

        # Execute function using invoke
        result = get_order.invoke({})

        # Verify return message
        assert "currently empty" in result

    @patch('src.llm.tools.get_current_order_state')
    def test_get_order_with_items(self, mock_get_current_order_state):
        """Test getting order with items."""
        # Setup mocks
        mock_get_current_order_state.return_value = [
            {"name": "Martini", "price": 13.0, "modifiers": "shaken", "quantity": 1},
            {"name": "Beer", "price": 10.0, "modifiers": "no modifiers", "quantity": 2}
        ]

        # Execute function using invoke
        result = get_order.invoke({})

        # Verify order details
        assert "Current Order:" in result
        assert "Martini" in result
        assert "shaken" in result
        assert "$13.00" in result
        assert "2x Beer" in result
        assert "$5.00 each" in result
        assert "Total: $23.00" in result

    @patch('src.llm.tools.get_current_order_state')
    def test_get_order_with_modifiers(self, mock_get_current_order_state):
        """Test getting order with items that have modifiers."""
        # Setup mocks
        mock_get_current_order_state.return_value = [
            {"name": "Old Fashioned", "price": 12.0, "modifiers": "on the rocks", "quantity": 1}
        ]

        # Execute function using invoke
        result = get_order.invoke({})

        # Verify modifiers are displayed
        assert "on the rocks" in result
        assert "Old Fashioned" in result


class TestConfirmOrder:
    """Test cases for confirm_order function."""

    @patch('src.llm.tools.get_current_order_state')
    def test_confirm_order_empty(self, mock_get_current_order_state):
        """Test confirming empty order."""
        # Setup mocks
        mock_get_current_order_state.return_value = []

        # Execute function using invoke
        result = confirm_order.invoke({})

        # Verify error message
        assert "nothing in the order" in result
        assert "add items first" in result

    @patch('src.llm.tools.get_current_order_state')
    def test_confirm_order_with_items(self, mock_get_current_order_state):
        """Test confirming order with items."""
        # Setup mocks
        mock_get_current_order_state.return_value = [
            {"name": "Martini", "price": 13.0, "modifiers": "shaken", "quantity": 1},
            {"name": "Beer", "price": 5.0, "modifiers": "no modifiers", "quantity": 1}
        ]

        # Execute function using invoke
        result = confirm_order.invoke({})

        # Verify confirmation message
        assert "Here is your current order:" in result
        assert "Martini" in result
        assert "shaken" in result
        assert "$13.00" in result
        assert "Beer" in result
        assert "$5.00" in result
        assert "Total: $18.00" in result
        assert "Is this correct?" in result


class TestPlaceOrder:
    """Test cases for place_order function."""

    @patch('src.llm.tools.get_current_order_state')
    @patch('src.llm.tools.update_order_state')
    @patch('src.llm.tools.random.randint')
    def test_place_order_successful(self, mock_randint, mock_update_order_state, mock_get_current_order_state):
        """Test successful order placement."""
        # Setup mocks
        mock_get_current_order_state.return_value = [
            {"name": "Martini", "price": 13.0, "modifiers": "shaken", "quantity": 1},
            {"name": "Beer", "price": 5.0, "modifiers": "no modifiers", "quantity": 1}
        ]
        mock_randint.return_value = 5

        # Execute function
        result = place_order.invoke({})

        # Verify random preparation time was generated
        mock_randint.assert_called_once_with(2, 8)

        # Verify update_order_state was called
        mock_update_order_state.assert_called_once_with("place_order")

        # Verify success message
        assert "Order placed successfully" in result
        assert "Martini" in result
        assert "Beer" in result
        assert "totalling $18.00" in result
        assert "5 minutes" in result

    @patch('src.llm.tools.get_current_order_state')
    def test_place_order_empty(self, mock_get_current_order_state):
        """Test placing empty order."""
        # Setup mocks
        mock_get_current_order_state.return_value = []

        # Execute function
        result = place_order.invoke({})

        # Verify error message
        assert "Cannot place an empty order" in result
        assert "add items first" in result


class TestClearOrder:
    """Test cases for clear_order function."""

    @patch('src.llm.tools.update_order_state')
    def test_clear_order_success(self, mock_update_order_state):
        """Test successful order clearing."""
        # Execute function using invoke
        result = clear_order.invoke({})

        # Verify update_order_state was called
        mock_update_order_state.assert_called_once_with("clear_order")

        # Verify success message
        assert "has been cleared" in result


class TestGetBill:
    """Test cases for get_bill function."""

    @patch('src.llm.tools.get_order_history')
    def test_get_bill_empty(self, mock_get_order_history):
        """Test getting bill for empty order."""
        # Setup mocks
        mock_get_order_history.return_value = {"items": [], "total_cost": 0.0, "tip_amount": 0.0, "paid": False}

        # Execute function using invoke
        result = get_bill.invoke({})

        # Verify message
        assert "haven't ordered anything" in result

    @patch('src.llm.tools.get_order_history')
    def test_get_bill_with_items_no_tip(self, mock_get_order_history):
        """Test getting bill with items but no tip."""
        # Setup mocks
        mock_get_order_history.return_value = {
            "items": [
                {"name": "Martini", "price": 13.0, "modifiers": "shaken", "quantity": 1},
                {"name": "Beer", "price": 5.0, "modifiers": "no modifiers", "quantity": 1}
            ],
            "total_cost": 18.0,
            "tip_amount": 0.0,
            "paid": False
        }

        # Execute function using invoke
        result = get_bill.invoke({})

        # Verify bill details
        assert "Your bill:" in result
        assert "Martini" in result
        assert "shaken" in result
        assert "$13.00" in result
        assert "Beer" in result
        assert "$5.00" in result
        assert "Total: $18.00" in result

    @patch('src.llm.tools.get_order_history')
    def test_get_bill_with_tip_percentage(self, mock_get_order_history):
        """Test getting bill with tip as percentage."""
        # Setup mocks
        mock_get_order_history.return_value = {
            "items": [{"name": "Martini", "price": 13.0, "modifiers": "shaken", "quantity": 1}],
            "total_cost": 13.0,
            "tip_amount": 1.95,
            "tip_percentage": 15.0,
            "paid": False
        }

        # Execute function using invoke
        result = get_bill.invoke({})

        # Verify tip details
        assert "Tip (15.0%)" in result
        assert "$1.95" in result
        assert "Total: $14.95" in result

    @patch('src.llm.tools.get_order_history')
    def test_get_bill_with_tip_amount(self, mock_get_order_history):
        """Test getting bill with tip as fixed amount."""
        # Setup mocks
        mock_get_order_history.return_value = {
            "items": [{"name": "Martini", "price": 13.0, "modifiers": "shaken", "quantity": 1}],
            "total_cost": 13.0,
            "tip_amount": 2.0,
            "tip_percentage": 0.0,
            "paid": False
        }

        # Execute function using invoke
        result = get_bill.invoke({})

        # Verify tip details
        assert "Tip: $2.00" in result
        assert "Total: $15.00" in result


class TestPayBill:
    """Test cases for pay_bill function."""

    @patch('src.llm.tools.get_order_history')
    @patch('src.llm.tools.update_order_state')
    def test_pay_bill_successful(self, mock_update_order_state, mock_get_order_history):
        """Test successful bill payment."""
        # Setup mocks
        mock_get_order_history.return_value = {
            "items": [{"name": "Martini", "price": 13.0, "modifiers": "shaken", "quantity": 1}],
            "total_cost": 13.0,
            "tip_amount": 2.0,
            "paid": False
        }

        # Execute function using invoke
        result = pay_bill.invoke({})

        # Verify update_order_state was called
        mock_update_order_state.assert_called_once_with("pay_bill")

        # Verify success message
        assert "Thank you for your payment" in result
        assert "$15.00" in result
        assert "$2.00 tip" in result

    @patch('src.llm.tools.get_order_history')
    def test_pay_bill_empty_order(self, mock_get_order_history):
        """Test paying bill for empty order."""
        # Setup mocks
        mock_get_order_history.return_value = {"items": [], "total_cost": 0.0, "paid": False}

        # Execute function using invoke
        result = pay_bill.invoke({})

        # Verify error message
        assert "haven't ordered anything" in result

    @patch('src.llm.tools.get_order_history')
    def test_pay_bill_already_paid(self, mock_get_order_history):
        """Test paying already paid bill."""
        # Setup mocks
        mock_get_order_history.return_value = {"items": [{"name": "Martini", "price": 13.0}], "paid": True}

        # Execute function using invoke
        result = pay_bill.invoke({})

        # Verify message
        assert "already been paid" in result
        assert "Thank you" in result


class TestAddTip:
    """Test cases for add_tip function."""

    @patch('src.llm.tools.get_order_history')
    @patch('src.llm.tools.update_order_state')
    def test_add_tip_percentage(self, mock_update_order_state, mock_get_order_history):
        """Test adding tip as percentage."""
        # Setup mocks
        mock_get_order_history.return_value = {
            "items": [{"name": "Martini", "price": 13.0}],
            "total_cost": 13.0,
            "paid": False
        }

        # Execute function using invoke
        result = add_tip.invoke({"percentage": 15.0})

        # Verify update_order_state was called
        mock_update_order_state.assert_called_once()
        call_args = mock_update_order_state.call_args[0]
        assert call_args[0] == "add_tip"

        tip_data = call_args[1]
        assert tip_data["amount"] == 1.95
        assert tip_data["percentage"] == 15.0

        # Verify return message
        assert "15.0% tip" in result
        assert "$1.95" in result
        assert "New total: $14.95" in result

    @patch('src.llm.tools.get_order_history')
    @patch('src.llm.tools.update_order_state')
    def test_add_tip_amount(self, mock_update_order_state, mock_get_order_history):
        """Test adding tip as fixed amount."""
        # Setup mocks
        mock_get_order_history.return_value = {
            "items": [{"name": "Martini", "price": 13.0}],
            "total_cost": 13.0,
            "paid": False
        }

        # Execute function using invoke
        result = add_tip.invoke({"amount": 2.0})

        # Verify update_order_state was called
        mock_update_order_state.assert_called_once()
        call_args = mock_update_order_state.call_args[0]
        tip_data = call_args[1]
        assert tip_data["amount"] == 2.0
        assert tip_data["percentage"] == pytest.approx(15.38, abs=0.01)  # 2.0 / 13.0 * 100

        # Verify return message
        assert "$2.00 tip" in result
        assert "New total: $15.00" in result

    @patch('src.llm.tools.get_order_history')
    def test_add_tip_empty_order(self, mock_get_order_history):
        """Test adding tip to empty order."""
        # Setup mocks
        mock_get_order_history.return_value = {"items": [], "total_cost": 0.0, "paid": False}

        # Execute function using invoke
        result = add_tip.invoke({"percentage": 15.0})

        # Verify error message
        assert "haven't ordered anything" in result
        assert "nothing to tip on" in result

    @patch('src.llm.tools.get_order_history')
    def test_add_tip_already_paid(self, mock_get_order_history):
        """Test adding tip to already paid bill."""
        # Setup mocks
        mock_get_order_history.return_value = {"items": [{"name": "Martini", "price": 13.0}], "paid": True}

        # Execute function using invoke
        result = add_tip.invoke({"percentage": 15.0})

        # Verify error message
        assert "already been paid" in result

    @patch('src.llm.tools.get_order_history')
    @patch('src.llm.tools.update_order_state')
    def test_add_tip_both_percentage_and_amount(self, mock_update_order_state, mock_get_order_history):
        """Test that percentage takes precedence when both are provided."""
        # Setup mocks
        mock_get_order_history.return_value = {
            "items": [{"name": "Martini", "price": 13.0}],
            "total_cost": 13.0,
            "paid": False
        }

        # Execute function with both parameters using invoke
        result = add_tip.invoke({"percentage": 15.0, "amount": 5.0})

        # Verify percentage was used (not amount)
        mock_update_order_state.assert_called_once()
        call_args = mock_update_order_state.call_args[0]
        tip_data = call_args[1]
        assert tip_data["amount"] == 1.95  # 15% of 13.0
        assert tip_data["percentage"] == 15.0

        # Verify percentage was mentioned in result
        assert "15.0% tip" in result


class TestGetAllTools:
    """Test cases for get_all_tools function."""

    def test_get_all_tools_returns_list(self):
        """Test that get_all_tools returns a list of all tools."""
        tools = get_all_tools()

        # Verify it's a list
        assert isinstance(tools, list)

        # Verify all expected tools are present (use .name attribute for StructuredTool)
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            'get_menu', 'get_recommendation', 'add_to_order',
            'add_to_order_with_balance', 'get_balance', 'get_order',
            'confirm_order', 'place_order', 'clear_order', 'get_bill',
            'pay_bill', 'add_tip', 'create_stripe_payment', 'check_payment_status'
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

        # Verify correct count
        assert len(tools) == len(expected_tools)


class TestAddToOrderWithBalance:
    """Test cases for add_to_order_with_balance function."""

    @patch('src.llm.tools.get_current_session')
    @patch('src.llm.tools.get_global_store')
    @patch('src.llm.tools.get_menu')
    def test_add_to_order_with_balance_item_not_found(self, mock_get_menu, mock_get_store, mock_get_session):
        """Test adding item not found in menu returns ITEM_NOT_FOUND error."""
        # Setup mocks
        mock_get_session.return_value = "test_session"
        mock_get_store.return_value = {}
        mock_get_menu.invoke.return_value = """
        MENU:
        Martini - $13.00
        """

        # Execute function using invoke
        from src.llm.tools import add_to_order_with_balance
        result = add_to_order_with_balance.invoke({"item_name": "Unknown Drink"})

        # Verify error response
        assert result["status"] == "error"
        assert result["error"] == "ITEM_NOT_FOUND"
        assert "Unknown Drink" in result["message"]

