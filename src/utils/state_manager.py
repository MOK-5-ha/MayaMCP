"""State management for conversation and order tracking."""

from typing import Dict, List, Any, Optional, MutableMapping
from ..config.logging_config import get_logger

logger = get_logger(__name__)

# Default State Templates
DEFAULT_CONVERSATION_STATE = {
    'turn_count': 0,
    'phase': 'greeting',
    'last_order_time': 0,
    'small_talk_count': 0
}

DEFAULT_ORDER_HISTORY = {
    'items': [],
    'total_cost': 0.0,
    'paid': False,
    'tip_amount': 0.0,
    'tip_percentage': 0.0
}

DEFAULT_CURRENT_ORDER = {
    'order': [],
    'finished': False
}

def _get_session_data(session_id: str, store: MutableMapping) -> Dict[str, Any]:
    """
    Retrieve session data from the store, initializing it if necessary.
    
    Args:
        session_id: Unique identifier for the user session.
        store: Mutable mapping (dict or modal.Dict) to store state.
        
    Returns:
        The session data dictionary.
    """
    if session_id not in store:
        logger.info(f"Initializing new session state for {session_id}")
        store[session_id] = {
            'conversation': DEFAULT_CONVERSATION_STATE.copy(),
            'history': DEFAULT_ORDER_HISTORY.copy(),
            'current_order': DEFAULT_CURRENT_ORDER.copy()
        }
    return store[session_id]

def _save_session_data(session_id: str, store: MutableMapping, data: Dict[str, Any]) -> None:
    """
    Save session data back to the store.
    
    Args:
        session_id: Unique identifier for the user session.
        store: Mutable mapping to update.
        data: The full session data object.
    """
    store[session_id] = data


def initialize_state(session_id: str = "default", store: MutableMapping = None) -> None:
    """
    Initialize or reset state variables for a session.
    
    Args:
        session_id: Session ID to initialize.
        store: Storage backend.
    """
    if store is None:
        # For backward compatibility or testing without a store, we warn but do nothing
        # or we could use a local global dict if we wanted to maintain old behavior,
        # but for this refactor we want to enforce passing state.
        logger.warning("initialize_state called without store! State will be ephemeral/lost.")
        return

    # Force reset by overwriting with defaults
    store[session_id] = {
        'conversation': DEFAULT_CONVERSATION_STATE.copy(),
        'history': DEFAULT_ORDER_HISTORY.copy(),
        'current_order': DEFAULT_CURRENT_ORDER.copy()
    }
    logger.info(f"State initialized for session {session_id}")

def get_conversation_state(session_id: str, store: MutableMapping) -> Dict[str, Any]:
    """Get current conversation state."""
    data = _get_session_data(session_id, store)
    return data['conversation'].copy()

def get_order_history(session_id: str, store: MutableMapping) -> Dict[str, Any]:
    """Get order history."""
    data = _get_session_data(session_id, store)
    return data['history']

def get_current_order_state(session_id: str, store: MutableMapping) -> List[Dict[str, Any]]:
    """Get current order state."""
    data = _get_session_data(session_id, store)
    return data['current_order']['order']

def update_conversation_state(session_id: str, store: MutableMapping, updates: Dict[str, Any]) -> None:
    """
    Update conversation state.
    """
    data = _get_session_data(session_id, store)
    data['conversation'].update(updates)
    _save_session_data(session_id, store, data)
    logger.debug(f"Conversation state updated for {session_id}: {updates}")

def update_order_state(session_id: str, store: MutableMapping, action: str, data: Optional[Any] = None) -> None:
    """
    Update order state based on action.
    """
    session_data = _get_session_data(session_id, store)
    history = session_data['history']
    current_order = session_data['current_order']
    
    if action == "add_item" and data:
        # Add item to current order
        current_order['order'].append(data)
        
        # Add to order history
        history['items'].append(data.copy())
        history['total_cost'] += data['price']
        
        logger.info(f"Added item to order for {session_id}: {data['name']}")
        
    elif action == "place_order":
        # Mark order as finished and clear current order
        current_order['finished'] = True
        current_order['order'] = []
        
        logger.info(f"Order placed for {session_id}")
        
    elif action == "clear_order":
        # Clear current order
        current_order['order'] = []
        current_order['finished'] = False
        
        logger.info(f"Order cleared for {session_id}")
        
    elif action == "add_tip" and data:
        # Add tip to order history
        history['tip_amount'] = data['amount']
        history['tip_percentage'] = data['percentage']
        
        logger.info(f"Tip added for {session_id}: ${data['amount']:.2f}")
        
    elif action == "pay_bill":
        # Mark bill as paid
        history['paid'] = True
        
        logger.info(f"Bill paid for {session_id}")
        
    # Save changes
    _save_session_data(session_id, store, session_data)

def reset_session_state(session_id: str, store: MutableMapping) -> None:
    """Reset all session state."""
    initialize_state(session_id, store)
    logger.info(f"Session state reset for {session_id}")

def is_order_finished(session_id: str, store: MutableMapping) -> bool:
    """Check if current order is finished."""
    data = _get_session_data(session_id, store)
    return data['current_order']['finished']

def get_order_total(session_id: str, store: MutableMapping) -> float:
    """Get total cost of current order."""
    data = _get_session_data(session_id, store)
    return sum(item['price'] for item in data['current_order']['order'])