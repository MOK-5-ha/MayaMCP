# Implementation Plan

- [ ] 1. Extend state management with payment state
  - [ ] 1.1 Add payment state schema to state_manager.py
    - Define PaymentState TypedDict with exact types, defaults, and validation:
      ```python
      class PaymentState(TypedDict):
          balance: float          # >= 0, default: 1000.00
          tab_total: float        # >= 0, default: 0.00
          stripe_payment_id: Optional[str]  # None or Stripe ID pattern: ^(plink_|pi_)[a-zA-Z0-9]+$
          payment_status: Literal['pending', 'processing', 'completed']  # default: 'pending'
          idempotency_key: Optional[str]    # None or format: {session_id}_{unix_timestamp}
          version: int            # >= 0, default: 0
          needs_reconciliation: bool  # default: False
      ```
    - Validation rules:
      - balance >= 0, tab_total >= 0, version >= 0
      - stripe_payment_id: None or matches Stripe ID regex
      - idempotency_key: None or alphanumeric with underscore separator
    - Status transitions: pending → processing → completed (no backwards transitions)
    - Mutual constraint: needs_reconciliation == False when payment_status == 'completed'
    - needs_reconciliation lifecycle:
      - Set True: when Stripe link created but local state update failed
      - Set False: upon successful manual/automated reconciliation (increment version)
    - Add validate_payment_state() function to enforce all constraints
    - Add DEFAULT_PAYMENT_STATE instance with all defaults
    - Add payment state to session initialization referencing DEFAULT_PAYMENT_STATE
    - _Requirements: 1.1_
  - [ ] 1.2 Implement thread-safe session locking
    - Add _session_locks Dict[str, Lock] (regular dict, NOT WeakValueDictionary)
    - Add _session_locks_mutex to protect dict access
    - Implement get_session_lock() function:
      - Acquire mutex, get or create lock, return lock (mutex released)
      - Lock instance persists until explicit cleanup
    - Implement cleanup_session_lock() for explicit cleanup on session reset/expiry
    - Call cleanup_session_lock() from reset_session_state()
    - Memory management: locks cleaned up only via explicit cleanup_session_lock() calls
    - Add session expiry mechanism: cleanup locks for sessions inactive >1 hour (background task)
    - _Requirements: 1.2, 1.3_
  - [ ] 1.3 Implement atomic order update function
    - Create atomic_order_update() that acquires lock, checks balance, deducts, adds to tab atomically
    - Implement optimistic locking: read current version, perform update with expected version, fail if version mismatch
    - On version mismatch: return CONCURRENT_MODIFICATION immediately (no automatic retry)
    - Increment version by +1 on each successful update
    - Return (success, error_code, new_balance) tuple
    - Client behavior on CONCURRENT_MODIFICATION: Maya asks user to retry the order
    - _Requirements: 1.2, 1.3, 1.5_
  - [ ] 1.4 Write property test for balance deduction consistency
    - **Property 1: Balance Deduction Consistency**
    - **Validates: Requirements 1.2**
    - Preconditions: Session initialized, balance B >= 0, item price P > 0, B >= P
    - Generators: balance in [0.01, 10000.00], price in [0.01, balance]
    - Invariant: new_balance == B - P exactly (floating point equality with tolerance 0.001)
    - Edge cases: exact balance (B == P), minimum price ($0.01), large amounts ($999.99)
    - Assertion: `assert abs(new_balance - (initial_balance - price)) < 0.001`
  - [ ] 1.5 Write property test for insufficient funds rejection
    - **Property 3: Insufficient Funds Rejection**
    - **Validates: Requirements 1.3**
    - Preconditions: Session initialized, balance B >= 0, item price P > B
    - Generators: balance in [0, 999.99], price in [balance + 0.01, 1000.00]
    - Invariant: order rejected with INSUFFICIENT_FUNDS, balance unchanged
    - Edge cases: zero balance, price exactly $0.01 over balance, very large price
    - Assertion: `assert result.error == "INSUFFICIENT_FUNDS" and new_balance == initial_balance`
  - [ ] 1.6 Write property test for state preservation on rejection
    - **Property 4: State Preservation on Rejection**
    - **Validates: Requirements 1.5**
    - Preconditions: Session with existing order items, insufficient balance for new item
    - Generators: order_items list of 0-10 items, new item price > remaining balance
    - Invariant: order list identical before and after rejection (same items, same order)
    - Edge cases: empty order, single item order, order at max capacity
    - Assertion: `assert order_after == order_before`

- [ ] 2. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Set up session context for tools
  - [ ] 3.1 Add _current_session thread-local variable
    - Create thread-local storage for session context in src/llm/tools.py
    - Initialize with default None (no active session) for backwards compatibility
    - Existing tools that don't use session context continue to work unchanged
    - _Requirements: 1.2_
  - [ ] 3.2 Update process_order to set session context
    - Set _current_session before calling LLM in processor.py
    - Clear _current_session after processing complete (in finally block to handle errors)
    - Initialize from existing session_id parameter passed to process_order
    - Treat None as "no active session" - tools fall back to legacy behavior
    - _Requirements: 1.2_
  - [ ] 3.3 Add unit tests for session context lifecycle
    - Test set/clear semantics work correctly
    - Test legacy code reading from session store still works
    - Test error handling clears context properly
    - _Requirements: 1.2_

