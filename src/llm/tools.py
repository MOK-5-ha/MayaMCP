"""LLM tools for bartending operations."""

import re
import random
import threading
from enum import Enum
from langchain_core.tools import tool
from typing import Dict, List, Optional, Union
from typing_extensions import TypedDict, Literal

from ..config.logging_config import get_logger
from ..utils.state_manager import (
    get_current_order_state,
    get_order_history,
    update_order_state,
    get_payment_state,
    atomic_order_update,
    INSUFFICIENT_FUNDS as STATE_INSUFFICIENT_FUNDS,
    CONCURRENT_MODIFICATION as STATE_CONCURRENT_MODIFICATION,
)

logger = get_logger(__name__)


# =============================================================================
# Payment Tool Response Types
# =============================================================================

class ToolSuccess(TypedDict):
    """Successful tool response structure."""
    status: Literal["ok"]
    result: dict


class ToolError(TypedDict):
    """Error tool response structure."""
    status: Literal["error"]
    error: str  # PaymentError enum name as string
    message: str


ToolResponse = Union[ToolSuccess, ToolError]


class PaymentError(Enum):
    """
    Payment error codes with human-readable message templates.

    Each error code documents the condition that triggers it and
    references the requirement it validates.
    """
    # INSUFFICIENT_FUNDS: balance < order price (Req 1.3)
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"

    # STRIPE_UNAVAILABLE: Stripe MCP server not responding (Req 3.4)
    STRIPE_UNAVAILABLE = "STRIPE_UNAVAILABLE"

    # PAYMENT_FAILED: Stripe payment processing failed (Req 3.3)
    PAYMENT_FAILED = "PAYMENT_FAILED"

    # CONCURRENT_MODIFICATION: optimistic lock version mismatch (Req 1.3)
    CONCURRENT_MODIFICATION = "CONCURRENT_MODIFICATION"

    # NETWORK_ERROR: network timeout or connection failure during Stripe calls
    NETWORK_ERROR = "NETWORK_ERROR"

    # RATE_LIMITED: Stripe API rate limit exceeded
    RATE_LIMITED = "RATE_LIMITED"

    # INVALID_SESSION: session_id not found or expired
    INVALID_SESSION = "INVALID_SESSION"

    # PAYMENT_TIMEOUT: payment status polling exceeded deadline
    PAYMENT_TIMEOUT = "PAYMENT_TIMEOUT"


# Human-readable message templates for each error code
PAYMENT_ERROR_MESSAGES: Dict[PaymentError, str] = {
    PaymentError.INSUFFICIENT_FUNDS: (
        "Insufficient funds: your balance is ${balance:.2f} "
        "but the item costs ${price:.2f}."
    ),
    PaymentError.STRIPE_UNAVAILABLE: (
        "Payment service is temporarily unavailable. "
        "Please try again or use an alternative payment method."
    ),
    PaymentError.PAYMENT_FAILED: (
        "Payment processing failed. Please check your payment details "
        "and try again."
    ),
    PaymentError.CONCURRENT_MODIFICATION: (
        "Your order was modified by another request. "
        "Please try your order again."
    ),
    PaymentError.NETWORK_ERROR: (
        "Network error occurred while processing payment. "
        "Please check your connection and try again."
    ),
    PaymentError.RATE_LIMITED: (
        "Too many payment requests. Please wait a moment and try again."
    ),
    PaymentError.INVALID_SESSION: (
        "Your session has expired or is invalid. "
        "Please refresh the page and try again."
    ),
    PaymentError.PAYMENT_TIMEOUT: (
        "Payment status check timed out. "
        "Please check your payment status manually or try again."
    ),
}


def create_tool_success(result: dict) -> ToolSuccess:
    """Create a successful tool response."""
    return {"status": "ok", "result": result}


