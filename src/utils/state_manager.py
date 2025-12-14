"""State management for conversation and order tracking."""

import re
import threading
import time
from typing import Dict, List, Any, Optional, MutableMapping, Tuple, Literal
from typing_extensions import TypedDict
from ..config.logging_config import get_logger

logger = get_logger(__name__)


# =============================================================================
# Payment State Types and Validation
# =============================================================================

class PaymentState(TypedDict):
    """Payment state schema with strict typing."""
    balance: float          # >= 0, default: 1000.00
    tab_total: float        # >= 0, default: 0.00
    stripe_payment_id: Optional[str]  # None or Stripe ID pattern: ^(plink_|pi_)[a-zA-Z0-9]+$
    payment_status: Literal['pending', 'processing', 'completed']  # default: 'pending'
    idempotency_key: Optional[str]    # None or format: {session_id}_{unix_timestamp}
    version: int            # >= 0, default: 0
    needs_reconciliation: bool  # default: False


# Stripe ID pattern: plink_ or pi_ followed by alphanumeric characters
STRIPE_ID_PATTERN = re.compile(r'^(plink_|pi_)[a-zA-Z0-9]+$')

# Idempotency key pattern: alphanumeric with underscore separator
IDEMPOTENCY_KEY_PATTERN = re.compile(r'^[a-zA-Z0-9]+_[0-9]+$')

# Valid payment status transitions
VALID_STATUS_TRANSITIONS = {
    'pending': {'processing', 'completed'},
    'processing': {'completed'},
    'completed': set()  # No backwards transitions allowed
}


DEFAULT_PAYMENT_STATE: PaymentState = {
    'balance': 1000.00,
    'tab_total': 0.00,
    'stripe_payment_id': None,
    'payment_status': 'pending',
    'idempotency_key': None,
    'version': 0,
    'needs_reconciliation': False
}


class PaymentStateValidationError(ValueError):
    """Raised when payment state validation fails."""
    pass


def validate_payment_state(state: Dict[str, Any], allow_partial: bool = False) -> bool:
    """
    Validate payment state against all constraints.
    
    Args:
        state: Payment state dictionary to validate
        allow_partial: If True, only validate fields that are present
        
    Returns:
        True if valid
        
    Raises:
        PaymentStateValidationError: If validation fails
    """
    # Check required fields if not partial
    if not allow_partial:
        required_fields = {'balance', 'tab_total', 'stripe_payment_id', 
                          'payment_status', 'idempotency_key', 'version', 
                          'needs_reconciliation'}
        missing = required_fields - set(state.keys())
        if missing:
            raise PaymentStateValidationError(f"Missing required fields: {missing}")
    
    # Validate balance >= 0
    if 'balance' in state:
        if not isinstance(state['balance'], (int, float)):
            raise PaymentStateValidationError("balance must be a number")
        if state['balance'] < 0:
            raise PaymentStateValidationError(f"balance must be >= 0, got {state['balance']}")
    
    # Validate tab_total >= 0
    if 'tab_total' in state:
        if not isinstance(state['tab_total'], (int, float)):
            raise PaymentStateValidationError("tab_total must be a number")
        if state['tab_total'] < 0:
            raise PaymentStateValidationError(f"tab_total must be >= 0, got {state['tab_total']}")
    
    # Validate version >= 0
    if 'version' in state:
        if not isinstance(state['version'], int):
            raise PaymentStateValidationError("version must be an integer")
        if state['version'] < 0:
            raise PaymentStateValidationError(f"version must be >= 0, got {state['version']}")
    
    # Validate stripe_payment_id pattern
    if 'stripe_payment_id' in state:
        stripe_id = state['stripe_payment_id']
        if stripe_id is not None:
            if not isinstance(stripe_id, str):
                raise PaymentStateValidationError("stripe_payment_id must be a string or None")
            if not STRIPE_ID_PATTERN.match(stripe_id):
                raise PaymentStateValidationError(
                    f"stripe_payment_id must match pattern ^(plink_|pi_)[a-zA-Z0-9]+$, got {stripe_id}"
                )
    
    # Validate idempotency_key pattern
    if 'idempotency_key' in state:
        idem_key = state['idempotency_key']
        if idem_key is not None:
            if not isinstance(idem_key, str):
                raise PaymentStateValidationError("idempotency_key must be a string or None")
            if not IDEMPOTENCY_KEY_PATTERN.match(idem_key):
                raise PaymentStateValidationError(
                    f"idempotency_key must match pattern {{session_id}}_{{unix_timestamp}}, got {idem_key}"
                )
    
    # Validate payment_status
    if 'payment_status' in state:
        valid_statuses = {'pending', 'processing', 'completed'}
        if state['payment_status'] not in valid_statuses:
            raise PaymentStateValidationError(
                f"payment_status must be one of {valid_statuses}, got {state['payment_status']}"
            )
    
    # Validate needs_reconciliation is boolean
    if 'needs_reconciliation' in state:
        if not isinstance(state['needs_reconciliation'], bool):
            raise PaymentStateValidationError("needs_reconciliation must be a boolean")
    
    # Mutual constraint: needs_reconciliation == False when payment_status == 'completed'
    if 'payment_status' in state and 'needs_reconciliation' in state:
        if state['payment_status'] == 'completed' and state['needs_reconciliation']:
            raise PaymentStateValidationError(
                "needs_reconciliation must be False when payment_status is 'completed'"
            )
    
    return True


