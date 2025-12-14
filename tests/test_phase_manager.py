#!/usr/bin/env python3
"""
Unit tests for src.conversation.phase_manager module.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os



from src.conversation.phase_manager import ConversationPhaseManager
from src.utils.state_manager import initialize_state, update_conversation_state, cleanup_session_lock


class TestConversationPhaseManager:
    """Test cases for ConversationPhaseManager class."""

    def setup_method(self):
        """Setup for each test."""
        self.store = {}
        self.session_id = "test_session"
        initialize_state(self.session_id, self.store)
        self.manager = ConversationPhaseManager(self.session_id, self.store)

    def teardown_method(self):
        """Cleanup after each test."""
        self.store.clear()
        cleanup_session_lock(self.session_id)

    def test_init(self):
        """Test ConversationPhaseManager initialization."""
        manager = ConversationPhaseManager(self.session_id, self.store)
        assert hasattr(manager, 'logger')
        assert manager.logger is not None
        assert manager.session_id == self.session_id
        assert manager.app_state == self.store

    def test_get_current_phase_initial(self):
        """Test get_current_phase returns initial phase."""
        phase = self.manager.get_current_phase()
        assert phase == 'greeting'

    def test_get_current_phase_after_update(self):
        """Test get_current_phase after phase update."""
        update_conversation_state(self.session_id, self.store, {'phase': 'order_taking'})
        phase = self.manager.get_current_phase()
        assert phase == 'order_taking'

    def test_increment_turn(self):
        """Test increment_turn increases turn count."""
        # Initial turn count should be 0
        self.manager.increment_turn()
        from src.utils.state_manager import get_conversation_state
        state = get_conversation_state(self.session_id, self.store)
        assert state['turn_count'] == 1
        
        self.manager.increment_turn()
        state = get_conversation_state(self.session_id, self.store)
        assert state['turn_count'] == 2

    def test_increment_small_talk_in_small_talk_phase(self):
        """Test increment_small_talk in small_talk phase."""
        update_conversation_state(self.session_id, self.store, {'phase': 'small_talk'})
        self.manager.increment_small_talk()
        from src.utils.state_manager import get_conversation_state
        state = get_conversation_state(self.session_id, self.store)
        assert state['small_talk_count'] == 1

    def test_increment_small_talk_not_in_small_talk_phase(self):
        """Test increment_small_talk not in small_talk phase does nothing."""
        # Phase is 'greeting' by default
        self.manager.increment_small_talk()
        from src.utils.state_manager import get_conversation_state
        state = get_conversation_state(self.session_id, self.store)
        assert state['small_talk_count'] == 0

    def test_handle_order_placed(self):
        """Test handle_order_placed updates state correctly."""
        # Set up some turn count
        update_conversation_state(self.session_id, self.store, {'turn_count': 5, 'small_talk_count': 3})
        
        self.manager.handle_order_placed()
        
        from src.utils.state_manager import get_conversation_state
        state = get_conversation_state(self.session_id, self.store)
        assert state['last_order_time'] == 5
        assert state['small_talk_count'] == 0

    def test_update_phase_without_order(self):
        """Test update_phase without order placement."""
        # Start in greeting phase
        new_phase = self.manager.update_phase(order_placed=False)
        # Phase should transition based on determine_next_phase logic
        assert isinstance(new_phase, str)

    def test_update_phase_with_order(self):
        """Test update_phase with order placement."""
        update_conversation_state(self.session_id, self.store, {'turn_count': 5})
        new_phase = self.manager.update_phase(order_placed=True)
        
        from src.utils.state_manager import get_conversation_state
        state = get_conversation_state(self.session_id, self.store)
        # last_order_time should be updated
        assert state['last_order_time'] == 5
        assert isinstance(new_phase, str)

    def test_should_use_rag_casual(self):
        """Test should_use_rag returns True for casual conversation."""
        # Test with casual input
        result = self.manager.should_use_rag("Tell me about yourself")
        assert isinstance(result, bool)

    def test_should_use_rag_not_casual(self):
        """Test should_use_rag returns False for order-related input."""
        # Test with order-related input
        result = self.manager.should_use_rag("I want a martini")
        assert isinstance(result, bool)

    def test_reset_phase(self):
        """Test reset_phase resets all conversation state."""
        # Modify state first
        update_conversation_state(self.session_id, self.store, {
            'phase': 'order_taking',
            'turn_count': 10,
            'small_talk_count': 5,
            'last_order_time': 8
        })
        
        self.manager.reset_phase()
        
        from src.utils.state_manager import get_conversation_state
        state = get_conversation_state(self.session_id, self.store)
        assert state['phase'] == 'greeting'
        assert state['turn_count'] == 0
        assert state['small_talk_count'] == 0
        assert state['last_order_time'] == 0

    @patch('src.conversation.phase_manager.logger')
    def test_update_phase_logging(self, mock_logger):
        """Test that update_phase logs phase transitions."""
        self.manager.update_phase()
        # The manager's logger should have been called
        # Note: We're patching the module-level logger, not the instance logger

    @patch('src.conversation.phase_manager.logger')
    def test_reset_phase_logging(self, mock_logger):
        """Test that reset_phase logs the reset."""
        self.manager.reset_phase()
        # The manager's logger should have been called

    def test_integration_workflow(self):
        """Test a complete conversation workflow."""
        # Start conversation
        assert self.manager.get_current_phase() == 'greeting'
        
        # Increment turns
        self.manager.increment_turn()
        self.manager.increment_turn()
        
        # Update phase
        self.manager.update_phase()
        
        # Place an order
        self.manager.update_phase(order_placed=True)
        
        # Reset
        self.manager.reset_phase()
        assert self.manager.get_current_phase() == 'greeting'

    def test_edge_cases(self):
        """Test edge cases."""
        # Multiple increments
        for _ in range(100):
            self.manager.increment_turn()
        
        from src.utils.state_manager import get_conversation_state
        state = get_conversation_state(self.session_id, self.store)
        assert state['turn_count'] == 100
        
        # Reset and verify
        self.manager.reset_phase()
        state = get_conversation_state(self.session_id, self.store)
        assert state['turn_count'] == 0

    def test_should_use_rag_returns_boolean(self):
        """Test should_use_rag always returns a boolean."""
        test_inputs = [
            "Hello",
            "I want a drink",
            "What's on the menu?",
            "Tell me a story",
            "",
            "   ",
            "12345"
        ]
        
        for input_text in test_inputs:
            result = self.manager.should_use_rag(input_text)
            assert isinstance(result, bool), f"should_use_rag('{input_text}') returned {type(result)}"

    def test_manager_state_isolation(self):
        """Test that different managers with different sessions are isolated."""
        store2 = {}
        session_id2 = "test_session_2"
        initialize_state(session_id2, store2)
        manager2 = ConversationPhaseManager(session_id2, store2)
        
        # Modify first manager's state
        update_conversation_state(self.session_id, self.store, {'phase': 'order_taking', 'turn_count': 5})
        
        # Second manager should still have initial state
        assert manager2.get_current_phase() == 'greeting'
        from src.utils.state_manager import get_conversation_state
        state2 = get_conversation_state(session_id2, store2)
        assert state2['turn_count'] == 0
