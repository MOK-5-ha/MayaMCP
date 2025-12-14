"""
Property-based tests for payment state management.

Uses Hypothesis for property-based testing as specified in the design document.
Each test is annotated with the property it validates from the design.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from src.utils.state_manager import (
    atomic_order_update,
    get_payment_state,
    initialize_state,
    get_current_order_state,
    update_order_state,
    INSUFFICIENT_FUNDS,
    CONCURRENT_MODIFICATION,
    DEFAULT_PAYMENT_STATE,
)


# =============================================================================
# Test Configuration
# =============================================================================

# Minimum 100 iterations per property test as specified in design
TEST_SETTINGS = settings(max_examples=100, deadline=60000)


# =============================================================================
# Strategies (Generators)
# =============================================================================

# Balance strategy: [0.01, 10000.00]
balance_strategy = st.floats(min_value=0.01, max_value=10000.00, allow_nan=False)

# Price strategy for valid orders: [0.01, balance]
# This will be used with assume() to ensure price <= balance
price_strategy = st.floats(min_value=0.01, max_value=10000.00, allow_nan=False)

# Price strategy for insufficient funds: price > balance
# Generated dynamically based on balance

# Order items strategy for state preservation test
order_item_strategy = st.fixed_dictionaries({
    'name': st.text(min_size=1, max_size=20),
    'price': st.floats(min_value=0.01, max_value=100.00, allow_nan=False),
    'category': st.sampled_from(['spirits', 'beer', 'wine', 'cocktail'])
})


# =============================================================================
# Property Tests
# =============================================================================

class TestBalanceDeductionConsistency:
    """
    **Feature: stripe-payment, Property 1: Balance Deduction Consistency**
    
    *For any* drink order with price P and initial balance B where B >= P,
    after the order is processed, the new balance SHALL equal B - P exactly.
    
    **Validates: Requirements 1.2**
    """

    @TEST_SETTINGS
    @given(
        initial_balance=balance_strategy,
        price=price_strategy
    )
    def test_balance_deduction_consistency(self, initial_balance, price):
        """
        Property 1: Balance Deduction Consistency
        
        Preconditions: Session initialized, balance B >= 0, item price P > 0, B >= P
        Invariant: new_balance == B - P exactly (floating point tolerance 0.001)
        """
        # Precondition: price must be <= balance
        assume(price <= initial_balance)
        
        # Setup: Create fresh session with specific balance
        store = {}
        session_id = "test_balance_deduction"
        initialize_state(session_id, store)
        
        # Set initial balance
        store[session_id]['payment']['balance'] = initial_balance
        store[session_id]['payment']['tab_total'] = 0.0
        store[session_id]['payment']['version'] = 0
        
        # Act: Perform order update
        success, error, new_balance = atomic_order_update(session_id, store, price)
        
        # Assert: Order should succeed and balance should be exactly B - P
        assert success, f"Order should succeed: {error}"
        assert error == "", f"No error expected, got: {error}"
        
        expected_balance = initial_balance - price
        assert abs(new_balance - expected_balance) < 0.001, (
            f"Balance deduction incorrect: "
            f"expected {expected_balance}, got {new_balance}"
        )

    @TEST_SETTINGS
    @given(initial_balance=balance_strategy)
    def test_exact_balance_deduction(self, initial_balance):
        """Edge case: exact balance (B == P)"""
        store = {}
        session_id = "test_exact_balance"
        initialize_state(session_id, store)
        
        store[session_id]['payment']['balance'] = initial_balance
        
        # Use exact balance as price
        success, error, new_balance = atomic_order_update(
            session_id, store, initial_balance
        )
        
        assert success, f"Exact balance order should succeed: {error}"
        assert abs(new_balance - 0.0) < 0.001, (
            f"Balance should be 0 after exact deduction, got {new_balance}"
        )

    def test_minimum_price_deduction(self):
        """Edge case: minimum price ($0.01)"""
        store = {}
        session_id = "test_min_price"
        initialize_state(session_id, store)
        
        initial_balance = 1000.00
        min_price = 0.01
        
        success, error, new_balance = atomic_order_update(
            session_id, store, min_price
        )
        
        assert success
        assert abs(new_balance - (initial_balance - min_price)) < 0.001

    def test_large_amount_deduction(self):
        """Edge case: large amounts ($999.99)"""
        store = {}
        session_id = "test_large_amount"
        initialize_state(session_id, store)
        
        large_price = 999.99
        
        success, error, new_balance = atomic_order_update(
            session_id, store, large_price
        )
        
        assert success
        expected = DEFAULT_PAYMENT_STATE['balance'] - large_price
        assert abs(new_balance - expected) < 0.001



class TestInsufficientFundsRejection:
    """
    **Feature: stripe-payment, Property 3: Insufficient Funds Rejection**
    
    *For any* drink order with price P and balance B where B < P,
    the order SHALL be rejected with "INSUFFICIENT_FUNDS" error code,
    and the balance SHALL remain unchanged at B.
    
    **Validates: Requirements 1.3**
    """

    @TEST_SETTINGS
    @given(
        balance=st.floats(min_value=0.0, max_value=999.99, allow_nan=False),
        price_offset=st.floats(min_value=0.01, max_value=100.00, allow_nan=False)
    )
    def test_insufficient_funds_rejection(self, balance, price_offset):
        """
        Property 3: Insufficient Funds Rejection
        
        Preconditions: Session initialized, balance B >= 0, item price P > B
        Invariant: order rejected with INSUFFICIENT_FUNDS, balance unchanged
        """
        # Price is balance + offset, ensuring P > B
        price = balance + price_offset
        
        # Setup
        store = {}
        session_id = "test_insufficient"
        initialize_state(session_id, store)
        
        store[session_id]['payment']['balance'] = balance
        initial_balance = balance
        
        # Act
        success, error, returned_balance = atomic_order_update(
            session_id, store, price
        )
        
        # Assert: Order should be rejected
        assert success is False, "Order should be rejected for insufficient funds"
        assert error == INSUFFICIENT_FUNDS, (
            f"Expected INSUFFICIENT_FUNDS, got: {error}"
        )
        
        # Assert: Balance unchanged
        assert abs(returned_balance - initial_balance) < 0.001, (
            f"Balance should be unchanged: expected {initial_balance}, "
            f"got {returned_balance}"
        )
        
        # Verify state is actually unchanged
        payment = get_payment_state(session_id, store)
        assert abs(payment['balance'] - initial_balance) < 0.001

    def test_zero_balance_rejection(self):
        """Edge case: zero balance"""
        store = {}
        session_id = "test_zero_balance"
        initialize_state(session_id, store)
        
        store[session_id]['payment']['balance'] = 0.0
        
        success, error, balance = atomic_order_update(session_id, store, 0.01)
        
        assert success is False
        assert error == INSUFFICIENT_FUNDS
        assert abs(balance - 0.0) < 0.001

    def test_price_exactly_over_balance(self):
        """Edge case: price exactly $0.01 over balance"""
        store = {}
        session_id = "test_barely_over"
        initialize_state(session_id, store)
        
        balance = 100.00
        store[session_id]['payment']['balance'] = balance
        price = balance + 0.01
        
        success, error, returned_balance = atomic_order_update(
            session_id, store, price
        )
        
        assert success is False
        assert error == INSUFFICIENT_FUNDS
        assert abs(returned_balance - balance) < 0.001

    def test_very_large_price_rejection(self):
        """Edge case: very large price"""
        store = {}
        session_id = "test_large_price"
        initialize_state(session_id, store)
        
        # Default balance is 1000
        very_large_price = 999999.99
        
        success, error, balance = atomic_order_update(
            session_id, store, very_large_price
        )
        
        assert success is False
        assert error == INSUFFICIENT_FUNDS


class TestStatePreservationOnRejection:
    """
    **Feature: stripe-payment, Property 4: State Preservation on Rejection**
    
    *For any* order state S and rejected order due to insufficient funds,
    the order state after rejection SHALL be identical to S
    (no items added or removed).
    
    **Validates: Requirements 1.5**
    """

    @TEST_SETTINGS
    @given(
        order_items=st.lists(order_item_strategy, min_size=0, max_size=10),
        remaining_balance=st.floats(
            min_value=0.01, max_value=50.00, allow_nan=False
        ),
        price_offset=st.floats(min_value=0.01, max_value=100.00, allow_nan=False),
        test_id=st.integers(min_value=0, max_value=2**31)
    )
    def test_state_preservation_on_rejection(
        self, order_items, remaining_balance, price_offset, test_id
    ):
        """
        Property 4: State Preservation on Rejection
        
        Preconditions: Session with existing order items, insufficient balance
        Invariant: order list identical before and after rejection
        """
        # Setup - use unique session_id per test to avoid state pollution
        store = {}
        session_id = f"test_preservation_{test_id}"
        initialize_state(session_id, store)
        
        # Add existing order items
        for item in order_items:
            update_order_state(session_id, store, "add_item", item)
        
        # Set remaining balance
        store[session_id]['payment']['balance'] = remaining_balance
        
        # Capture state before rejection - make deep copy of order items
        order_before = [item.copy() for item in get_current_order_state(session_id, store)]
        payment_before = get_payment_state(session_id, store)
        
        # Attempt order with price > remaining balance
        price = remaining_balance + price_offset
        success, error, _ = atomic_order_update(session_id, store, price)
        
        # Assert rejection
        assert success is False
        assert error == INSUFFICIENT_FUNDS
        
        # Assert order state unchanged
        order_after = get_current_order_state(session_id, store)
        assert order_after == order_before, (
            f"Order state changed after rejection: "
            f"before={order_before}, after={order_after}"
        )
        
        # Assert payment state unchanged (except possibly version read)
        payment_after = get_payment_state(session_id, store)
        assert abs(payment_after['balance'] - payment_before['balance']) < 0.001
        assert abs(payment_after['tab_total'] - payment_before['tab_total']) < 0.001

    def test_empty_order_preservation(self):
        """Edge case: empty order"""
        import uuid
        store = {}
        session_id = f"test_empty_order_{uuid.uuid4()}"
        initialize_state(session_id, store)
        
        store[session_id]['payment']['balance'] = 10.00
        
        order_before = get_current_order_state(session_id, store).copy()
        
        success, _, _ = atomic_order_update(session_id, store, 100.00)
        
        assert success is False
        order_after = get_current_order_state(session_id, store)
        assert order_after == order_before == []

    def test_single_item_order_preservation(self):
        """Edge case: single item order"""
        import uuid
        store = {}
        session_id = f"test_single_item_{uuid.uuid4()}"
        initialize_state(session_id, store)
        
        item = {'name': 'Beer', 'price': 5.00, 'category': 'beer'}
        update_order_state(session_id, store, "add_item", item)
        
        store[session_id]['payment']['balance'] = 10.00
        
        order_before = get_current_order_state(session_id, store).copy()
        
        success, _, _ = atomic_order_update(session_id, store, 100.00)
        
        assert success is False
        order_after = get_current_order_state(session_id, store)
        assert order_after == order_before
        assert len(order_after) == 1
