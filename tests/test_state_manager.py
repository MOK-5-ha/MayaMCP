#!/usr/bin/env python3
"""
Unit tests for src.utils.state_manager module.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os


from src.utils.state_manager import (
    initialize_state,
    get_conversation_state,
    get_order_history,
    get_current_order_state,
    update_conversation_state,
    update_order_state,
    reset_session_state,
    is_order_finished,
    get_order_total
)


class TestStateManager:
    """Test cases for state manager functions."""

    def setup_method(self):
        """Reset state before each test."""
        initialize_state()

    def teardown_method(self):
        """Clean up after each test."""
        initialize_state()

    def test_initialize_state(self):
        """Test state initialization sets correct default values."""
        # Modify state first to ensure reset works
        update_conversation_state({'turn_count': 5, 'phase': 'test'})
        update_order_state('add_item', {'name': 'test', 'price': 10.0})

        # Reset state
        initialize_state()

        # Verify conversation state
        conv_state = get_conversation_state()
        assert conv_state['turn_count'] == 0
        assert conv_state['phase'] == 'greeting'
        assert conv_state['last_order_time'] == 0
        assert conv_state['small_talk_count'] == 0

        # Verify order history
        order_hist = get_order_history()
        assert order_hist['items'] == []
        assert order_hist['total_cost'] == pytest.approx(0.0)
        assert order_hist['paid'] is False
        assert order_hist['tip_amount'] == pytest.approx(0.0)
        assert order_hist['tip_percentage'] == pytest.approx(0.0)

        # Verify current order state
        current_order = get_current_order_state()
        assert current_order == []

    def test_get_conversation_state_returns_copy(self):
        """Test that get_conversation_state returns a copy, not reference."""
        state1 = get_conversation_state()
        state2 = get_conversation_state()

        # Modify one copy
        state1['test'] = 'modified'

        # Verify other copy and original state unaffected
        assert 'test' not in state2
        assert 'test' not in get_conversation_state()

    def test_update_conversation_state(self):
        """Test conversation state updates."""
        # Test single update
        update_conversation_state({'turn_count': 5})
        state = get_conversation_state()
        assert state['turn_count'] == 5
        assert state['phase'] == 'greeting'  # Other values unchanged

        # Test multiple updates
        update_conversation_state({
            'phase': 'order_taking',
            'small_talk_count': 3
        })
        state = get_conversation_state()
        assert state['turn_count'] == 5  # Previous value preserved
        assert state['phase'] == 'order_taking'
        assert state['small_talk_count'] == 3

    def test_update_order_state_add_item(self):
        """Test adding items to order."""
        item1 = {'name': 'Whiskey on the rocks', 'price': 12.0, 'category': 'spirits'}
        item2 = {'name': 'Beer', 'price': 5.0, 'category': 'beer'}

        # Add first item
        update_order_state('add_item', item1)

        current_order = get_current_order_state()
        order_history = get_order_history()

        assert len(current_order) == 1
        assert current_order[0] == item1
        assert len(order_history['items']) == 1
        assert order_history['items'][0] == item1
        assert order_history['total_cost'] == pytest.approx(12.0)

        # Add second item
        update_order_state('add_item', item2)

        current_order = get_current_order_state()
        order_history = get_order_history()

        assert len(current_order) == 2
        assert current_order[1] == item2
        assert len(order_history['items']) == 2
        assert order_history['total_cost'] == pytest.approx(17.0)

    def test_update_order_state_place_order(self):
        """Test placing order."""
        # Add item first
        item = {'name': 'Martini', 'price': 13.0}
        update_order_state('add_item', item)

        # Place order
        update_order_state('place_order')

        current_order = get_current_order_state()
        order_history = get_order_history()

        # Current order should be cleared and marked finished
        assert current_order == []
        assert is_order_finished() is True

        # Order history should retain items
        assert len(order_history['items']) == 1
        assert order_history['items'][0] == item

    def test_update_order_state_clear_order(self):
        """Test clearing order."""
        # Add item first
        item = {'name': 'Beer', 'price': 5.0}
        update_order_state('add_item', item)

        # Clear order
        update_order_state('clear_order')

        current_order = get_current_order_state()
        assert current_order == []
        assert is_order_finished() is False

    def test_update_order_state_add_tip(self):
        """Test adding tip."""
        tip_data = {'amount': 5.0, 'percentage': 20.0}

        update_order_state('add_tip', tip_data)

        order_history = get_order_history()
        assert order_history['tip_amount'] == pytest.approx(5.0)
        assert order_history['tip_percentage'] == pytest.approx(20.0)

    def test_update_order_state_pay_bill(self):
        """Test paying bill."""
        update_order_state('pay_bill')

        order_history = get_order_history()
        assert order_history['paid'] is True

    def test_update_order_state_invalid_action(self):
        """Test invalid action does nothing."""
        initial_state = get_current_order_state().copy()
        initial_history = get_order_history().copy()

        # Invalid action should not change state
        update_order_state('invalid_action', {'test': 'data'})

        assert get_current_order_state() == initial_state
        assert get_order_history() == initial_history

    def test_update_order_state_missing_data(self):
        """Test actions requiring data with None data."""
        initial_state = get_current_order_state().copy()
        initial_history = get_order_history().copy()

        # Actions requiring data should not crash with None
        update_order_state('add_item', None)
        update_order_state('add_tip', None)

        assert get_current_order_state() == initial_state
        assert get_order_history() == initial_history

    def test_reset_session_state(self):
        """Test session state reset."""
        # Modify all states
        update_conversation_state({'turn_count': 10, 'phase': 'test'})
        update_order_state('add_item', {'name': 'test', 'price': 20.0})
        update_order_state('add_tip', {'amount': 5.0, 'percentage': 25.0})

        # Reset session
        reset_session_state()

        # Verify all states reset
        conv_state = get_conversation_state()
        assert conv_state['turn_count'] == 0
        assert conv_state['phase'] == 'greeting'

        order_history = get_order_history()
        assert order_history['items'] == []
        assert order_history['total_cost'] == pytest.approx(0.0)
        assert order_history['tip_amount'] == pytest.approx(0.0)

        current_order = get_current_order_state()
        assert current_order == []

    def test_is_order_finished_initial_state(self):
        """Test is_order_finished with initial state."""
        assert is_order_finished() is False

    def test_is_order_finished_after_place_order(self):
        """Test is_order_finished after placing order."""
        update_order_state('add_item', {'name': 'Test', 'price': 10.0})
        update_order_state('place_order')

        assert is_order_finished() is True

    def test_is_order_finished_after_clear_order(self):
        """Test is_order_finished after clearing order."""
        update_order_state('place_order')  # Mark as finished
        update_order_state('clear_order')  # Clear and unfinish

        assert is_order_finished() is False

    def test_get_order_total_empty_order(self):
        """Test get_order_total with empty order."""
        assert get_order_total() == pytest.approx(0.0)

    def test_get_order_total_with_items(self):
        """Test get_order_total with items."""
        update_order_state('add_item', {'name': 'Item1', 'price': 10.0})
        assert get_order_total() == pytest.approx(10.0)

        update_order_state('add_item', {'name': 'Item2', 'price': 15.5})
        assert get_order_total() == pytest.approx(25.5)

        update_order_state('add_item', {'name': 'Item3', 'price': 7.25})
        assert get_order_total() == pytest.approx(32.75)

    def test_get_order_total_after_place_order(self):
        """Test get_order_total after placing order (should be 0)."""
        update_order_state('add_item', {'name': 'Test', 'price': 10.0})
        assert get_order_total() == pytest.approx(10.0)

        update_order_state('place_order')
        assert get_order_total() == pytest.approx(0.0)  # Current order cleared

    def test_complex_order_workflow(self):
        """Test complex order workflow."""
        # Start with items
        update_order_state('add_item', {'name': 'Whiskey', 'price': 12.0})
        update_order_state('add_item', {'name': 'Beer', 'price': 5.0})

        assert get_order_total() == pytest.approx(17.0)
        assert len(get_current_order_state()) == 2
        assert get_order_history()['total_cost'] == pytest.approx(17.0)

        # Place order
        update_order_state('place_order')

        assert is_order_finished() is True
        assert get_order_total() == pytest.approx(0.0)
        assert len(get_current_order_state()) == 0
        assert get_order_history()['total_cost'] == pytest.approx(17.0)  # History preserved

        # Add tip and pay
        update_order_state('add_tip', {'amount': 3.4, 'percentage': 20.0})
        update_order_state('pay_bill')

        order_hist = get_order_history()
        assert order_hist['tip_amount'] == pytest.approx(3.4)
        assert order_hist['tip_percentage'] == pytest.approx(20.0)
        assert order_hist['paid'] is True

    @patch('src.utils.state_manager.logger')
    def test_logging_calls(self, mock_logger):
        """Test that appropriate logging calls are made."""
        # Test initialize_state logging
        initialize_state()
        # Check that info was called and message contains expected content
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0][0]
        assert "State" in call_args and "initialized" in call_args

        # Test update_conversation_state logging
        update_conversation_state({'turn_count': 5})
        # Check that debug was called and message contains key content
        mock_logger.debug.assert_called()
        call_args = mock_logger.debug.call_args[0][0]
        assert "turn_count" in call_args and "5" in call_args and "Conversation state updated" in call_args

        # Test order action logging
        mock_logger.info.reset_mock()
        update_order_state('add_item', {'name': 'Test', 'price': 10.0})
        # Check that info was called and message contains item name
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0][0]
        assert "Added item" in call_args and "Test" in call_args

        update_order_state('place_order')
        # Check that info was called and message contains expected content
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0][0]
        assert "Order placed" in call_args

        update_order_state('clear_order')
        # Check that info was called and message contains expected content
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0][0]
        assert "Order cleared" in call_args

        update_order_state('add_tip', {'amount': 5.0, 'percentage': 20.0})
        # Check that info was called and message contains tip information
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0][0]
        assert "Tip added" in call_args and "5.00" in call_args

        update_order_state('pay_bill')
        # Check that info was called and message contains expected content
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0][0]
        assert "Bill paid" in call_args

        # Test reset_session_state logging
        reset_session_state()
        # Check that info was called and message contains expected content
        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args[0][0]
        assert "Session" in call_args and "reset" in call_args
