"""Conversation phase management for Maya."""

from typing import Dict, Any
from ..utils.state_manager import get_conversation_state, update_conversation_state
from ..utils.helpers import determine_next_phase
from ..config.logging_config import get_logger

logger = get_logger(__name__)

class ConversationPhaseManager:
    """Manages conversation phases and state transitions."""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    def get_current_phase(self) -> str:
        """Get the current conversation phase."""
        state = get_conversation_state()
        return state['phase']
    
    def increment_turn(self) -> None:
        """Increment the conversation turn count."""
        state = get_conversation_state()
        update_conversation_state({'turn_count': state['turn_count'] + 1})
    
    def increment_small_talk(self) -> None:
        """Increment the small talk counter."""
        state = get_conversation_state()
        if state['phase'] == 'small_talk':
            update_conversation_state({'small_talk_count': state['small_talk_count'] + 1})
    
    def handle_order_placed(self) -> None:
        """Handle state updates when an order is placed."""
        state = get_conversation_state()
        update_conversation_state({
            'last_order_time': state['turn_count'],
            'small_talk_count': 0
        })
    
    def update_phase(self, order_placed: bool = False) -> str:
        """
        Update conversation phase based on current state and actions.
        
        Args:
            order_placed: Whether an order was just placed
            
        Returns:
            New conversation phase
        """
        current_state = get_conversation_state()
        
        # Handle order placement
        if order_placed:
            self.handle_order_placed()
            current_state = get_conversation_state()  # Get updated state
        
        # Determine next phase
        next_phase = determine_next_phase(current_state, order_placed)
        
        # Update phase
        update_conversation_state({'phase': next_phase})
        
        self.logger.info(f"Conversation phase updated: {current_state['phase']} -> {next_phase}")
        
        return next_phase
    
    def should_use_rag(self, user_input: str) -> bool:
        """
        Determine if RAG should be used for this input.
        
        Args:
            user_input: User's input text
            
        Returns:
            True if RAG should be used
        """
        from ..utils.helpers import is_casual_conversation
        
        # Use RAG for casual conversation
        return is_casual_conversation(user_input)
    
    def reset_phase(self) -> None:
        """Reset conversation phase to greeting."""
        update_conversation_state({
            'phase': 'greeting',
            'turn_count': 0,
            'small_talk_count': 0,
            'last_order_time': 0
        })
        self.logger.info("Conversation phase reset to greeting")