def is_valid_status_transition(current_status: str, new_status: str) -> bool:
    """
    Check if a payment status transition is valid.
    
    Status transitions: pending → processing → completed (no backwards transitions)
    
    Args:
        current_status: Current payment status
        new_status: Proposed new status
        
    Returns:
        True if transition is valid, False otherwise
    """
    if current_status == new_status:
        return True  # No change is always valid
    
    allowed = VALID_STATUS_TRANSITIONS.get(current_status, set())
    return new_status in allowed


# =============================================================================
# Thread-Safe Session Locking
# =============================================================================

# Session locks for concurrency control (thread-safe access)
# Using regular Dict (NOT WeakValueDictionary) to ensure lock instances persist
# until explicit cleanup - prevents race conditions from premature GC
_session_locks: Dict[str, threading.Lock] = {}
_session_locks_mutex = threading.Lock()  # Protects _session_locks dict

# Track last access time for session expiry
_session_last_access: Dict[str, float] = {}

# Default session expiry time (1 hour)
SESSION_EXPIRY_SECONDS = 3600


def get_session_lock(session_id: str) -> threading.Lock:
    """
    Get or create lock for session. Thread-safe via mutex.
    
    Lock instance persists until explicit cleanup via cleanup_session_lock().
    This ensures the same lock instance is always returned for a given session,
    preventing race conditions that could occur with WeakValueDictionary.
    
    Args:
        session_id: Unique identifier for the user session.
        
    Returns:
        threading.Lock instance for the session.
    """
    with _session_locks_mutex:
        if session_id not in _session_locks:
            _session_locks[session_id] = threading.Lock()
        # Update last access time
        _session_last_access[session_id] = time.time()
        return _session_locks[session_id]


def cleanup_session_lock(session_id: str) -> None:
    """
    Remove session lock when session is invalidated.
    
    MUST be called from reset_session_state() to prevent memory leaks.
    Safe to call even if lock doesn't exist.
    
    Args:
        session_id: Unique identifier for the user session.
    """
    with _session_locks_mutex:
        _session_locks.pop(session_id, None)
        _session_last_access.pop(session_id, None)
    logger.debug(f"Session lock cleaned up for {session_id}")


def cleanup_expired_session_locks(max_age_seconds: int = SESSION_EXPIRY_SECONDS) -> int:
    """
    Background task to clean up locks for sessions inactive > max_age.
    
    Operational guidance:
    - Scheduler: Use threading.Timer in app process (simple, no external deps)
    - Frequency: Run every 10 minutes
    - Startup: Register timer on app initialization in main.py
    - Shutdown: Cancel timer gracefully on app shutdown
    - Error handling: Catch all exceptions, log errors, continue (fail-safe)
    - Idempotence: Safe to run concurrently (mutex protects dict)
    - Monitoring: Log cleaned count, emit metric maya_session_locks_cleaned_total
    - Alert: If cleanup fails 3 consecutive times, log critical error
    
    Args:
        max_age_seconds: Maximum age in seconds before session is expired.
        
    Returns:
        Number of locks cleaned up (for metrics).
    """
    cleaned_count = 0
    current_time = time.time()
    
    with _session_locks_mutex:
        expired_sessions = [
            session_id for session_id, last_access in _session_last_access.items()
            if current_time - last_access > max_age_seconds
        ]
        
        for session_id in expired_sessions:
            _session_locks.pop(session_id, None)
            _session_last_access.pop(session_id, None)
            cleaned_count += 1
    
    if cleaned_count > 0:
        logger.info(f"Cleaned up {cleaned_count} expired session locks")
    
    return cleaned_count


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

