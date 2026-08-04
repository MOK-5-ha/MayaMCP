"""Helper functions for conversation management."""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..config.logging_config import get_logger

logger = get_logger(__name__)


def extract_session_id(request: Any = None, default: str = "default") -> str:
    """Extract session_id from Gradio Request object, dictionary, or string with fallback.

    Args:
        request: Gradio request object, dictionary containing session details, or session string.
        default: Fallback session ID string.

    Returns:
        Extracted session ID or fallback string.
    """
    if request is None:
        return default
    if isinstance(request, str):
        stripped = request.strip()
        return stripped if stripped else default
    if hasattr(request, "session_hash") and getattr(request, "session_hash", None):
        return request.session_hash
    if isinstance(request, dict):
        return request.get("session_hash") or request.get("session_id") or default
    return default


def format_currency(amount: Optional[float], default: float = 0.0) -> str:
    """Format numeric value as USD currency string (e.g. '$12.50').

    Args:
        amount: Floating-point or numeric monetary value.
        default: Fallback numeric value if amount is None.

    Returns:
        Formatted currency string.
    """
    val = default if amount is None else safe_float(amount, default=default)
    return f"${val:.2f}"


def safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert value to float without raising exceptions.

    Args:
        val: Value to convert to float.
        default: Fallback float if conversion fails.

    Returns:
        Converted float or default value.
    """
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def mask_api_key(key: Optional[str], visible_chars: int = 4, suffix_chars: int = 4) -> str:
    """Obfuscate API key strings for sensitive logging or UI output.

    Args:
        key: API key string.
        visible_chars: Number of visible prefix characters to display.
        suffix_chars: Number of visible suffix characters to display.

    Returns:
        Masked API key string (e.g., 'AIza...key').
    """
    if not key or not isinstance(key, str) or len(key.strip()) < (visible_chars + suffix_chars):
        return "****"
    cleaned = key.strip()
    return f"{cleaned[:visible_chars]}...{cleaned[-suffix_chars:]}"



def build_response_dict(
    success: bool,
    message: str = "",
    data: Optional[Dict[str, Any]] = None,
    error_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a standardized status/response dictionary.

    Args:
        success: Whether the operation succeeded.
        message: Descriptive response message.
        data: Optional payload dictionary.
        error_code: Optional error code string.

    Returns:
        Dictionary with status, success, message, data, error_code, and timestamp.
    """
    res: Dict[str, Any] = {
        "status": "success" if success else "error",
        "success": success,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if data is not None:
        res["data"] = data
    if error_code is not None:
        res["error_code"] = error_code
    return res


def normalize_text(text: Optional[str]) -> str:
    """Lowercase, strip whitespace, and normalize spaces in string input.

    Args:
        text: Input string.

    Returns:
        Cleaned, lowercased string.
    """
    if not text or not isinstance(text, str):
        return ""
    return " ".join(text.lower().strip().split())


def detect_order_inquiry(user_input: str) -> Dict[str, Any]:
    """
    Detect if the user is asking about their order or bill in conversational ways.
    
    Args:
        user_input: User's input text
        
    Returns:
        Dictionary with intent and confidence.
    """
    user_text = user_input.lower()

    # Intent patterns with keywords
    intent_patterns = {
        'show_order': [
            'show my order', 'what did i order', 'what have i ordered',
            "what's in my order", 'what is in my order', 'my current order',
            'order so far', 'view my order', 'see my order'
        ],
        'get_bill': [
            'bill', 'check please', 'check, please', 'tab', 'pay', 'total',
            'how much', 'what do i owe', 'my total', 'my bill', 'the total',
            'the bill', "what's the damage", "what's the total", 'what is the total',
            'how much is my bill', 'how much do i owe', "what's my tab",
            'what is my tab', "what's my total", 'what is my total'
        ],
        'pay_bill': [
            'pay my bill', 'pay the bill', 'pay my tab', 'pay the tab',
            "i'll pay now", 'pay now', 'settle my bill', 'settle the bill',
            'settle up', 'cash out', 'close my tab', 'close the tab'
        ]
    }

    # Check for matches
    matched_intent = None
    highest_score = 0

    # Pre-compute user words set once, handling whitespace-only input
    user_words_set = set(user_text.strip().split())
    if not user_words_set:
        return {'intent': None, 'confidence': 0}

    for intent, patterns in intent_patterns.items():
        for pattern in patterns:
            if pattern in user_text:
                # Direct match has highest priority
                return {'intent': intent, 'confidence': 1.0}

        # Check for partial word matches
        pattern_words = set()
        for pattern in patterns:
            pattern_words.update(pattern.split())

        # Count matching words (pre-compute split operation with set for O(1) lookups)
        matching_words = sum(1 for word in pattern_words if word in user_words_set)
        if matching_words > 0:
            score = matching_words / len(user_words_set)
            if score > highest_score:
                highest_score = score
                matched_intent = intent

    # Only return intent if confidence is high enough and makes sense
    if matched_intent and highest_score >= 0.5:  # Increased threshold
        return {'intent': matched_intent, 'confidence': highest_score}
    else:
        return {'intent': None, 'confidence': 0}

def determine_next_phase(current_state: Dict, order_placed: bool) -> str:
    """
    Determine the next conversation phase based on current state and whether an order was placed.
    
    Args:
        current_state: Current conversation state
        order_placed: Whether an order was just placed
        
    Returns:
        Next conversation phase
    """
    phase = current_state['phase']
    small_talk_count = current_state['small_talk_count']

    # If this is the first interaction, move from greeting to order taking
    if phase == 'greeting':
        return 'order_taking'

    # If an order was just placed, transition to small talk
    if order_placed:
        current_state['small_talk_count'] = 0
        return 'small_talk'

    # If we're taking an order, stay in that phase
    if phase == 'order_taking':
        return 'order_taking'

    # If we're in small talk phase
    if phase == 'small_talk':
        if small_talk_count >= 4:
            return 'reorder_prompt'
        return 'small_talk'

    # If we just prompted for a reorder
    if phase == 'reorder_prompt':
        # Go back to small talk regardless of whether they ordered
        current_state['small_talk_count'] = 0
        return 'small_talk'

    # Default fallback
    return 'small_talk'

def detect_speech_acts(user_input: str, conversation_context: List[str] = None) -> Dict[str, Any]:
    """
    Detect speech acts using Austin's framework for better intent recognition.
    
    Args:
        user_input: Current user input
        conversation_context: Previous conversation messages for context
        
    Returns:
        Dictionary with speech act type, intent, and confidence
    """
    user_text = user_input.lower().strip()
    context = conversation_context or []

    # Extract recent drink mentions from context
    drink_context = extract_drink_context(context)

    # Speech act patterns based on Austin's theory
    speech_acts = {
        'commissive': {  # Commitments to action (I will/can/shall)
            'patterns': [
                r'\bi can\b.*(?:get|make|prepare|serve)',
                r'\bi will\b.*(?:get|make|prepare|serve)',
                r'\bi shall\b.*(?:get|make|prepare|serve)',
                r'\bcertainly\b.*(?:get|make|prepare|serve)',
                r'\bof course\b.*(?:get|make|prepare|serve)',
                r'\babsolutely\b.*(?:get|make|prepare|serve)',
                r'\bsure\b.*(?:get|make|prepare|serve)',
                r'\bcoming right up\b',
                r'\bone \w+ coming up\b'
            ],
            'order_indicators': ['whiskey', 'beer', 'cocktail', 'drink', 'beverage',
                               'old fashioned', 'manhattan', 'martini', 'rocks', 'neat']
        },
        'assertive': {  # Statements about order completion
            'patterns': [
                r'\bhere is\b.*(?:your|the)',
                r'\bhere\'s\b.*(?:your|the)',
                r'\bthis is\b.*(?:your|the)',
                r'\bthat was\b.*(?:your|the)',
                r'\byour \w+ is ready\b',
                r'\bone \w+ for you\b',
                r'\bthis is your\b'
            ],
            'order_indicators': ['drink', 'order', 'whiskey', 'cocktail', 'beverage', 'manhattan']
        },
        'directive': {  # Direct requests
            'patterns': [
                r'\bplease\b',
                r'\bcan you\b',
                r'\bwould you\b',
                r'\bi want\b',
                r'\bi need\b',
                r'\bi\'d like\b',
                r'\bmay i have\b'
            ],
            'order_indicators': ['whiskey', 'beer', 'cocktail', 'drink', 'rocks', 'manhattan']
        }
    }

    detected_acts = []

    for act_type, config in speech_acts.items():
        for pattern in config['patterns']:
            if re.search(pattern, user_text):
                # Check if order indicators are present
                order_confidence = 0
                for indicator in config['order_indicators']:
                    if indicator in user_text:
                        order_confidence += 0.3
                    # Also check drink context from conversation
                    if drink_context and indicator in drink_context:
                        order_confidence += 0.2

                # Special case: commissive acts with drink context get high confidence
                if act_type == 'commissive' and drink_context:
                    order_confidence = min(1.0, order_confidence + 0.5)

                detected_acts.append({
                    'speech_act': act_type,
                    'pattern': pattern,
                    'confidence': min(1.0, order_confidence),
                    'drink_context': drink_context
                })

    # Return highest confidence detection
    if detected_acts:
        best_act = max(detected_acts, key=lambda x: x['confidence'])
        if best_act['confidence'] >= 0.3:  # Threshold for action
            return {
                'intent': 'order_confirmation' if best_act['speech_act'] in ('commissive', 'assertive') else 'order_request',
                'speech_act': best_act['speech_act'],
                'confidence': best_act['confidence'],
                'drink_context': best_act['drink_context']
            }

    return {'intent': None, 'speech_act': None, 'confidence': 0, 'drink_context': drink_context}

def extract_drink_context(conversation_history: List[str]) -> str:
    """
    Extract drink mentions from recent conversation history.
    
    Args:
        conversation_history: List of recent conversation messages
        
    Returns:
        String containing drink context or empty string
    """
    if not conversation_history:
        return ""

    drinks = ['whiskey', 'beer', 'cocktail', 'wine', 'vodka', 'gin', 'rum', 'tequila',
              'old fashioned', 'manhattan', 'martini', 'negroni', 'mojito', 'rocks', 'neat']

    # Look at last 3 messages for drink context
    recent_messages = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history

    found_drinks = []
    for message in recent_messages:
        message_lower = message.lower()
        for drink in drinks:
            if drink in message_lower and drink not in found_drinks:
                found_drinks.append(drink)

    return " ".join(found_drinks)

def is_casual_conversation(user_input: str) -> bool:
    """
    Determine if user input is casual conversation vs order-related.
    Enhanced with speech act detection.
    
    Args:
        user_input: User's input text
        
    Returns:
        True if this appears to be casual conversation
    """
    # First check for speech acts that indicate ordering
    speech_act_result = detect_speech_acts(user_input)
    if speech_act_result['intent'] in ['order_confirmation', 'order_request']:
        return False

    order_related_keywords = [
        'order', 'menu', 'drink', 'beer', 'cocktail', 'price',
        'cost', 'bill', 'payment', 'tip'
    ]

    user_text = user_input.lower()
    for keyword in order_related_keywords:
        if keyword in user_text:
            return False

    return True


def append_to_history(
    history: List[Dict[str, str]], user_text: str, assistant_text: str
) -> List[Dict[str, str]]:
    """
    Append user and assistant messages to history and return a new list.
    """
    updated = list(history)
    updated.append({'role': 'user', 'content': user_text})
    updated.append({'role': 'assistant', 'content': assistant_text})
    return updated


def get_overlay_payment_data(
    payment_state: Dict[str, Any]
) -> Tuple[float, float, Optional[int], float]:
    """
    Get payment data formatted for tab overlay.
    
    Returns:
        Tuple of (tab_total, balance, tip_percentage, tip_amount)
    """
    return (
        payment_state['tab_total'],
        payment_state['balance'],
        payment_state['tip_percentage'],
        payment_state['tip_amount']
    )