def create_tool_error(
    error: PaymentError,
    message: Optional[str] = None,
    **format_kwargs
) -> ToolError:
    """
    Create an error tool response.

    Args:
        error: PaymentError enum value
        message: Optional custom message (uses template if not provided)
        **format_kwargs: Values to format into the message template

    Returns:
        ToolError dict with status, error code, and message
    """
    if message is None:
        template = PAYMENT_ERROR_MESSAGES.get(error, "An unknown error occurred.")
        try:
            message = template.format(**format_kwargs)
        except KeyError:
            message = template

    return {
        "status": "error",
        "error": error.value,
        "message": message
    }

# Thread-local storage for session context
# This allows tools to access the current session_id without explicit parameter passing
# Initialize with default None (no active session) for backwards compatibility
_session_context = threading.local()


def get_current_session() -> Optional[str]:
    """Get the current session ID from thread-local storage.
    
    Returns:
        The current session_id if set, None otherwise.
        None indicates no active session - tools should fall back to legacy behavior.
    """
    return getattr(_session_context, 'session_id', None)


def set_current_session(session_id: Optional[str]) -> None:
    """Set the current session ID in thread-local storage.
    
    Args:
        session_id: The session ID to set, or None to clear.
    """
    _session_context.session_id = session_id


def clear_current_session() -> None:
    """Clear the current session ID from thread-local storage.

    This should be called in a finally block after processing completes
    to ensure the session context is always cleaned up.
    """
    _session_context.session_id = None


# Global store reference for payment tools (set during app initialization)
# This allows tools to access the session store without explicit parameter passing
_global_store: Optional[Dict] = None


def set_global_store(store: Dict) -> None:
    """Set the global store reference for payment tools."""
    global _global_store
    _global_store = store


def get_global_store() -> Dict:
    """Get the global store, creating a default if not set."""
    global _global_store
    if _global_store is None:
        _global_store = {}
    return _global_store


@tool
def add_to_order_with_balance(
    item_name: str,
    modifiers: Optional[List[str]] = None,
    quantity: int = 1
) -> ToolResponse:
    """Add item to order if user has sufficient balance.

    Session context read implicitly from _current_session thread-local.

    Args:
        item_name: The name of the drink to add to the order
        modifiers: Optional list of modifiers (e.g., 'neat', 'on the rocks')
        quantity: The number of this item to add (defaults to 1)

    Returns:
        Success: {"status": "ok", "result": {"item": str, "new_balance": float,
                  "new_tab": float}}
        Error: {"status": "error", "error": "INSUFFICIENT_FUNDS", "message": ...}
               {"status": "error", "error": "CONCURRENT_MODIFICATION", ...}
               {"status": "error", "error": "INVALID_SESSION", "message": ...}
    """
    if modifiers is None:
        modifiers = []

    # Get session context
    session_id = get_current_session()
    if session_id is None:
        logger.warning("add_to_order_with_balance called without session context")
        return create_tool_error(
            PaymentError.INVALID_SESSION,
            "No active session. Please refresh and try again."
        )

    store = get_global_store()

    # Parse menu to get item price
    menu_str = get_menu.invoke({})
    menu_items = _parse_menu_items(menu_str)
    item_lower = item_name.lower()

    if item_lower not in menu_items:
        logger.warning(f"Item '{item_name}' not found in menu")
        return create_tool_error(
            PaymentError.INVALID_SESSION,
            f"Item '{item_name}' not found on the menu."
        )

    unit_price = menu_items[item_lower]
    total_price = unit_price * quantity

    # Attempt atomic order update
    success, error_code, new_balance = atomic_order_update(
        session_id, store, total_price
    )

    if not success:
        if error_code == STATE_INSUFFICIENT_FUNDS:
            # Get current balance for error message
            payment = get_payment_state(session_id, store)
            return create_tool_error(
                PaymentError.INSUFFICIENT_FUNDS,
                balance=payment['balance'],
                price=total_price
            )
        elif error_code == STATE_CONCURRENT_MODIFICATION:
            return create_tool_error(PaymentError.CONCURRENT_MODIFICATION)
        else:
            return create_tool_error(
                PaymentError.INVALID_SESSION,
                f"Unknown error: {error_code}"
            )

    # Add item to order state (for display purposes)
    modifier_str = ", ".join(modifiers) if modifiers else "no modifiers"
    item = {
        "name": item_name,
        "price": total_price,
        "modifiers": modifier_str,
        "quantity": quantity
    }
    update_order_state("add_item", item)

    # Get updated payment state for response
    payment = get_payment_state(session_id, store)

    logger.info(
        f"Added {quantity}x '{item_name}' to order. "
        f"New balance: ${new_balance:.2f}, Tab: ${payment['tab_total']:.2f}"
    )

    return create_tool_success({
        "item": f"{quantity}x {item_name}" if quantity > 1 else item_name,
        "new_balance": new_balance,
        "new_tab": payment['tab_total']
    })


