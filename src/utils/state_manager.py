"""State management for conversation and order tracking."""

import re
import threading
import time
from typing import Dict, List, Any, Optional, MutableMapping, Tuple, Literal
from typing_extensions import TypedDict
from ..config.logging_config import get_logger
from ..security.encryption import get_encryption_manager

logger = get_logger(__name__)


# =============================================================================
# Payment State Types and Validation
# =============================================================================

class PaymentState(TypedDict):
    """Payment state schema with strict typing."""
    balance: float          # >= 0, default: 1000.00
    tab_total: float        # >= 0, default: 0.00
    tip_percentage: Optional[Literal[10, 15, 20]]  # None when no tip selected
    tip_amount: float       # >= 0, default: 0.00
    stripe_payment_id: Optional[str]  # None or Stripe ID pattern: ^(plink_|pi_)[a-zA-Z0-9]+$
    payment_status: Literal['pending', 'processing', 'completed']  # default: 'pending'
    idempotency_key: Optional[str]    # None or format: {session_id}_{unix_timestamp}
    version: int            # >= 0, default: 0
    needs_reconciliation: bool  # default: False


# Valid tip percentages
VALID_TIP_PERCENTAGES = {10, 15, 20}


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
    'tip_percentage': None,
    'tip_amount': 0.00,
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
        required_fields = {'balance', 'tab_total', 'tip_percentage', 'tip_amount',
                          'stripe_payment_id', 'payment_status', 'idempotency_key', 
                          'version', 'needs_reconciliation'}
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
    
    # Validate tip_percentage (None or one of {10, 15, 20})
    if 'tip_percentage' in state:
        tip_pct = state['tip_percentage']
        if tip_pct is not None and tip_pct not in VALID_TIP_PERCENTAGES:
            raise PaymentStateValidationError(
                f"tip_percentage must be None or one of {VALID_TIP_PERCENTAGES}, got {tip_pct}"
            )
    
    # Validate tip_amount >= 0
    if 'tip_amount' in state:
        if not isinstance(state['tip_amount'], (int, float)):
            raise PaymentStateValidationError("tip_amount must be a number")
        if state['tip_amount'] < 0:
            raise PaymentStateValidationError(f"tip_amount must be >= 0, got {state['tip_amount']}")
    
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