# =============================================================================
# Backward Compatibility: Global Store and Default Session
# =============================================================================
# For backward compatibility with code that doesn't pass session_id and store,
# we maintain a global store and default session ID.
_global_store: Dict[str, Any] = {}
DEFAULT_SESSION_ID = "default"


def _get_store_and_session(session_id: Optional[str], store: Optional[MutableMapping]) -> Tuple[str, MutableMapping]:
    """
    Get the store and session_id, using defaults for backward compatibility.
    
    Args:
        session_id: Session ID or None for default
        store: Store or None for global store
        
    Returns:
        Tuple of (session_id, store)
    """
    if store is None:
        store = _global_store
    if session_id is None:
        session_id = DEFAULT_SESSION_ID
    return session_id, store


def _deep_copy_defaults() -> Dict[str, Any]:
    """Create a deep copy of all default state to avoid mutation issues."""
    import copy
    return {
        'conversation': copy.deepcopy(DEFAULT_CONVERSATION_STATE),
        'history': copy.deepcopy(DEFAULT_ORDER_HISTORY),
        'current_order': copy.deepcopy(DEFAULT_CURRENT_ORDER),
        'payment': copy.deepcopy(DEFAULT_PAYMENT_STATE)
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
        store[session_id] = _deep_copy_defaults()
    # Handle existing sessions that don't have payment state (migration)
    elif 'payment' not in store[session_id]:
        logger.info(f"Adding payment state to existing session {session_id}")
        import copy
        session_data = store[session_id]
        session_data['payment'] = copy.deepcopy(DEFAULT_PAYMENT_STATE)
        store[session_id] = session_data
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


def initialize_state(session_id: Optional[str] = None, store: Optional[MutableMapping] = None) -> None:
    """
    Initialize or reset state variables for a session.
    
    Args:
        session_id: Session ID to initialize (defaults to "default" for backward compatibility).
        store: Storage backend (defaults to global store for backward compatibility).
    """
    session_id, store = _get_store_and_session(session_id, store)

    # Force reset by overwriting with defaults (deep copy to avoid mutation)
    store[session_id] = _deep_copy_defaults()
    logger.info(f"State initialized for session {session_id}")

def get_conversation_state(session_id: Optional[str] = None, store: Optional[MutableMapping] = None) -> Dict[str, Any]:
    """Get current conversation state."""
    session_id, store = _get_store_and_session(session_id, store)
    data = _get_session_data(session_id, store)
    return data['conversation'].copy()

def get_order_history(session_id: Optional[str] = None, store: Optional[MutableMapping] = None) -> Dict[str, Any]:
    """Get order history."""
    session_id, store = _get_store_and_session(session_id, store)
    data = _get_session_data(session_id, store)
    return data['history']

def get_current_order_state(session_id: Optional[str] = None, store: Optional[MutableMapping] = None) -> List[Dict[str, Any]]:
    """Get current order state."""
    session_id, store = _get_store_and_session(session_id, store)
    data = _get_session_data(session_id, store)
    return data['current_order']['order']

def update_conversation_state(session_id_or_updates: Any = None, store_or_none: Optional[MutableMapping] = None, updates: Optional[Dict[str, Any]] = None) -> None:
    """
    Update conversation state.
    
    Supports both old API: update_conversation_state(updates)
    And new API: update_conversation_state(session_id, store, updates)
    """
    # Detect which API is being used
    if isinstance(session_id_or_updates, dict) and updates is None:
        # Old API: update_conversation_state(updates)
        updates = session_id_or_updates
        session_id, store = _get_store_and_session(None, None)
    else:
        # New API: update_conversation_state(session_id, store, updates)
        session_id, store = _get_store_and_session(session_id_or_updates, store_or_none)
    
    data = _get_session_data(session_id, store)
    data['conversation'].update(updates)
    _save_session_data(session_id, store, data)
    logger.debug(f"Conversation state updated for {session_id}: {updates}")

def update_order_state(action_or_session_id: Any, data_or_store: Any = None, action_or_data: Optional[Any] = None, data: Optional[Any] = None) -> None:
    """
    Update order state based on action.
    
    Supports both old API: update_order_state(action, data)
    And new API: update_order_state(session_id, store, action, data)
    """
    # Detect which API is being used
    if isinstance(action_or_session_id, str) and action_or_session_id in ("add_item", "place_order", "clear_order", "add_tip", "pay_bill"):
        # Old API: update_order_state(action, data)
        action = action_or_session_id
        item_data = data_or_store
        session_id, store = _get_store_and_session(None, None)
    else:
        # New API: update_order_state(session_id, store, action, data)
        session_id, store = _get_store_and_session(action_or_session_id, data_or_store)
        action = action_or_data
        item_data = data
    
    session_data = _get_session_data(session_id, store)
    history = session_data['history']
    current_order = session_data['current_order']
    
    if action == "add_item" and item_data:
        # Add item to current order
        current_order['order'].append(item_data)
        
        # Add to order history
        history['items'].append(item_data.copy())
        history['total_cost'] += item_data['price']
        
        logger.info(f"Added item to order for {session_id}: {item_data['name']}")
        
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
        
    elif action == "add_tip" and item_data:
        # Add tip to order history
        history['tip_amount'] = item_data['amount']
        history['tip_percentage'] = item_data['percentage']
        
        logger.info(f"Tip added for {session_id}: ${item_data['amount']:.2f}")
        
    elif action == "pay_bill":
        # Mark bill as paid
        history['paid'] = True
        
        logger.info(f"Bill paid for {session_id}")
        
    # Save changes
    _save_session_data(session_id, store, session_data)

def reset_session_state(session_id: Optional[str] = None, store: Optional[MutableMapping] = None) -> None:
    """Reset all session state and cleanup session lock."""
    session_id, store = _get_store_and_session(session_id, store)
    # Cleanup session lock to prevent memory leaks
    cleanup_session_lock(session_id)
    initialize_state(session_id, store)
    logger.info(f"Session state reset for {session_id}")

def is_order_finished(session_id: Optional[str] = None, store: Optional[MutableMapping] = None) -> bool:
    """Check if current order is finished."""
    session_id, store = _get_store_and_session(session_id, store)
    data = _get_session_data(session_id, store)
    return data['current_order']['finished']

def get_order_total(session_id: Optional[str] = None, store: Optional[MutableMapping] = None) -> float:
    """Get total cost of current order."""
    session_id, store = _get_store_and_session(session_id, store)
    data = _get_session_data(session_id, store)
    return sum(item['price'] for item in data['current_order']['order'])


# =============================================================================
# Payment State Functions
# =============================================================================

def get_payment_state(session_id: str, store: MutableMapping) -> Dict[str, Any]:
    """
    Get payment state for session.
    
    Args:
        session_id: Unique identifier for the user session.
        store: Mutable mapping to store state.
        
    Returns:
        Copy of the payment state dictionary.
    """
    data = _get_session_data(session_id, store)
    return data['payment'].copy()


def update_payment_state(session_id: str, store: MutableMapping, 
                         updates: Dict[str, Any]) -> None:
    """
    Update payment state with validation.
    
    Args:
        session_id: Unique identifier for the user session.
        store: Mutable mapping to store state.
        updates: Dictionary of fields to update.
        
    Raises:
        PaymentStateValidationError: If updates would result in invalid state.
    """
    data = _get_session_data(session_id, store)
    current_payment = data['payment']
    
    # Check status transition validity if status is being updated
    if 'payment_status' in updates:
        current_status = current_payment['payment_status']
        new_status = updates['payment_status']
        if not is_valid_status_transition(current_status, new_status):
            raise PaymentStateValidationError(
                f"Invalid status transition from '{current_status}' to '{new_status}'"
            )
    
    # Create merged state for validation
    merged_state = current_payment.copy()
    merged_state.update(updates)
    
    # Validate the merged state
    validate_payment_state(merged_state)
    
    # Apply updates
    current_payment.update(updates)
    _save_session_data(session_id, store, data)
    logger.debug(f"Payment state updated for {session_id}: {updates}")


# Error codes for atomic operations
INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
CONCURRENT_MODIFICATION = "CONCURRENT_MODIFICATION"


def atomic_order_update(
    session_id: str, 
    store: MutableMapping,
    item_price: float,
    expected_version: Optional[int] = None
) -> Tuple[bool, str, float]:
    """
    Atomically check balance, deduct, and add to tab.
    
    This function acquires the session lock, checks if the user has sufficient
    balance, and if so, atomically deducts from balance and adds to tab.
    Uses optimistic locking with version checks.
    
    Args:
        session_id: Unique identifier for the user session.
        store: Mutable mapping to store state.
        item_price: Price of the item to add.
        expected_version: Expected version for optimistic locking. If None,
                         reads current version (for first-time callers).
    
    Returns:
        Tuple of (success, error_code_or_empty, new_balance):
        - On success: (True, "", new_balance)
        - On insufficient funds: (False, "INSUFFICIENT_FUNDS", current_balance)
        - On version mismatch: (False, "CONCURRENT_MODIFICATION", current_balance)
    
    Note:
        On CONCURRENT_MODIFICATION, the client should ask the user to retry.
        No automatic retry is performed.
    """
    lock = get_session_lock(session_id)
    
    with lock:
        data = _get_session_data(session_id, store)
        payment = data['payment']
        current_balance = payment['balance']
        current_version = payment['version']
        
        # Check version if expected_version is provided
        if expected_version is not None and current_version != expected_version:
            logger.warning(
                f"Version mismatch for {session_id}: "
                f"expected {expected_version}, got {current_version}"
            )
            return (False, CONCURRENT_MODIFICATION, current_balance)
        
        # Check sufficient funds
        if current_balance < item_price:
            logger.info(
                f"Insufficient funds for {session_id}: "
                f"balance={current_balance}, price={item_price}"
            )
            return (False, INSUFFICIENT_FUNDS, current_balance)
        
        # Atomically update balance, tab, and version
        new_balance = current_balance - item_price
        new_tab = payment['tab_total'] + item_price
        new_version = current_version + 1
        
        payment['balance'] = new_balance
        payment['tab_total'] = new_tab
        payment['version'] = new_version
        
        _save_session_data(session_id, store, data)
        
        logger.info(
            f"Order update for {session_id}: "
            f"price={item_price}, new_balance={new_balance}, "
            f"new_tab={new_tab}, version={new_version}"
        )
        
        return (True, "", new_balance)


def check_sufficient_funds(
    session_id: str, 
    store: MutableMapping, 
    amount: float
) -> Tuple[bool, float]:
    """
    Check if user has sufficient balance.
    
    Args:
        session_id: Unique identifier for the user session.
        store: Mutable mapping to store state.
        amount: Amount to check against balance.
        
    Returns:
        Tuple of (has_funds, current_balance).
    """
    payment = get_payment_state(session_id, store)
    current_balance = payment['balance']
    return (current_balance >= amount, current_balance)


def atomic_payment_complete(session_id: str, store: MutableMapping) -> bool:
    """
    Atomically reset tab and mark as paid.
    
    Args:
        session_id: Unique identifier for the user session.
        store: Mutable mapping to store state.
        
    Returns:
        True if successful, False otherwise.
    """
    lock = get_session_lock(session_id)
    
    with lock:
        data = _get_session_data(session_id, store)
        payment = data['payment']
        
        # Reset tab and mark as completed
        payment['tab_total'] = 0.00
        payment['payment_status'] = 'completed'
        payment['needs_reconciliation'] = False
        payment['version'] += 1
        
        _save_session_data(session_id, store, data)
        
        logger.info(f"Payment completed for {session_id}")
        
        return True