@tool
def get_balance() -> ToolResponse:
    """Return current user balance and tab.

    Session context read implicitly from _current_session thread-local.

    Returns:
        Success: {"status": "ok", "result": {"balance": float, "tab": float}}
        Error: {"status": "error", "error": "INVALID_SESSION", "message": ...}
    """
    session_id = get_current_session()
    if session_id is None:
        logger.warning("get_balance called without session context")
        return create_tool_error(
            PaymentError.INVALID_SESSION,
            "No active session. Please refresh and try again."
        )

    store = get_global_store()
    payment = get_payment_state(session_id, store)

    return create_tool_success({
        "balance": payment['balance'],
        "tab": payment['tab_total']
    })


@tool
def get_menu() -> str:
    """Provide the latest up-to-date menu."""
    return """
    MENU:
    Cocktails with Liquor:
    Daiquiri - $10.00
    Martini - $13.00
    Long Island - $12.00
    Old Fashioned - $12.00 
    Negroni - $11.00
    Cosmopolitan - $12.00
    Manhattan - $12.00

    Beer:
    Tap Beer - $5.00
    Classic Brew - $5.00
    IPA - $6.00

    Spirits (Neat or On the Rocks):
    Whiskey - $8.00
    Vodka - $7.00
    Rum - $7.00
    Gin - $8.00
    Tequila - $8.00
    Brandy - $9.00

    Non-Alcoholic Beverages:
    Water - $1.00
    Iced Tea - $2.00
    Lemonade - $2.00
    Soda - $3.00

    Modifiers:
    Liquor Options: Vodka, Tequila, Gin, Whiskey, Rum, Brandy; Default option: Vodka
    Special requests: 'shaken', 'stirred', 'neat', 'dry', 'dirty', 'perfect', 'on the rocks', 'with a chaser'
    
    Drink Term Explanations:
    'neat' - No ice, straight from the bottle
    'on the rocks' - Served with ice
    'dry' - Less vermouth (for martinis)
    'dirty' - With olive juice (for martinis)
    'perfect' - Equal parts dry and sweet vermouth
    'chaser' - Separate non-alcoholic drink to follow
    
    Preference Guide:
    'sobering' - Non-alcoholic options when you want to stay clear-headed
    'classy' - Sophisticated, elegant drinks for refined tastes
    'fruity' - Sweet, refreshing drinks with fruit flavors
    'strong' - Higher alcohol content for experienced drinkers
    'burning' - Intense sensation with high alcohol content, often spirits like whiskey
"""