DEFAULT_API_KEY_STATE = {
    'gemini_key': None,
    'cartesia_key': None,
    'keys_validated': False,
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
        'payment': copy.deepcopy(DEFAULT_PAYMENT_STATE),
        'api_keys': copy.deepcopy(DEFAULT_API_KEY_STATE),
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
        return store[session_id]

    import copy
    session_data = store[session_id]
    needs_update = False

    # Handle migration for session data (Requirement: 2.2, 7.2, 7.3, 3.1)
    
    # 1. Ensure 'api_keys' exists
    if 'api_keys' not in session_data:
        logger.info(f"Adding api_keys state to existing session {session_id}")
        session_data['api_keys'] = copy.deepcopy(DEFAULT_API_KEY_STATE)
        needs_update = True
        
    # 2. Ensure 'payment' exists
    if 'payment' not in session_data:
        logger.info(f"Adding payment state to existing session {session_id}")
        session_data['payment'] = copy.deepcopy(DEFAULT_PAYMENT_STATE)
        needs_update = True
    else:
        # 3. Ensure tip fields exist within existing payment state
        payment = session_data['payment']
        payment_needs_update = False
        if 'tip_percentage' not in payment:
            payment['tip_percentage'] = None
            payment_needs_update = True
        if 'tip_amount' not in payment:
            payment['tip_amount'] = 0.00
            payment_needs_update = True
        
        if payment_needs_update:
            logger.info(f"Adding missing tip fields to existing session {session_id}")
            needs_update = True

    if needs_update:
        store[session_id] = session_data

    return session_data

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
    return data['history'].copy()

def get_current_order_state(session_id: Optional[str] = None, store: Optional[MutableMapping] = None) -> List[Dict[str, Any]]:
    """Get current order state."""
    session_id, store = _get_store_and_session(session_id, store)
    data = _get_session_data(session_id, store)
    return data['current_order']['order'].copy()

def update_conversation_state(session_id: Optional[str] = None, store: Optional[MutableMapping] = None, updates: Optional[Dict[str, Any]] = None) -> None:
    """Update conversation state."""
    if updates is None:
        logger.warning("update_conversation_state called with updates=None")
        return
    session_id, store = _get_store_and_session(session_id, store)
    
    lock = get_session_lock(session_id)
    with lock:
        data = _get_session_data(session_id, store)
        data['conversation'].update(updates)
        _save_session_data(session_id, store, data)
    logger.debug(f"Conversation state updated for {session_id}: {updates}")

def update_order_state(session_id: Optional[str] = None, store: Optional[MutableMapping] = None, action: str = "", item_data: Optional[Any] = None) -> None:
    """Update order state based on action."""
    session_id, store = _get_store_and_session(session_id, store)
    
    lock = get_session_lock(session_id)
    with lock:
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
    # Cleanup cached LLM/TTS clients for this session
    try:
        from ..llm.session_registry import clear_session_clients
        clear_session_clients(session_id)
    except Exception:
        logger.error(
            "Failed to clear session clients for %s",
            session_id,
            exc_info=True,
        )
    initialize_state(session_id, store)
    logger.info(f"Session state reset for {session_id}")

def is_order_finished(session_id: Optional[str] = None, store: Optional[MutableMapping] = None) -> bool:
    """Check if current order is finished."""
    session_id, store = _get_store_and_session(session_id, store)
    data = _get_session_data(session_id, store)
    return data['current_order']['finished']

# =============================================================================
# Payment State Functions
# =============================================================================

def calculate_tip(tab_total: float, percentage: int) -> float:
    """
    Calculate tip amount from tab total and percentage.
    
    Args:
        tab_total: Current tab amount (drinks only, no previous tip)
        percentage: 10, 15, or 20
        
    Returns:
        Tip amount rounded to 2 decimal places
        
    Raises:
        ValueError: If percentage is not in {10, 15, 20}
    """
    if percentage not in VALID_TIP_PERCENTAGES:
        raise ValueError(f"percentage must be one of {VALID_TIP_PERCENTAGES}, got {percentage}")
    
    tip = tab_total * (percentage / 100)
    return round(tip, 2)


def set_tip(
    session_id: str, 
    store: MutableMapping, 
    percentage: Optional[int]
) -> Tuple[float, float]:
    """
    Set tip percentage and calculate tip amount.
    
    Implements toggle behavior: if the same percentage is already selected,
    calling set_tip with that percentage will remove the tip.
    
    Args:
        session_id: Unique identifier for the user session.
        store: Mutable mapping to store state.
        percentage: 10, 15, 20 to set tip, or None to remove tip
        
    Returns:
        Tuple of (tip_amount, total) where total = tab_total + tip_amount
        
    Raises:
        ValueError: If percentage is not None and not in {10, 15, 20}
    """
    # Validate percentage
    if percentage is not None and percentage not in VALID_TIP_PERCENTAGES:
        raise ValueError(f"percentage must be None or one of {VALID_TIP_PERCENTAGES}, got {percentage}")
    
    lock = get_session_lock(session_id)
    
    with lock:
        data = _get_session_data(session_id, store)
        payment = data['payment']
        tab_total = payment['tab_total']
        current_percentage = payment['tip_percentage']
        
        # Toggle behavior: if same percentage is selected, remove tip
        if percentage is not None and percentage == current_percentage:
            payment['tip_percentage'] = None
            payment['tip_amount'] = 0.00
            logger.info(f"Tip removed for {session_id} (toggle)")
        elif percentage is None:
            # Explicitly remove tip
            payment['tip_percentage'] = None
            payment['tip_amount'] = 0.00
            logger.info(f"Tip removed for {session_id}")
        else:
            # Set new tip
            tip_amount = calculate_tip(tab_total, percentage)
            payment['tip_percentage'] = percentage
            payment['tip_amount'] = tip_amount
            logger.info(f"Tip set for {session_id}: {percentage}% = ${tip_amount:.2f}")
        
        _save_session_data(session_id, store, data)
        
        return (payment['tip_amount'], tab_total + payment['tip_amount'])


def get_payment_total(session_id: str, store: MutableMapping) -> float:
    """
    Get total payment amount including tab and tip.
    
    Args:
        session_id: Unique identifier for the user session.
        store: Mutable mapping to store state.
        
    Returns:
        Total amount (tab_total + tip_amount)
    """
    payment = get_payment_state(session_id, store)
    return payment['tab_total'] + payment['tip_amount']


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
    session_id, store = _get_store_and_session(session_id, store)
    
    lock = get_session_lock(session_id)
    with lock:
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


def atomic_payment_complete(session_id: str, store: MutableMapping) -> bool:
    """
    Atomically reset tab, tip, and mark as paid.
    
    Args:
        session_id: Unique identifier for the user session.
        store: Mutable mapping to store state.
        
    Returns:
        True if successful, False if an exception occurs.
    """
    lock = get_session_lock(session_id)
    
    with lock:
        try:
            data = _get_session_data(session_id, store)
            payment = data['payment']
            
            # Reset tab, tip, and mark as completed
            payment['tab_total'] = 0.00
            payment['tip_percentage'] = None
            payment['tip_amount'] = 0.00
            payment['payment_status'] = 'completed'
            payment['needs_reconciliation'] = False
            payment['version'] += 1
            
            _save_session_data(session_id, store, data)
            
            logger.info(f"Payment completed for {session_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete payment for {session_id}: {str(e)}")
            return False


# =============================================================================
# API Key State Functions (BYOK)
# =============================================================================

def get_api_key_state(session_id: str, store: MutableMapping) -> Dict[str, Any]:
    """Get API key state for session (decrypted).
    
    Args:
        session_id: Unique identifier for the user session.
        store: Mutable mapping to store state.

    Returns:
        Copy of the API key state dictionary with decrypted keys.
    """
    lock = get_session_lock(session_id)
    encryption_manager = get_encryption_manager()
    
    with lock:
        data = _get_session_data(session_id, store)
        state = data['api_keys'].copy()
        
        # Decrypt keys if present
        # We catch broad exceptions from decryption but log specific details
        # to avoid crashing on corrupted or key-mismatched data.
        if state.get('gemini_key'):
            try:
                state['gemini_key'] = encryption_manager.decrypt(state['gemini_key'])
            except Exception as e:
                logger.warning(f"Failed to decrypt gemini_key for {session_id}: {str(e)}")
                state['gemini_key'] = None
                 
        if state.get('cartesia_key'):
            try:
                state['cartesia_key'] = encryption_manager.decrypt(state['cartesia_key'])
            except Exception as e:
                logger.warning(f"Failed to decrypt cartesia_key for {session_id}: {str(e)}")
                state['cartesia_key'] = None
                 
    return state


def set_api_keys(
    session_id: str,
    store: MutableMapping,
    gemini_key: str,
    cartesia_key: Optional[str] = None,
) -> None:
    """Store user-provided API keys for a session (encrypted).

    Args:
        session_id: Unique identifier for the user session.
        store: Mutable mapping to store state.
        gemini_key: User's Gemini API key.
        cartesia_key: User's Cartesia API key (optional).
    """
    lock = get_session_lock(session_id)
    encryption_manager = get_encryption_manager()

    with lock:
        data = _get_session_data(session_id, store)
        
        # Encrypt keys before storage
        stripped_gemini = gemini_key.strip() if gemini_key else None
        encrypted_gemini = encryption_manager.encrypt(stripped_gemini) if stripped_gemini else None
        
        encrypted_cartesia = None
        if cartesia_key and cartesia_key.strip():
             encrypted_cartesia = encryption_manager.encrypt(cartesia_key.strip())
             
        data['api_keys'] = {
            'gemini_key': encrypted_gemini,
            'cartesia_key': encrypted_cartesia,
            'keys_validated': True,
        }
        _save_session_data(session_id, store, data)

    logger.info(f"API keys stored (encrypted) for session {session_id}")


def has_valid_keys(session_id: str, store: MutableMapping) -> bool:
    """Check whether a session has validated API keys.

    Args:
        session_id: Unique identifier for the user session.
        store: Mutable mapping to store state.

    Returns:
        True if the session has at least a validated Gemini key.
    """
    data = _get_session_data(session_id, store)
    api_keys = data.get('api_keys', {})
    return bool(api_keys.get('keys_validated') and api_keys.get('gemini_key'))