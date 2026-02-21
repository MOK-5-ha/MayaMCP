"""Helper functions for conversation management."""

from typing import Dict, List, Any
import re
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
        
        # Count matching words (pre-compute split operation with set for O(1) lookups)
        user_words_set = set(user_text.split())
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