@tool
def get_recommendation(preference: str) -> str:
    """Recommends drinks based on customer preference.
    
    Args:
        preference: Customer's drink preference (e.g., 'classy', 'strong', 'fruity', 'sobering', 'burning')
        
    Returns:
        Recommended drinks matching the preference
    """
    preferences_map = {
        "sobering": {
            "drinks": ["Water", "Iced Tea", "Lemonade", "Soda"],
            "description": "Here are some excellent non-alcoholic options to keep you refreshed and clear-headed"
        },
        "classy": {
            "drinks": ["Martini", "Old Fashioned", "Manhattan", "Negroni"],
            "description": "These sophisticated classics have stood the test of time for the discerning palate"
        },
        "fruity": {
            "drinks": ["Daiquiri", "Cosmopolitan", "Lemonade"],
            "description": "These drinks offer a perfect balance of sweetness and refreshing fruit flavors"
        },
        "strong": {
            "drinks": ["Long Island", "Old Fashioned", "Negroni", "Whiskey (neat)"],
            "description": "These potent options pack a punch with higher alcohol content"
        },
        "burning": {
            "drinks": ["Whiskey (neat)", "Tequila (neat)", "Rum (neat)"],
            "description": "These spirits deliver that characteristic burn when sipped straight"
        }
    }
    
    preference = preference.lower()
    
    # Check if the preference is valid
    if preference in preferences_map:
        rec = preferences_map[preference]
        drinks_list = ", ".join(rec["drinks"])
        return f"{rec['description']}: {drinks_list}"
    else:
        # If preference not recognized, provide general recommendations
        popular_drinks = "Martini, Daiquiri, Old Fashioned, and IPA"
        return f"I'm not familiar with that specific preference, but some of our most popular drinks are: {popular_drinks}"

def _parse_menu_items(menu_str: str) -> Dict[str, float]:
    """Parse menu string to extract items and prices."""
    items = {}
    # Regex to find lines like "Item Name - $Price.xx"
    pattern = re.compile(r"^\s*(.+?)\s*-\s*\$(\d+\.\d{2})\s*$", re.MULTILINE)
    matches = pattern.findall(menu_str)
    for match in matches:
        item_name = match[0].strip()
        price = float(match[1])
        items[item_name.lower()] = price 
    return items

@tool
def add_to_order(
    item_name: str,
    modifiers: Optional[List[str]] = None,
    quantity: int = 1
) -> str:
    """Adds the specified drink to the customer's order, including any modifiers.

    If a session context is available, this tool will check the user's balance
    before adding the item. If balance is insufficient, the order is rejected.

    Args:
        item_name: The name of the drink to add to the order
        modifiers: Optional list of modifiers (e.g., 'neat', 'on the rocks')
        quantity: The number of this item to add (defaults to 1).

    Returns:
        A confirmation message with the updated order, or an error message.
    """
    if modifiers is None:
        modifiers = []

    # Check if we have a session context for balance checking
    session_id = get_current_session()

    if session_id is not None:
        # Use balance-aware ordering
        result = add_to_order_with_balance.invoke({
            "item_name": item_name,
            "modifiers": modifiers,
            "quantity": quantity
        })

        # Convert ToolResponse to string for backward compatibility
        if result["status"] == "ok":
            modifier_str = ", ".join(modifiers) if modifiers else "no modifiers"
            new_balance = result["result"]["new_balance"]
            return (
                f"Successfully added {quantity}x {item_name} ({modifier_str}) "
                f"to the order. Your balance is now ${new_balance:.2f}."
            )
        else:
            # Return error message
            return f"Error: {result['message']}"

    # Legacy behavior: no session context, no balance checking
    menu_str = get_menu.invoke({})
    menu_items = _parse_menu_items(menu_str)
    item_lower = item_name.lower()

    if item_lower in menu_items:
        price = menu_items[item_lower]
        modifier_str = ", ".join(modifiers) if modifiers else "no modifiers"

        # Create item with quantity info
        item = {
            "name": item_name,
            "price": price * quantity,
            "modifiers": modifier_str,
            "quantity": quantity
        }

        # Update order state
        update_order_state("add_item", item)

        logger.info(
            f"Tool: Added {quantity}x '{item_name}' ({modifier_str}) to order."
        )
        return (
            f"Successfully added {quantity}x {item_name} ({modifier_str}) "
            "to the order."
        )
    else:
        logger.warning(
            f"Tool: Item '{item_name}' not found in parsed menu."
        )
        return (
            f"Error: Item '{item_name}' could not be found on the menu. "
            "Please verify the item name."
        )

