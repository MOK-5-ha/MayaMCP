"""
Property-based tests for payment state management.

Uses Hypothesis for property-based testing as specified in the design document.
Each test is annotated with the property it validates from the design.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from src.utils.state_manager import (
    atomic_order_update,
    atomic_payment_complete,
    get_payment_state,
    initialize_state,
    get_current_order_state,
    update_order_state,
    update_payment_state,
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


class TestTabAccumulationAccuracy:
    """
    **Feature: stripe-payment, Property 2: Tab Accumulation Accuracy**

    *For any* sequence of drink orders with prices [P1, P2, ..., Pn],
    the tab total SHALL equal the sum of all prices: sum(P1 + P2 + ... + Pn).

    **Validates: Requirements 2.2**
    """

    @TEST_SETTINGS
    @given(
        prices=st.lists(
            st.floats(min_value=0.01, max_value=50.00, allow_nan=False),
            min_size=1,
            max_size=20
        ),
        test_id=st.integers(min_value=0, max_value=2**31)
    )
    def test_tab_accumulation_accuracy(self, prices, test_id):
        """
        Property 2: Tab Accumulation Accuracy

        Preconditions: Session initialized with $1000 balance, empty tab
        Generators: list of 1-20 item prices, each in [0.01, 50.00]
        Invariant: tab_total == sum(all_item_prices) exactly
        """
        # Precondition: total must be <= 1000 (starting balance)
        total_price = sum(prices)
        assume(total_price <= 1000.00)

        # Setup
        store = {}
        session_id = f"test_tab_accumulation_{test_id}"
        initialize_state(session_id, store)

        # Verify initial state
        payment = get_payment_state(session_id, store)
        assert payment['balance'] == 1000.00
        assert payment['tab_total'] == 0.00

        # Act: Add all items
        for price in prices:
            success, error, _ = atomic_order_update(session_id, store, price)
            assert success, f"Order should succeed: {error}"

        # Assert: tab_total == sum(prices)
        payment = get_payment_state(session_id, store)
        assert abs(payment['tab_total'] - total_price) < 0.001, (
            f"Tab accumulation incorrect: "
            f"expected {total_price}, got {payment['tab_total']}"
        )

    def test_single_item_tab(self):
        """Edge case: single item"""
        store = {}
        session_id = "test_single_item_tab"
        initialize_state(session_id, store)

        price = 15.00
        success, _, _ = atomic_order_update(session_id, store, price)

        assert success
        payment = get_payment_state(session_id, store)
        assert abs(payment['tab_total'] - price) < 0.001

    def test_many_small_items_tab(self):
        """Edge case: many small items"""
        store = {}
        session_id = "test_many_small_items"
        initialize_state(session_id, store)

        # 100 items at $0.01 each = $1.00 total
        small_price = 0.01
        num_items = 100

        for _ in range(num_items):
            success, _, _ = atomic_order_update(session_id, store, small_price)
            assert success

        payment = get_payment_state(session_id, store)
        expected_total = small_price * num_items
        assert abs(payment['tab_total'] - expected_total) < 0.001

    def test_items_totaling_exactly_1000(self):
        """Edge case: items totaling exactly $1000"""
        store = {}
        session_id = "test_exact_1000"
        initialize_state(session_id, store)

        # Add items totaling exactly $1000
        prices = [500.00, 300.00, 150.00, 50.00]  # = 1000.00

        for price in prices:
            success, _, _ = atomic_order_update(session_id, store, price)
            assert success

        payment = get_payment_state(session_id, store)
        assert abs(payment['tab_total'] - 1000.00) < 0.001
        assert abs(payment['balance'] - 0.00) < 0.001



class TestPaymentCompletionStateReset:
    """
    **Feature: stripe-payment, Property 5: Payment Completion State Reset**

    *For any* successful payment completion, the tab total SHALL reset to $0.00
    and payment status SHALL be "completed".

    **Validates: Requirements 3.3**
    """

    @TEST_SETTINGS
    @given(
        tab_total=st.floats(min_value=0.01, max_value=1000.00, allow_nan=False),
        payment_status=st.sampled_from(['pending', 'processing']),
        test_id=st.integers(min_value=0, max_value=2**31)
    )
    def test_payment_completion_state_reset(self, tab_total, payment_status, test_id):
        """
        Property 5: Payment Completion State Reset

        Preconditions: Session with non-zero tab, payment_status != "completed"
        Generators: tab_total in [0.01, 1000.00], various payment_status values
        Invariant: after completion, tab_total == 0.00 AND payment_status == "completed"
        """
        # Setup
        store = {}
        session_id = f"test_payment_complete_{test_id}"
        initialize_state(session_id, store)

        # Set up initial state with non-zero tab and non-completed status
        store[session_id]['payment']['tab_total'] = tab_total
        store[session_id]['payment']['payment_status'] = payment_status
        store[session_id]['payment']['needs_reconciliation'] = False

        # Verify preconditions
        payment_before = get_payment_state(session_id, store)
        assert payment_before['tab_total'] == tab_total
        assert payment_before['payment_status'] == payment_status

        # Act: Complete payment
        success = atomic_payment_complete(session_id, store)

        # Assert: Operation succeeded
        assert success, "Payment completion should succeed"

        # Assert: tab_total == 0.00 AND payment_status == "completed"
        payment_after = get_payment_state(session_id, store)
        assert payment_after['tab_total'] == 0.0, (
            f"Tab should be reset to 0.00, got {payment_after['tab_total']}"
        )
        assert payment_after['payment_status'] == "completed", (
            f"Status should be 'completed', got {payment_after['payment_status']}"
        )

    def test_minimum_tab_completion(self):
        """Edge case: minimum tab ($0.01)"""
        store = {}
        session_id = "test_min_tab_complete"
        initialize_state(session_id, store)

        store[session_id]['payment']['tab_total'] = 0.01
        store[session_id]['payment']['payment_status'] = 'pending'

        success = atomic_payment_complete(session_id, store)

        assert success
        payment = get_payment_state(session_id, store)
        assert payment['tab_total'] == 0.0
        assert payment['payment_status'] == "completed"

    def test_maximum_tab_completion(self):
        """Edge case: maximum tab ($1000)"""
        store = {}
        session_id = "test_max_tab_complete"
        initialize_state(session_id, store)

        store[session_id]['payment']['tab_total'] = 1000.00
        store[session_id]['payment']['payment_status'] = 'pending'

        success = atomic_payment_complete(session_id, store)

        assert success
        payment = get_payment_state(session_id, store)
        assert payment['tab_total'] == 0.0
        assert payment['payment_status'] == "completed"

    def test_processing_status_completion(self):
        """Edge case: already processing status"""
        store = {}
        session_id = "test_processing_complete"
        initialize_state(session_id, store)

        store[session_id]['payment']['tab_total'] = 50.00
        store[session_id]['payment']['payment_status'] = 'processing'

        success = atomic_payment_complete(session_id, store)

        assert success
        payment = get_payment_state(session_id, store)
        assert payment['tab_total'] == 0.0
        assert payment['payment_status'] == "completed"

    def test_version_incremented_on_completion(self):
        """Verify version is incremented on completion"""
        store = {}
        session_id = "test_version_increment"
        initialize_state(session_id, store)

        store[session_id]['payment']['tab_total'] = 100.00
        store[session_id]['payment']['payment_status'] = 'pending'
        initial_version = store[session_id]['payment']['version']

        success = atomic_payment_complete(session_id, store)

        assert success
        payment = get_payment_state(session_id, store)
        assert payment['version'] == initial_version + 1

    def test_needs_reconciliation_cleared_on_completion(self):
        """Verify needs_reconciliation is set to False on completion"""
        store = {}
        session_id = "test_reconciliation_cleared"
        initialize_state(session_id, store)

        store[session_id]['payment']['tab_total'] = 75.00
        store[session_id]['payment']['payment_status'] = 'processing'
        store[session_id]['payment']['needs_reconciliation'] = True

        success = atomic_payment_complete(session_id, store)

        assert success
        payment = get_payment_state(session_id, store)
        assert payment['needs_reconciliation'] is False
        assert payment['payment_status'] == "completed"


# Import for balance color tests
from src.ui.tab_overlay import get_balance_color, COLOR_NORMAL, COLOR_LOW_FUNDS, COLOR_DEPLETED


class TestBalanceColorSelection:
    """
    **Feature: stripe-payment, Property 7: Balance Color Selection**

    *For any* balance value B:
    - If B >= 50.00, color SHALL be white (#FFFFFF)
    - If 0 < B < 50.00, color SHALL be orange (#FFA500)
    - If B <= 0, color SHALL be red (#FF4444)

    Every numeric balance maps to exactly one color with no gaps or overlaps.

    **Validates: Requirements 6.3, 6.4**
    """

    @TEST_SETTINGS
    @given(
        balance=st.floats(min_value=-100.00, max_value=2000.00, allow_nan=False)
    )
    def test_balance_color_selection(self, balance):
        """
        Property 7: Balance Color Selection

        Preconditions: None (pure function)
        Generators: balance in [-100.00, 2000.00] covering all ranges
        Invariant: balance >= 50 → #FFFFFF, 0 < balance < 50 → #FFA500, balance <= 0 → #FF4444
        """
        color = get_balance_color(balance)

        # Determine expected color based on balance
        if balance >= 50.0:
            expected_color = COLOR_NORMAL  # #FFFFFF
        elif balance > 0:
            expected_color = COLOR_LOW_FUNDS  # #FFA500
        else:
            expected_color = COLOR_DEPLETED  # #FF4444

        assert color == expected_color, (
            f"Balance {balance} should map to {expected_color}, got {color}"
        )

    def test_exactly_50_dollars(self):
        """Edge case: exactly $50"""
        color = get_balance_color(50.0)
        assert color == COLOR_NORMAL, "Balance of exactly $50 should be white"

    def test_exactly_0_dollars(self):
        """Edge case: exactly $0"""
        color = get_balance_color(0.0)
        assert color == COLOR_DEPLETED, "Balance of exactly $0 should be red"

    def test_negative_balance(self):
        """Edge case: negative values"""
        color = get_balance_color(-50.0)
        assert color == COLOR_DEPLETED, "Negative balance should be red"

    def test_boundary_49_99(self):
        """Edge case: boundary value $49.99"""
        color = get_balance_color(49.99)
        assert color == COLOR_LOW_FUNDS, "Balance of $49.99 should be orange"

    def test_boundary_50_01(self):
        """Edge case: boundary value $50.01"""
        color = get_balance_color(50.01)
        assert color == COLOR_NORMAL, "Balance of $50.01 should be white"

    def test_boundary_0_01(self):
        """Edge case: boundary value $0.01"""
        color = get_balance_color(0.01)
        assert color == COLOR_LOW_FUNDS, "Balance of $0.01 should be orange"

    def test_boundary_negative_0_01(self):
        """Edge case: boundary value -$0.01"""
        color = get_balance_color(-0.01)
        assert color == COLOR_DEPLETED, "Balance of -$0.01 should be red"



# Import for animation queue tests
from src.ui.tab_overlay import AnimationQueue, TabUpdate
import time


class TestAnimationQueueLengthConsistency:
    """
    **Feature: stripe-payment, Property 6: Animation Queue Length Consistency**

    *For any* sequence of N item additions to the tab, the animation queue
    SHALL contain exactly N pending animations before any are executed.

    Note: This property tests the deterministic queue length invariant.
    Animation timing verification is handled via integration tests.

    **Validates: Requirements 5.3**
    """

    @TEST_SETTINGS
    @given(
        updates=st.lists(
            st.floats(min_value=0.01, max_value=100.00, allow_nan=False),
            min_size=1,
            max_size=50
        )
    )
    def test_animation_queue_length_consistency(self, updates):
        """
        Property 6: Animation Queue Length Consistency

        Preconditions: Animation queue initialized, no animations running
        Generators: sequence of 1-50 tab updates with random amounts
        Invariant: queue length == number of updates added (before execution)
        
        Note: This test adds updates with sufficient delay (>100ms simulated)
        to prevent collapse behavior, testing the basic queue length property.
        """
        queue = AnimationQueue()
        
        # Add updates with simulated time gaps > 100ms to prevent collapse
        running_tab = 0.0
        for i, amount in enumerate(updates):
            prev_tab = running_tab
            running_tab += amount
            
            update = TabUpdate(
                start_tab=prev_tab,
                end_tab=running_tab,
                start_balance=1000.0 - prev_tab,
                end_balance=1000.0 - running_tab
            )
            
            # Simulate time passing to prevent collapse (>100ms between updates)
            queue._last_enqueue_time = 0  # Reset to ensure no collapse
            queue.enqueue(update)
        
        # Assert: queue length equals number of updates (capped at MAX_DEPTH)
        expected_length = min(len(updates), AnimationQueue.MAX_DEPTH)
        assert queue.get_queue_length() == expected_length, (
            f"Queue length should be {expected_length}, got {queue.get_queue_length()}"
        )

    def test_single_update_queue_length(self):
        """Edge case: single update"""
        queue = AnimationQueue()
        
        update = TabUpdate(
            start_tab=0.0,
            end_tab=10.0,
            start_balance=1000.0,
            end_balance=990.0
        )
        queue.enqueue(update)
        
        assert queue.get_queue_length() == 1

    def test_rapid_consecutive_updates_collapse(self):
        """Edge case: rapid consecutive updates should collapse"""
        queue = AnimationQueue()
        
        # Simulate rapid updates within 100ms window
        # These should collapse into a single animation
        base_time = time.time() * 1000
        
        # First update
        queue._last_enqueue_time = base_time
        queue.enqueue(TabUpdate(
            start_tab=0.0,
            end_tab=10.0,
            start_balance=1000.0,
            end_balance=990.0
        ))
        
        # Second update within 100ms - should collapse
        queue._last_enqueue_time = base_time + 50  # 50ms later
        queue.enqueue(TabUpdate(
            start_tab=10.0,
            end_tab=25.0,
            start_balance=990.0,
            end_balance=975.0
        ))
        
        # Should have collapsed to 1 item
        assert queue.get_queue_length() == 1
        
        # The collapsed item should have start from first, end from last
        item = queue._queue[0]
        assert item.start_tab == 0.0
        assert item.end_tab == 25.0

    def test_updates_with_same_amount(self):
        """Edge case: updates with same amount"""
        queue = AnimationQueue()
        
        for i in range(5):
            queue._last_enqueue_time = 0  # Reset to prevent collapse
            queue.enqueue(TabUpdate(
                start_tab=i * 10.0,
                end_tab=(i + 1) * 10.0,
                start_balance=1000.0 - i * 10.0,
                end_balance=1000.0 - (i + 1) * 10.0
            ))
        
        assert queue.get_queue_length() == 5

    def test_queue_max_depth_enforcement(self):
        """Test that queue respects MAX_DEPTH limit"""
        queue = AnimationQueue()
        
        # Add more than MAX_DEPTH updates
        for i in range(10):
            queue._last_enqueue_time = 0  # Reset to prevent collapse
            queue.enqueue(TabUpdate(
                start_tab=i * 10.0,
                end_tab=(i + 1) * 10.0,
                start_balance=1000.0,
                end_balance=990.0
            ))
        
        # Queue should be capped at MAX_DEPTH
        assert queue.get_queue_length() == AnimationQueue.MAX_DEPTH

    def test_process_next_reduces_queue_length(self):
        """Test that processing reduces queue length"""
        queue = AnimationQueue()
        
        for i in range(3):
            queue._last_enqueue_time = 0
            queue.enqueue(TabUpdate(
                start_tab=i * 10.0,
                end_tab=(i + 1) * 10.0,
                start_balance=1000.0,
                end_balance=990.0
            ))
        
        assert queue.get_queue_length() == 3
        
        # Process one
        queue.process_next()
        assert queue.get_queue_length() == 2
        
        # Process another
        queue.process_next()
        assert queue.get_queue_length() == 1

    def test_cancel_all_clears_queue(self):
        """Test that cancel_all clears the queue"""
        queue = AnimationQueue()
        
        for i in range(3):
            queue._last_enqueue_time = 0
            queue.enqueue(TabUpdate(
                start_tab=i * 10.0,
                end_tab=(i + 1) * 10.0,
                start_balance=1000.0,
                end_balance=990.0
            ))
        
        assert queue.get_queue_length() == 3
        
        queue.cancel_all()
        assert queue.get_queue_length() == 0


# =============================================================================
# Tip-Related Property Tests
# =============================================================================

from src.utils.state_manager import (
    calculate_tip,
    set_tip,
    get_payment_total,
    VALID_TIP_PERCENTAGES,
)


class TestTipCalculationAccuracy:
    """
    **Feature: stripe-payment, Property 8: Tip Calculation Accuracy**

    *For any* tab total T > 0 and tip percentage P in {10, 15, 20},
    the calculated tip amount SHALL equal T * (P / 100) rounded to 2 decimal places.

    **Validates: Requirements 7.2**
    """

    @TEST_SETTINGS
    @given(
        tab_total=st.floats(min_value=0.01, max_value=1000.00, allow_nan=False),
        percentage=st.sampled_from([10, 15, 20])
    )
    def test_tip_calculation_accuracy(self, tab_total, percentage):
        """
        Property 8: Tip Calculation Accuracy

        Generators: tab_total in [0.01, 1000.00], percentage in {10, 15, 20}
        Invariant: tip == round(tab * percentage / 100, 2)
        """
        # Act
        tip = calculate_tip(tab_total, percentage)

        # Assert: tip equals expected calculation
        expected_tip = round(tab_total * (percentage / 100), 2)
        assert abs(tip - expected_tip) < 0.001, (
            f"Tip calculation incorrect: "
            f"tab={tab_total}, percentage={percentage}, "
            f"expected={expected_tip}, got={tip}"
        )

    def test_tip_10_percent(self):
        """Test 10% tip calculation"""
        assert calculate_tip(100.00, 10) == 10.00
        assert calculate_tip(50.00, 10) == 5.00
        assert calculate_tip(33.33, 10) == 3.33

    def test_tip_15_percent(self):
        """Test 15% tip calculation"""
        assert calculate_tip(100.00, 15) == 15.00
        assert calculate_tip(50.00, 15) == 7.50
        assert calculate_tip(33.33, 15) == 5.00  # 4.9995 rounds to 5.00

    def test_tip_20_percent(self):
        """Test 20% tip calculation"""
        assert calculate_tip(100.00, 20) == 20.00
        assert calculate_tip(50.00, 20) == 10.00
        assert calculate_tip(33.33, 20) == 6.67

    def test_invalid_percentage_raises_error(self):
        """Test that invalid percentages raise ValueError"""
        with pytest.raises(ValueError):
            calculate_tip(100.00, 5)
        with pytest.raises(ValueError):
            calculate_tip(100.00, 25)
        with pytest.raises(ValueError):
            calculate_tip(100.00, 0)


class TestTipToggleBehavior:
    """
    **Feature: stripe-payment, Property 9: Tip Toggle Behavior**

    *For any* selected tip percentage P, clicking the same percentage button again
    SHALL result in tip_percentage = None and tip_amount = 0.00.

    **Validates: Requirements 7.6**
    """

    @TEST_SETTINGS
    @given(
        tab_total=st.floats(min_value=0.01, max_value=1000.00, allow_nan=False),
        percentage=st.sampled_from([10, 15, 20]),
        test_id=st.integers(min_value=0, max_value=2**31)
    )
    def test_tip_toggle_behavior(self, tab_total, percentage, test_id):
        """
        Property 9: Tip Toggle Behavior

        Preconditions: Tip already selected with percentage P
        Invariant: clicking same percentage results in tip_percentage=None, tip_amount=0
        """
        # Precondition: tip must be non-zero after rounding
        # Very small tabs (e.g., $0.03 at 10%) round to $0.00 tip
        expected_tip = round(tab_total * (percentage / 100), 2)
        assume(expected_tip > 0)

        # Setup
        store = {}
        session_id = f"test_tip_toggle_{test_id}"
        initialize_state(session_id, store)

        # Set up tab total
        store[session_id]['payment']['tab_total'] = tab_total

        # First: Set tip with percentage P
        tip_amount, total = set_tip(session_id, store, percentage)
        
        # Verify tip was set
        payment = get_payment_state(session_id, store)
        assert payment['tip_percentage'] == percentage
        assert payment['tip_amount'] > 0

        # Act: Toggle by setting same percentage again
        tip_amount_after, total_after = set_tip(session_id, store, percentage)

        # Assert: Tip should be removed (toggle behavior)
        payment_after = get_payment_state(session_id, store)
        assert payment_after['tip_percentage'] is None, (
            f"tip_percentage should be None after toggle, got {payment_after['tip_percentage']}"
        )
        assert payment_after['tip_amount'] == 0.0, (
            f"tip_amount should be 0 after toggle, got {payment_after['tip_amount']}"
        )
        assert tip_amount_after == 0.0
        assert total_after == tab_total  # Total should equal just the tab

    def test_toggle_10_percent(self):
        """Test toggle behavior for 10%"""
        store = {}
        session_id = "test_toggle_10"
        initialize_state(session_id, store)
        store[session_id]['payment']['tab_total'] = 100.00

        # Set 10%
        set_tip(session_id, store, 10)
        payment = get_payment_state(session_id, store)
        assert payment['tip_percentage'] == 10
        assert payment['tip_amount'] == 10.00

        # Toggle off
        set_tip(session_id, store, 10)
        payment = get_payment_state(session_id, store)
        assert payment['tip_percentage'] is None
        assert payment['tip_amount'] == 0.0

    def test_toggle_15_percent(self):
        """Test toggle behavior for 15%"""
        store = {}
        session_id = "test_toggle_15"
        initialize_state(session_id, store)
        store[session_id]['payment']['tab_total'] = 100.00

        set_tip(session_id, store, 15)
        set_tip(session_id, store, 15)
        
        payment = get_payment_state(session_id, store)
        assert payment['tip_percentage'] is None
        assert payment['tip_amount'] == 0.0

    def test_toggle_20_percent(self):
        """Test toggle behavior for 20%"""
        store = {}
        session_id = "test_toggle_20"
        initialize_state(session_id, store)
        store[session_id]['payment']['tab_total'] = 100.00

        set_tip(session_id, store, 20)
        set_tip(session_id, store, 20)
        
        payment = get_payment_state(session_id, store)
        assert payment['tip_percentage'] is None
        assert payment['tip_amount'] == 0.0


class TestTotalCalculationWithTip:
    """
    **Feature: stripe-payment, Property 10: Total Calculation with Tip**

    *For any* tab total T and tip amount A, the displayed total SHALL equal T + A exactly.

    **Validates: Requirements 7.4, 7.9**
    """

    @TEST_SETTINGS
    @given(
        tab_total=st.floats(min_value=0.01, max_value=1000.00, allow_nan=False),
        tip_amount=st.floats(min_value=0.0, max_value=200.00, allow_nan=False),
        test_id=st.integers(min_value=0, max_value=2**31)
    )
    def test_total_calculation_with_tip(self, tab_total, tip_amount, test_id):
        """
        Property 10: Total Calculation with Tip

        Generators: tab in [0.01, 1000.00], tip in [0, 200.00]
        Invariant: total == tab + tip exactly
        """
        # Setup
        store = {}
        session_id = f"test_total_calc_{test_id}"
        initialize_state(session_id, store)

        # Set up tab and tip directly
        store[session_id]['payment']['tab_total'] = tab_total
        store[session_id]['payment']['tip_amount'] = tip_amount

        # Act
        total = get_payment_total(session_id, store)

        # Assert: total == tab + tip
        expected_total = tab_total + tip_amount
        assert abs(total - expected_total) < 0.001, (
            f"Total calculation incorrect: "
            f"tab={tab_total}, tip={tip_amount}, "
            f"expected={expected_total}, got={total}"
        )

    def test_total_with_zero_tip(self):
        """Test total when tip is zero"""
        store = {}
        session_id = "test_total_zero_tip"
        initialize_state(session_id, store)

        store[session_id]['payment']['tab_total'] = 100.00
        store[session_id]['payment']['tip_amount'] = 0.00

        total = get_payment_total(session_id, store)
        assert total == 100.00

    def test_total_with_tip_via_set_tip(self):
        """Test total calculation using set_tip function"""
        store = {}
        session_id = "test_total_via_set_tip"
        initialize_state(session_id, store)

        store[session_id]['payment']['tab_total'] = 100.00
        
        tip_amount, total = set_tip(session_id, store, 15)
        
        assert tip_amount == 15.00
        assert total == 115.00
        assert get_payment_total(session_id, store) == 115.00


class TestTipReplacementOnNewSelection:
    """
    **Feature: stripe-payment, Property 11: Tip Replacement on New Selection**

    *For any* existing tip with percentage P1 and new selection P2 where P1 != P2,
    the tip SHALL be recalculated as tab_total * (P2 / 100), completely replacing
    the previous tip.

    **Validates: Requirements 7.5**
    """

    @TEST_SETTINGS
    @given(
        tab_total=st.floats(min_value=0.01, max_value=1000.00, allow_nan=False),
        p1=st.sampled_from([10, 15, 20]),
        p2=st.sampled_from([10, 15, 20]),
        test_id=st.integers(min_value=0, max_value=2**31)
    )
    def test_tip_replacement_on_new_selection(self, tab_total, p1, p2, test_id):
        """
        Property 11: Tip Replacement on New Selection

        Preconditions: Existing tip with P1, new selection P2 where P1 != P2
        Invariant: new tip = tab * P2 / 100, completely replaces old
        """
        # Skip if same percentage (that's toggle behavior, tested separately)
        assume(p1 != p2)

        # Setup
        store = {}
        session_id = f"test_tip_replace_{test_id}"
        initialize_state(session_id, store)

        store[session_id]['payment']['tab_total'] = tab_total

        # Set initial tip with P1
        set_tip(session_id, store, p1)
        payment_after_p1 = get_payment_state(session_id, store)
        assert payment_after_p1['tip_percentage'] == p1

        # Act: Replace with P2
        tip_amount, total = set_tip(session_id, store, p2)

        # Assert: Tip is completely replaced with P2 calculation
        expected_tip = round(tab_total * (p2 / 100), 2)
        payment_after_p2 = get_payment_state(session_id, store)
        
        assert payment_after_p2['tip_percentage'] == p2, (
            f"tip_percentage should be {p2}, got {payment_after_p2['tip_percentage']}"
        )
        assert abs(payment_after_p2['tip_amount'] - expected_tip) < 0.001, (
            f"tip_amount should be {expected_tip}, got {payment_after_p2['tip_amount']}"
        )
        assert abs(tip_amount - expected_tip) < 0.001

    def test_replace_10_with_15(self):
        """Test replacing 10% with 15%"""
        store = {}
        session_id = "test_replace_10_15"
        initialize_state(session_id, store)
        store[session_id]['payment']['tab_total'] = 100.00

        set_tip(session_id, store, 10)
        assert get_payment_state(session_id, store)['tip_amount'] == 10.00

        set_tip(session_id, store, 15)
        payment = get_payment_state(session_id, store)
        assert payment['tip_percentage'] == 15
        assert payment['tip_amount'] == 15.00

    def test_replace_20_with_10(self):
        """Test replacing 20% with 10%"""
        store = {}
        session_id = "test_replace_20_10"
        initialize_state(session_id, store)
        store[session_id]['payment']['tab_total'] = 100.00

        set_tip(session_id, store, 20)
        assert get_payment_state(session_id, store)['tip_amount'] == 20.00

        set_tip(session_id, store, 10)
        payment = get_payment_state(session_id, store)
        assert payment['tip_percentage'] == 10
        assert payment['tip_amount'] == 10.00


class TestTipResetOnPaymentCompletion:
    """
    **Feature: stripe-payment, Property 12: Tip Reset on Payment Completion**

    *For any* successful payment completion with a non-zero tip,
    both tip_percentage SHALL be None and tip_amount SHALL be 0.00 after completion.

    **Validates: Requirements 7.10**
    """

    @TEST_SETTINGS
    @given(
        tab_total=st.floats(min_value=0.01, max_value=1000.00, allow_nan=False),
        percentage=st.sampled_from([10, 15, 20]),
        test_id=st.integers(min_value=0, max_value=2**31)
    )
    def test_tip_reset_on_payment_completion(self, tab_total, percentage, test_id):
        """
        Property 12: Tip Reset on Payment Completion

        Preconditions: Non-zero tip before payment
        Invariant: tip_percentage=None, tip_amount=0 after completion
        """
        # Precondition: tip must be non-zero after rounding
        # Very small tabs (e.g., $0.03 at 10%) round to $0.00 tip
        expected_tip = round(tab_total * (percentage / 100), 2)
        assume(expected_tip > 0)

        # Setup
        store = {}
        session_id = f"test_tip_reset_{test_id}"
        initialize_state(session_id, store)

        # Set up tab and tip
        store[session_id]['payment']['tab_total'] = tab_total
        set_tip(session_id, store, percentage)

        # Verify tip is set
        payment_before = get_payment_state(session_id, store)
        assert payment_before['tip_percentage'] == percentage
        assert payment_before['tip_amount'] > 0

        # Act: Complete payment
        success = atomic_payment_complete(session_id, store)

        # Assert: Payment succeeded and tip is reset
        assert success, "Payment completion should succeed"
        
        payment_after = get_payment_state(session_id, store)
        assert payment_after['tip_percentage'] is None, (
            f"tip_percentage should be None after payment, got {payment_after['tip_percentage']}"
        )
        assert payment_after['tip_amount'] == 0.0, (
            f"tip_amount should be 0 after payment, got {payment_after['tip_amount']}"
        )

    def test_tip_reset_with_10_percent(self):
        """Test tip reset with 10% tip"""
        store = {}
        session_id = "test_tip_reset_10"
        initialize_state(session_id, store)

        store[session_id]['payment']['tab_total'] = 100.00
        set_tip(session_id, store, 10)

        atomic_payment_complete(session_id, store)

        payment = get_payment_state(session_id, store)
        assert payment['tip_percentage'] is None
        assert payment['tip_amount'] == 0.0
        assert payment['tab_total'] == 0.0

    def test_tip_reset_with_15_percent(self):
        """Test tip reset with 15% tip"""
        store = {}
        session_id = "test_tip_reset_15"
        initialize_state(session_id, store)

        store[session_id]['payment']['tab_total'] = 50.00
        set_tip(session_id, store, 15)

        atomic_payment_complete(session_id, store)

        payment = get_payment_state(session_id, store)
        assert payment['tip_percentage'] is None
        assert payment['tip_amount'] == 0.0

    def test_tip_reset_with_20_percent(self):
        """Test tip reset with 20% tip"""
        store = {}
        session_id = "test_tip_reset_20"
        initialize_state(session_id, store)

        store[session_id]['payment']['tab_total'] = 200.00
        set_tip(session_id, store, 20)

        atomic_payment_complete(session_id, store)

        payment = get_payment_state(session_id, store)
        assert payment['tip_percentage'] is None
        assert payment['tip_amount'] == 0.0


# =============================================================================
# Tip UI Property Tests (Properties 13 and 14)
# =============================================================================

from src.ui.tab_overlay import (
    generate_tip_notification,
    generate_tip_removal_notification,
    create_tip_buttons_html,
    TIP_BUTTON_HIGHLIGHT_COLOR,
    TIP_BUTTON_DEFAULT_BG,
    TIP_PERCENTAGES,
)


class TestTipNotificationContent:
    """
    **Feature: stripe-payment, Property 13: Tip Notification Content**

    *For any* tip selection with percentage P in {10, 15, 20} and calculated amount A,
    the generated notification SHALL contain both the percentage value P and the tip amount A.

    **Validates: Requirements 7.11**
    """

    @TEST_SETTINGS
    @given(
        percentage=st.sampled_from([10, 15, 20]),
        tip_amount=st.floats(min_value=0.01, max_value=200.00, allow_nan=False),
        tab_total=st.floats(min_value=0.01, max_value=1000.00, allow_nan=False)
    )
    def test_tip_notification_content(self, percentage, tip_amount, tab_total):
        """
        Property 13: Tip Notification Content

        Generators: percentage in {10, 15, 20}, amount in [0.01, 200.00]
        Invariant: notification contains both percentage and amount values
        """
        # Act
        notification = generate_tip_notification(percentage, tip_amount, tab_total)

        # Assert: notification contains percentage value
        assert str(percentage) in notification, (
            f"Notification should contain percentage {percentage}: {notification}"
        )

        # Assert: notification contains tip amount (formatted to 2 decimal places)
        # The amount could be formatted as $X.XX or just X.XX
        amount_str = f"{tip_amount:.2f}"
        assert amount_str in notification, (
            f"Notification should contain amount {amount_str}: {notification}"
        )

    def test_notification_10_percent(self):
        """Test notification for 10% tip"""
        notification = generate_tip_notification(10, 10.00, 100.00)
        assert "10" in notification
        assert "10.00" in notification

    def test_notification_15_percent(self):
        """Test notification for 15% tip"""
        notification = generate_tip_notification(15, 15.00, 100.00)
        assert "15" in notification
        assert "15.00" in notification

    def test_notification_20_percent(self):
        """Test notification for 20% tip"""
        notification = generate_tip_notification(20, 20.00, 100.00)
        assert "20" in notification
        assert "20.00" in notification

    def test_notification_small_amount(self):
        """Test notification with small tip amount"""
        notification = generate_tip_notification(10, 0.50, 5.00)
        assert "10" in notification
        assert "0.50" in notification

    def test_notification_large_amount(self):
        """Test notification with large tip amount"""
        notification = generate_tip_notification(20, 200.00, 1000.00)
        assert "20" in notification
        assert "200.00" in notification

    def test_removal_notification_exists(self):
        """Test that removal notification is generated"""
        notification = generate_tip_removal_notification()
        assert notification is not None
        assert len(notification) > 0
        assert isinstance(notification, str)


class TestTipButtonVisualState:
    """
    **Feature: stripe-payment, Property 14: Tip Button Visual State**

    *For any* tip selection state with selected_percentage P (where P is 10, 15, 20, or None),
    exactly one button SHALL have the highlighted style (#4CAF50 background) when P is not None,
    and zero buttons SHALL have the highlighted style when P is None.

    **Validates: Requirements 7.8**
    """

    @TEST_SETTINGS
    @given(
        selected_percentage=st.sampled_from([10, 15, 20, None]),
        tab_amount=st.floats(min_value=0.01, max_value=1000.00, allow_nan=False)
    )
    def test_tip_button_visual_state(self, selected_percentage, tab_amount):
        """
        Property 14: Tip Button Visual State

        Generators: selected_percentage in {10, 15, 20, None}
        Invariant: exactly one button highlighted when P != None, zero when P == None
        """
        # Act
        html = create_tip_buttons_html(tab_amount, selected_percentage)

        # Count highlighted buttons (those with the highlight color)
        highlight_count = html.count(TIP_BUTTON_HIGHLIGHT_COLOR)

        if selected_percentage is not None:
            # Exactly one button should be highlighted
            # The highlight color appears in both background and border for selected button
            # So we expect 2 occurrences (background + border) for the selected button
            assert highlight_count == 2, (
                f"Expected exactly one button highlighted (2 color occurrences) "
                f"when percentage={selected_percentage}, got {highlight_count} occurrences"
            )
        else:
            # No buttons should be highlighted
            assert highlight_count == 0, (
                f"Expected no buttons highlighted when percentage=None, "
                f"got {highlight_count} occurrences"
            )

    def test_10_percent_selected(self):
        """Test visual state when 10% is selected"""
        html = create_tip_buttons_html(100.00, 10)
        
        # 10% button should have highlight color
        assert TIP_BUTTON_HIGHLIGHT_COLOR in html
        
        # Count occurrences - should be 2 (background + border for one button)
        assert html.count(TIP_BUTTON_HIGHLIGHT_COLOR) == 2

    def test_15_percent_selected(self):
        """Test visual state when 15% is selected"""
        html = create_tip_buttons_html(100.00, 15)
        
        assert TIP_BUTTON_HIGHLIGHT_COLOR in html
        assert html.count(TIP_BUTTON_HIGHLIGHT_COLOR) == 2

    def test_20_percent_selected(self):
        """Test visual state when 20% is selected"""
        html = create_tip_buttons_html(100.00, 20)
        
        assert TIP_BUTTON_HIGHLIGHT_COLOR in html
        assert html.count(TIP_BUTTON_HIGHLIGHT_COLOR) == 2

    def test_no_selection(self):
        """Test visual state when no tip is selected"""
        html = create_tip_buttons_html(100.00, None)
        
        # No buttons should have highlight color
        assert TIP_BUTTON_HIGHLIGHT_COLOR not in html

    def test_buttons_disabled_when_tab_zero(self):
        """Test that buttons are disabled when tab is $0"""
        html = create_tip_buttons_html(0.00, None)
        
        # Buttons should be hidden (display: none)
        assert 'display: none' in html

    def test_buttons_enabled_when_tab_nonzero(self):
        """Test that buttons are enabled when tab is non-zero"""
        html = create_tip_buttons_html(50.00, None)
        
        # Buttons should be visible (display: flex)
        assert 'display: flex' in html

    def test_all_three_buttons_present(self):
        """Test that all three tip buttons are present"""
        html = create_tip_buttons_html(100.00, None)
        
        for percentage in TIP_PERCENTAGES:
            assert f'{percentage}%' in html, (
                f"Button for {percentage}% should be present"
            )