- [ ] 4. Implement payment tools
  - [ ] 4.1 Create ToolResponse types and PaymentError enum
    - Define ToolSuccess, ToolError TypedDicts
    - Define PaymentError enum with documented error codes:
      - INSUFFICIENT_FUNDS: balance < order price (Req 1.3)
      - STRIPE_UNAVAILABLE: Stripe MCP server not responding (Req 3.4)
      - PAYMENT_FAILED: Stripe payment processing failed (Req 3.3)
      - CONCURRENT_MODIFICATION: optimistic lock version mismatch (Req 1.3)
      - NETWORK_ERROR: network timeout or connection failure during Stripe calls
      - RATE_LIMITED: Stripe API rate limit exceeded
      - INVALID_SESSION: session_id not found or expired
      - PAYMENT_TIMEOUT: payment status polling exceeded deadline
    - Each error code must have a human-readable message template
    - _Requirements: 1.3, 3.3, 3.4_
  - [ ] 4.2 Implement add_to_order_with_balance tool
    - Get session context from _current_session thread-local
    - Call atomic_order_update from state manager
    - Return structured ToolResponse
    - _Requirements: 1.2, 1.3, 1.5_
  - [ ] 4.3 Implement get_balance tool
    - Return current balance and tab from payment state
    - _Requirements: 1.4_
  - [ ] 4.4 Update existing add_to_order to use balance checking
    - Modify existing tool to call add_to_order_with_balance internally
    - Maintain backward compatibility
    - _Requirements: 1.2_
  - [ ] 4.5 Write property test for tab accumulation accuracy
    - **Property 2: Tab Accumulation Accuracy**
    - **Validates: Requirements 2.2**
    - Preconditions: Session initialized with $1000 balance, empty tab
    - Generators: list of 1-20 item prices, each in [0.01, 50.00], total <= 1000
    - Invariant: tab_total == sum(all_item_prices) exactly
    - Edge cases: single item, many small items, items totaling exactly $1000
    - Assertion: `assert abs(tab_total - sum(prices)) < 0.001`

- [ ] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Create Stripe MCP client
  - [ ] 6.1 Create src/payments/__init__.py and stripe_mcp.py module
    - Create new payments package
    - Define StripeMCPClient class skeleton
    - _Requirements: 3.1, 4.1_
  - [ ] 6.2 Implement idempotency key generation
    - Create generate_idempotency_key() method
    - Format: {session_id}_{unix_timestamp}
    - _Requirements: 3.1_
  - [ ] 6.3 Implement create_payment_link with async retry logic
    - Use non-blocking async retries with `asyncio.sleep()` to avoid blocking request threads
    - Initial attempt, then up to 3 retries (total up to 4 requests, configurable via MAX_RETRIES)
    - Timing sequence: await 1s before 1st retry, 2s before 2nd, 4s before 3rd
    - Configurable overall timeout (default 15s) to cap total retry duration
    - Use Stripe MCP server via kiroPowers tool
    - Fallback behavior when retries exhausted:
      - Log warning with session_id, attempt count, error details
      - Emit metric/alert for fallback events (observable)
      - Surface fallback to user: Maya says "Using backup payment method"
      - Fall back to mock payment
    - _Requirements: 3.1, 3.2, 4.2_
  - [ ] 6.4 Implement is_available check and fallback logic
    - Availability check implementation:
      - Use lightweight probe: attempt to list Stripe MCP server tools via kiroPowers activate
      - Success criteria: server responds within 5 seconds with valid tool list
      - Unavailability indicators: connection refused, timeout, 5xx errors, empty tool list
    - Call is_available() before create_payment_link to avoid unnecessary retries
    - Cache availability result for 30 seconds to reduce probe overhead
    - Return False if unavailable, triggering immediate fallback to mock payment
    - _Requirements: 3.4_
  - [ ] 6.5 Implement check_payment_status with timeout
    - Poll interval: 2 seconds between attempts
    - Per-poll timeout: 5 seconds (each individual poll must complete within 5s)
    - Total wall-clock deadline: 30 seconds for entire polling operation
    - Maximum attempts: 15 (2s interval × 15 = 30s total)
    - Return "timeout" status if wall-clock deadline exceeded
    - _Requirements: 3.3_

- [ ] 7. Implement Stripe payment tools
  - [ ] 7.1 Implement create_stripe_payment tool
    - Generate idempotency key
    - Call StripeMCPClient.create_payment_link
    - Handle fallback to mock payment
    - Return structured response with url, payment_id, is_simulated
    - _Requirements: 3.1, 3.2, 3.4, 4.3_
  - [ ] 7.2 Implement check_payment_status tool
    - Call StripeMCPClient.check_payment_status
    - Handle timeout case
    - _Requirements: 3.3_
  - [ ] 7.3 Implement atomic_payment_complete function
    - Reset tab to $0.00
    - Set payment_status to completed
    - Atomic operation with version check
    - _Requirements: 3.3_
  - [ ] 7.4 Write property test for payment completion state reset
    - **Property 5: Payment Completion State Reset**
    - **Validates: Requirements 3.3**
    - Preconditions: Session with non-zero tab, payment_status != "completed"
    - Generators: tab_total in [0.01, 1000.00], various payment_status values
    - Invariant: after completion, tab_total == 0.00 AND payment_status == "completed"
    - Edge cases: minimum tab ($0.01), maximum tab ($1000), already processing status
    - Assertion: `assert tab_total == 0.0 and payment_status == "completed"`

