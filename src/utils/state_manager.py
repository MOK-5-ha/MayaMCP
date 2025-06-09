"""State management for conversation and order tracking."""

from typing import Dict, List, Any, Optional
from ..config.logging_config import get_logger

logger = get_logger(__name__)

# Global state variables (in a real application, these would be session-specific)
_conversation_state = {
    'turn_count': 0,
    'phase': 'greeting',  
    'last_order_time': 0,  
    'small_talk_count': 0  
}

_order_history = {
    'items': [],       
    'total_cost': 0.0, 
    'paid': False,     
    'tip_amount': 0.0, 
    'tip_percentage': 0.0 
}

_current_order_state = {
    'order': [], 
    'finished': False
}

def initialize_state() -> None:
    """Initialize or reset all state variables."""
    global _conversation_state, _order_history, _current_order_state
    
    _conversation_state = {
        'turn_count': 0,
        'phase': 'greeting',
        'last_order_time': 0,
        'small_talk_count': 0
    }
    
    _order_history = {
        'items': [],
        'total_cost': 0.0,
        'paid': False,
        'tip_amount': 0.0,
        'tip_percentage': 0.0
    }
    
    _current_order_state = {
        'order': [],
        'finished': False
    }
    
    logger.info("State initialized")

def get_conversation_state() -> Dict[str, Any]:
    """Get current conversation state."""
    return _conversation_state.copy()

def get_order_history() -> Dict[str, Any]:
    """Get order history."""
    return _order_history

def get_current_order_state() -> List[Dict[str, Any]]:
    """Get current order state."""
    return _current_order_state['order']

def update_conversation_state(updates: Dict[str, Any]) -> None:
    """
    Update conversation state.
    
    Args:
        updates: Dictionary of state updates
    """
    global _conversation_state
    _conversation_state.update(updates)
    logger.debug(f"Conversation state updated: {updates}")

def update_order_state(action: str, data: Optional[Any] = None) -> None:
    """
    Update order state based on action.
    
    Args:
        action: Action to perform (add_item, place_order, clear_order, add_tip, pay_bill)
        data: Additional data for the action
    """
    global _order_history, _current_order_state
    
    if action == "add_item" and data:
        # Add item to current order
        _current_order_state['order'].append(data)
        
        # Add to order history
        _order_history['items'].append(data.copy())
        _order_history['total_cost'] += data['price']
        
        logger.info(f"Added item to order: {data['name']}")
        
    elif action == "place_order":
        # Mark order as finished and clear current order
        _current_order_state['finished'] = True
        _current_order_state['order'] = []
        
        logger.info("Order placed")
        
    elif action == "clear_order":
        # Clear current order
        _current_order_state['order'] = []
        _current_order_state['finished'] = False
        
        logger.info("Order cleared")
        
    elif action == "add_tip" and data:
        # Add tip to order history
        _order_history['tip_amount'] = data['amount']
        _order_history['tip_percentage'] = data['percentage']
        
        logger.info(f"Tip added: ${data['amount']:.2f}")
        
    elif action == "pay_bill":
        # Mark bill as paid
        _order_history['paid'] = True
        
        logger.info("Bill paid")

def reset_session_state() -> None:
    """Reset all session state."""
    initialize_state()
    logger.info("Session state reset")

def is_order_finished() -> bool:
    """Check if current order is finished."""
    return _current_order_state['finished']

def get_order_total() -> float:
    """Get total cost of current order."""
    return sum(item['price'] for item in _current_order_state['order'])