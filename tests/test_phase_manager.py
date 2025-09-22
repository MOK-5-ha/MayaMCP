#!/usr/bin/env python3
"""
Unit tests for src.conversation.phase_manager module.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os



from src.conversation.phase_manager import ConversationPhaseManager
from src.utils.state_manager import initialize_state, update_conversation_state


class TestConversationPhaseManager:
    """Test cases for ConversationPhaseManager class."""

    def setup_method(self):
        """Setup for each test."""
        initialize_state()
        self.manager = ConversationPhaseManager()

    def teardown_method(self):
        """Cleanup after each test."""
        initialize_state()

    def test_init(self):
        """Test ConversationPhaseManager initialization."""
        manager = ConversationPhaseManager()
        assert hasattr(manager, 'logger')
        assert manager.logger is not None

    def test_get_current_phase_initial(self):
        """Test get_current_phase returns initial phase."""
        phase = self.manager.get_current_phase()
        assert phase == 'greeting'

    def test_get_current_phase_after_update(self):
        """Test get_current_phase after phase update."""
        update_conversation_state({'phase': 'order_taking'})
        phase = self.manager.get_current_phase()
        assert phase == 'order_taking'

    def test_increment_turn(self):
        """Test increment_turn increases turn count."""
        # Initial turn count should be 0
        self.manager.increment_turn()
        
        from src.utils.state_manager import get_conversation_state
        state = get_conversation_state()
        assert state['turn_count'] == 1
        
        # Increment again
        self.manager.increment_turn()
        state = get_conversation_state()
        assert state['turn_count'] == 2

    def test_increment_small_talk_in_small_talk_phase(self):
        """Test increment_small_talk when in small_talk phase."""
        # Set phase to small_talk
        update_conversation_state({'phase': 'small_talk', 'small_talk_count': 2})
        
        self.manager.increment_small_talk()
        
        from src.utils.state_manager import get_conversation_state
        state = get_conversation_state()
        assert state['small_talk_count'] == 3

    def test_increment_small_talk_not_in_small_talk_phase(self):
        """Test increment_small_talk when not in small_talk phase."""
        # Set phase to something other than small_talk
        update_conversation_state({'phase': 'order_taking', 'small_talk_count': 2})
        
        self.manager.increment_small_talk()
        
        from src.utils.state_manager import get_conversation_state
        state = get_conversation_state()
        assert state['small_talk_count'] == 2  # Should not change

    def test_handle_order_placed(self):
        """Test handle_order_placed updates state correctly."""
        # Set initial state
        update_conversation_state({'turn_count': 5, 'small_talk_count': 3})
        
        self.manager.handle_order_placed()
        
        from src.utils.state_manager import get_conversation_state
        state = get_conversation_state()
        assert state['last_order_time'] == 5  # Should match turn_count
        assert state['small_talk_count'] == 0  # Should reset

    @patch('src.conversation.phase_manager.determine_next_phase')
    def test_update_phase_without_order(self, mock_determine_next_phase):
        """Test update_phase without order placement."""
        mock_determine_next_phase.return_value = 'order_taking'
        
        result = self.manager.update_phase(order_placed=False)
        
        # Verify determine_next_phase called with correct parameters
        mock_determine_next_phase.assert_called_once()
        call_args = mock_determine_next_phase.call_args[0]
        assert call_args[1] is False  # order_placed parameter
        
        # Verify phase updated
        assert result == 'order_taking'
        assert self.manager.get_current_phase() == 'order_taking'

    @patch('src.conversation.phase_manager.determine_next_phase')
    def test_update_phase_with_order(self, mock_determine_next_phase):
        """Test update_phase with order placement."""
        mock_determine_next_phase.return_value = 'small_talk'
        update_conversation_state({'turn_count': 3})
        
        result = self.manager.update_phase(order_placed=True)
        
        # Verify handle_order_placed was called (check state changes)
        from src.utils.state_manager import get_conversation_state
        state = get_conversation_state()
        assert state['last_order_time'] == 3
        assert state['small_talk_count'] == 0
        
        # Verify determine_next_phase called with order_placed=True
        mock_determine_next_phase.assert_called_once()
        call_args = mock_determine_next_phase.call_args[0]
        assert call_args[1] is True
        
        assert result == 'small_talk'
        assert self.manager.get_current_phase() == 'small_talk'

    @patch('src.utils.helpers.is_casual_conversation')
    def test_should_use_rag_casual(self, mock_is_casual_conversation):
        """Test should_use_rag returns True for casual conversation."""
        mock_is_casual_conversation.return_value = True
        
        result = self.manager.should_use_rag("How's the weather?")
        
        mock_is_casual_conversation.assert_called_once_with("How's the weather?")
        assert result is True

    @patch('src.utils.helpers.is_casual_conversation')
    def test_should_use_rag_not_casual(self, mock_is_casual_conversation):
        """Test should_use_rag returns False for non-casual conversation."""
        mock_is_casual_conversation.return_value = False
        
        result = self.manager.should_use_rag("I want a whiskey")
        
        mock_is_casual_conversation.assert_called_once_with("I want a whiskey")
        assert result is False

    def test_reset_phase(self):
        """Test reset_phase resets all conversation state."""
        # Set non-default state
        update_conversation_state({
            'phase': 'order_taking',
            'turn_count': 10,
            'small_talk_count': 5,
            'last_order_time': 7
        })
        
        self.manager.reset_phase()
        
        from src.utils.state_manager import get_conversation_state
        state = get_conversation_state()
        assert state['phase'] == 'greeting'
        assert state['turn_count'] == 0
        assert state['small_talk_count'] == 0
        assert state['last_order_time'] == 0

    def test_update_phase_logging(self):
        """Test update_phase logs phase transitions."""
        with patch.object(self.manager, 'logger') as mock_logger:
            with patch('src.conversation.phase_manager.determine_next_phase') as mock_determine:
                mock_determine.return_value = 'order_taking'
                
                self.manager.update_phase()
                
                # Check that info log was called
                mock_logger.info.assert_called_once()
                log_call = mock_logger.info.call_args[0][0]
                assert 'Conversation phase updated' in log_call
                assert 'greeting -> order_taking' in log_call

    def test_reset_phase_logging(self):
        """Test reset_phase logs the reset."""
        with patch.object(self.manager, 'logger') as mock_logger:
            self.manager.reset_phase()
            
            mock_logger.info.assert_called_once_with("Conversation phase reset to greeting")

    def test_integration_workflow(self):
        """Test complete conversation phase workflow."""
        # Start in greeting phase
        assert self.manager.get_current_phase() == 'greeting'
        
        # Increment turn and update phase (greeting -> order_taking)
        self.manager.increment_turn()
        with patch('src.conversation.phase_manager.determine_next_phase') as mock_determine:
            mock_determine.return_value = 'order_taking'
            phase = self.manager.update_phase()
            assert phase == 'order_taking'
        
        # Place an order (order_taking -> small_talk)
        with patch('src.conversation.phase_manager.determine_next_phase') as mock_determine:
            mock_determine.return_value = 'small_talk'
            phase = self.manager.update_phase(order_placed=True)
            assert phase == 'small_talk'
        
        # Increment small talk multiple times
        for _ in range(3):
            self.manager.increment_small_talk()
        
        from src.utils.state_manager import get_conversation_state
        state = get_conversation_state()
        assert state['small_talk_count'] == 3
        
        # Reset to beginning
        self.manager.reset_phase()
        assert self.manager.get_current_phase() == 'greeting'

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test increment_small_talk with no prior small_talk_count
        update_conversation_state({'phase': 'small_talk'})
        # Remove small_talk_count to test default handling
        
        self.manager.increment_small_talk()
        
        from src.utils.state_manager import get_conversation_state
        state = get_conversation_state()
        assert 'small_talk_count' in state  # Should exist after increment
        assert state['small_talk_count'] == 1  # Should be 1 after first increment

    def test_should_use_rag_returns_boolean(self):
        """Test should_use_rag returns a boolean for given inputs."""
        # This test ensures the local import works correctly
        result = self.manager.should_use_rag("I love philosophy")
        assert isinstance(result, bool)
        
        result = self.manager.should_use_rag("I want a beer")
        assert isinstance(result, bool)

    def test_manager_state_isolation(self):
        """Test that different manager instances don't interfere."""
        manager1 = ConversationPhaseManager()
        manager2 = ConversationPhaseManager()
        
        # Both should see the same global state
        assert manager1.get_current_phase() == manager2.get_current_phase()
        
        # State changes should be visible to both
        update_conversation_state({'phase': 'order_taking'})
        assert manager1.get_current_phase() == 'order_taking'
        assert manager2.get_current_phase() == 'order_taking'