- [ ] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Create tab overlay UI component
  - [ ] 9.1 Create src/ui/tab_overlay.py module
    - Create new module for tab overlay component
    - _Requirements: 2.1_
  - [ ] 9.2 Implement get_balance_color function
    - Return #FFFFFF for balance >= $50 (normal)
    - Return #FFA500 for 0 < balance < $50 (low funds warning)
    - Return #FF4444 for balance <= $0 (depleted/negative)
    - Every numeric balance maps to exactly one color
    - _Requirements: 6.3, 6.4_
  - [ ] 9.3 Write property test for balance color selection
    - **Property 7: Balance Color Selection**
    - **Validates: Requirements 6.3, 6.4**
    - Preconditions: None (pure function)
    - Generators: balance in [-100.00, 2000.00] covering all ranges
    - Invariant: balance >= 50 → #FFFFFF, 0 < balance < 50 → #FFA500, balance <= 0 → #FF4444
    - Edge cases: exactly $50, exactly $0, negative values, boundary values ($49.99, $50.01)
    - Assertion: `assert get_balance_color(balance) == expected_color`
  - [ ] 9.4 Implement create_tab_overlay_html function
    - Generate HTML with semi-transparent dark background (rgba 0,0,0,0.7)
    - Position at bottom-left with 16px padding
    - Display "Tab: $X.XX" on left, "Balance: $X.XX" on right with 12px gap
    - _Requirements: 2.1, 2.4, 6.1_
  - [ ] 9.5 Implement count-up animation JavaScript
    - Trigger: animation starts whenever displayed value changes (from tool result or state update)
    - Animation lifecycle:
      1. Start from current displayed value
      2. Animate numeric change over 500ms (linear interpolation)
      3. Apply CSS scale pulse 1.0→1.1→1.0 synchronized with numeric animation
      4. Settle to final state
    - Events/hooks: onAnimationStart, onAnimationComplete, onAnimationCancel
    - _Requirements: 2.3, 5.1, 5.2, 5.4_
  - [ ] 9.6 Implement animation queue for rapid updates
    - Serialize updates: new update enqueues and starts only after current 500ms animation completes
    - Collapse strategy (by time window):
      - Updates arriving within 100ms of each other collapse into single animation
      - Collapsed animation shows: start value from first update, end value from last update
      - Example: $100→$50→$25 within 100ms becomes single animation $100→$25
      - Updates arriving >100ms apart animate separately to preserve visual feedback
    - Queue max depth: 5 pending animations (oldest dropped if exceeded)
    - Cancellation: if forced immediate update requested, cancel running animation and render final value instantly
    - Queue behavior: FIFO with time-window collapse optimization
    - _Requirements: 5.3_
  - [ ] 9.7 Write property test for animation queue length
    - **Property 6: Animation Queue Length Consistency**
    - **Validates: Requirements 5.3**
    - Preconditions: Animation queue initialized, no animations running
    - Generators: sequence of 1-50 tab updates with random amounts
    - Invariant: queue length == number of updates added (before any execution)
    - Edge cases: single update, rapid consecutive updates, updates with same amount
    - Assertion: `assert len(animation_queue) == num_updates_added`

- [ ] 10. Integrate tab overlay into Gradio UI
  - [ ] 10.1 Modify launcher.py to include tab overlay
    - Replace static avatar Image with HTML component
    - Create create_avatar_with_overlay function
    - _Requirements: 2.1_
  - [ ] 10.2 Add tab and balance state to Gradio interface
    - Add tab_state and balance_state gr.State components
    - Pass to handler functions
    - _Requirements: 2.2, 6.2_
  - [ ] 10.3 Update handlers to return tab overlay updates
    - Modify handle_gradio_input to return updated overlay HTML
    - Include previous values for animation
    - _Requirements: 2.2, 2.3_
  - [ ] 10.4 Wire up clear button to reset tab overlay
    - Reset all payment state fields to DEFAULT_PAYMENT_STATE values defined in Task 1.1
    - DEFAULT_PAYMENT_STATE: balance=$1000.00, tab_total=$0.00, payment_status="pending", version=0
    - This is a global default applied to all new sessions
    - _Requirements: 1.1_

- [ ] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Add payment tools to LLM tool list
  - [ ] 12.1 Register new payment tools in get_all_tools
    - Add add_to_order_with_balance, get_balance, create_stripe_payment, check_payment_status
    - _Requirements: 1.2, 1.4, 3.1, 3.3_

- [ ] 13. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