@tool
def get_order() -> str:
    """Returns the current list of items in the order for the agent to see."""
    order_list = get_current_order_state()
    
    if not order_list:
        return "The order is currently empty."
    
    # Enhanced order display including quantity and modifiers
    order_details = []
    for item in order_list:
        quantity = item.get('quantity', 1)  
    
        if "modifiers" in item and item["modifiers"] != "no modifiers":
            # Show single price per item, not total price
            item_price = item['price'] / quantity if quantity > 0 else item['price']
            if quantity > 1:
                order_details.append(f"- {quantity}x {item['name']} with {item['modifiers']} (${item_price:.2f} each)")
            else:
                order_details.append(f"- {item['name']} with {item['modifiers']} (${item_price:.2f})")
        else:
            # Show single price per item, not total price
            item_price = item['price'] / quantity if quantity > 0 else item['price']
            if quantity > 1:
                order_details.append(f"- {quantity}x {item['name']} (${item_price:.2f} each)")
            else:
                order_details.append(f"- {item['name']} (${item_price:.2f})")
    
    order_text = "\n".join(order_details)
    total = sum(item['price'] for item in order_list)
    
    return f"Current Order:\n{order_text}\nTotal: ${total:.2f}"

@tool
def confirm_order() -> str:
    """Displays the current order to the user and asks for confirmation."""
    order_list = get_current_order_state()
    
    if not order_list:
        return "There is nothing in the order to confirm. Please add items first."
    
    # Enhanced order display including modifiers
    order_details = []
    for item in order_list:
        if "modifiers" in item and item["modifiers"] != "no modifiers":
            order_details.append(f"- {item['name']} with {item['modifiers']} (${item['price']:.2f})")
        else:
            order_details.append(f"- {item['name']} (${item['price']:.2f})")
    
    order_text = "\n".join(order_details)
    total = sum(item['price'] for item in order_list)
    
    confirmation_request = f"Here is your current order:\n{order_text}\nTotal: ${total:.2f}\n\nIs this correct? You can ask to add/remove items or proceed to place the order."
    logger.info("Tool: Generated order confirmation request with modifiers for user.")
    
    return confirmation_request

@tool
def place_order() -> str:
    """Finalizes and places the customer's confirmed order."""
    order_list = get_current_order_state()
    
    if not order_list:
        return "Cannot place an empty order. Please add items first."
    
    # Enhanced order details including modifiers
    order_details = []
    current_order_cost = 0.0
    
    for item in order_list:
        # Add to running total
        current_order_cost += item['price']
        
        # Format for display
        if "modifiers" in item and item["modifiers"] != "no modifiers":
            order_details.append(f"{item['name']} with {item['modifiers']}")
        else:
            order_details.append(item['name'])
    
    order_text = ", ".join(order_details)
    total = sum(item['price'] for item in order_list)
    
    # Simulate random preparation time between 2-8 minutes
    prep_time = random.randint(2, 8)
    
    logger.info(f"Tool: Placing order: [{order_text}], Total: ${total:.2f}, ETA: {prep_time} minutes")
    
    # Update order state to place the order
    update_order_state("place_order")

    return f"Order placed successfully! Your items ({order_text}) totalling ${total:.2f} will be ready in approximately {prep_time} minutes."

@tool
def clear_order() -> str:
    """Removes all items from the user's order."""
    update_order_state("clear_order")
    return "Your order has been cleared."

