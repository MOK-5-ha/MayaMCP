"""Helper functions for conversation management."""

from typing import Dict
from ..config.logging_config import get_logger

logger = get_logger(__name__)

def detect_order_inquiry(user_input: str) -> Dict[str, any]:
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
    
    for intent, patterns in intent_patterns.items():
        for pattern in patterns:
            if pattern in user_text:
                # Direct match has highest priority
                return {'intent': intent, 'confidence': 1.0}
        
        # Check for partial word matches
        pattern_words = set()
        for pattern in patterns:
            pattern_words.update(pattern.split())
        
        # Count matching words
        matching_words = sum(1 for word in pattern_words if word in user_text.split())
        if matching_words > 0:
            score = matching_words / len(user_text.split())
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

def is_casual_conversation(user_input: str) -> bool:
    """
    Determine if user input is casual conversation vs order-related.
    
    Args:
        user_input: User's input text
        
    Returns:
        True if this appears to be casual conversation
    """
    order_related_keywords = [
        'order', 'menu', 'drink', 'beer', 'cocktail', 'price', 
        'cost', 'bill', 'payment', 'tip'
    ]
    
    user_text = user_input.lower()
    for keyword in order_related_keywords:
        if keyword in user_text:
            return False
    
    return True