@tool
def get_bill() -> str:
    """Calculates the total bill for all items ordered in this session."""
    order_history = get_order_history()
    
    if not order_history['items']:
        return "You haven't ordered anything yet."
    
    # Format the bill with details
    bill_details = []
    for item in order_history['items']:
        item_text = item['name']
        quantity = item.get('quantity', 1)  
    
        if "modifiers" in item and item["modifiers"] != "no modifiers":
            item_text += f" with {item['modifiers']}"
            
        # Calculate single item price
        item_price = item['price'] / quantity if quantity > 0 else item['price']
        
        if quantity > 1:
            bill_details.append(f"{quantity}x {item_text}: ${item_price:.2f} each = ${item['price']:.2f}")
        else:
            bill_details.append(f"{item_text}: ${item_price:.2f}")
    
    bill_text = "\n".join(bill_details)
    subtotal = order_history['total_cost']
    
    # Include tip in the bill if present
    if order_history['tip_amount'] > 0:
        tip = order_history['tip_amount']
        total = subtotal + tip
        if order_history['tip_percentage'] > 0:
            return f"Your bill:\n{bill_text}\n\nSubtotal: ${subtotal:.2f}\nTip ({order_history['tip_percentage']:.1f}%): ${tip:.2f}\nTotal: ${total:.2f}"
        else:
            return f"Your bill:\n{bill_text}\n\nSubtotal: ${subtotal:.2f}\nTip: ${tip:.2f}\nTotal: ${total:.2f}"
    else:
        return f"Your bill:\n{bill_text}\n\nTotal: ${subtotal:.2f}"

@tool
def pay_bill() -> str:
    """Mark the customer's bill as paid."""
    order_history = get_order_history()
    
    if not order_history['items']:
        return "You haven't ordered anything yet."
    
    if order_history['paid']:
        return "Your bill has already been paid. Thank you!"
    
    subtotal = order_history['total_cost']
    tip = order_history['tip_amount']
    total = subtotal + tip
    
    # Update order state to mark as paid
    update_order_state("pay_bill")
    
    if tip > 0:
        return f"Thank you for your payment of ${total:.2f} (including ${tip:.2f} tip)! We hope you enjoyed your drinks at MOK 5-ha."
    else:
        return f"Thank you for your payment of ${subtotal:.2f}! We hope you enjoyed your drinks at MOK 5-ha."

@tool
def add_tip(percentage: float = 0.0, amount: float = 0.0) -> str:
    """Add a tip to the bill. Can specify either a percentage or a fixed amount.
    
    Args:
        percentage: Tip percentage (e.g., 15 for 15%, 20 for 20%) - this takes precedence if both specified
        amount: Fixed tip amount in dollars (e.g., 5.0 for $5) - only used if percentage is 0
    
    Returns:
        Confirmation message with the updated bill total including tip
    """
    order_history = get_order_history()
    
    if not order_history['items']:
        return "You haven't ordered anything yet, so there's nothing to tip on."
    
    if order_history['paid']:
        return "The bill has already been paid. Thank you for your business!"
    
    # Calculate the tip amount
    if percentage > 0:
        tip_amount = order_history['total_cost'] * (percentage / 100)
        tip_percentage = percentage
    else:
        tip_amount = amount
        if order_history['total_cost'] > 0:
            tip_percentage = (amount / order_history['total_cost']) * 100
        else:
            tip_percentage = 0
    
    # Round tip to two decimal places for cleaner display
    tip_amount = round(tip_amount, 2)
    
    # Update order state with tip
    update_order_state("add_tip", {"amount": tip_amount, "percentage": tip_percentage})
    
    # Calculate the new total
    subtotal = order_history['total_cost']
    total_with_tip = subtotal + tip_amount
    
    if percentage > 0:
        return f"Added a {percentage:.1f}% tip (${tip_amount:.2f}) to your bill. New total: ${total_with_tip:.2f}"
    else:
        return f"Added a ${amount:.2f} tip to your bill. New total: ${total_with_tip:.2f}"

def get_all_tools() -> List:
    """Get list of all available tools."""
    return [
        get_menu,
        get_recommendation,
        add_to_order,
        add_to_order_with_balance,
        get_balance,
        get_order,
        confirm_order,
        place_order,
        clear_order,
        get_bill,
        pay_bill,
        add_tip
    ]