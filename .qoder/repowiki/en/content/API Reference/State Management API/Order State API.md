# Order State API

<cite>
**Referenced Files in This Document**
- [state_manager.py](file://src/utils/state_manager.py)
- [test_state_manager.py](file://tests/test_state_manager.py)
- [tools.py](file://src/llm/tools.py)
- [processor.py](file://src/conversation/processor.py)
- [test_payment_properties.py](file://tests/test_payment_properties.py)
- [tasks.md](file://.kiro/specs/stripe-payment/tasks.md)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction

The Order State API is a comprehensive system for managing drink ordering workflows in the MayaMCP bartending assistant. It provides atomic order state updates, payment integration, and robust error handling for concurrent modifications. The API manages three primary state areas: current order items, order history tracking, and payment state integration.

The system implements sophisticated concurrency control using thread-safe session locks, optimistic locking for atomic operations, and comprehensive validation for payment state consistency. It supports complex ordering scenarios including multi-item orders, tip calculations, and payment completion workflows.

## Project Structure

The Order State API is implemented primarily in the state management module with supporting components across the application:

```mermaid
graph TB
subgraph "Order State Management"
SM[state_manager.py]
TS[test_state_manager.py]
TPP[test_payment_properties.py]
end
subgraph "LLM Integration"
TL[tools.py]
PR[processor.py]
end
subgraph "UI Integration"
UI[tab_overlay.py]
LH[launcher.py]
HH[handlers.py]
end
subgraph "Payment System"
ST[Stripe MCP Client]
PY[payments/__init__.py]
end
SM --> TL
SM --> PR
SM --> ST
TL --> UI
PR --> UI
ST --> PY
```

**Diagram sources**
- [state_manager.py](file://src/utils/state_manager.py#L1-L814)
- [tools.py](file://src/llm/tools.py#L840-L1039)
- [processor.py](file://src/conversation/processor.py#L150-L349)

**Section sources**
- [state_manager.py](file://src/utils/state_manager.py#L1-L814)
- [tools.py](file://src/llm/tools.py#L840-L1039)

## Core Components

### Order State Data Structure

The order state system maintains three interconnected data structures:

**Current Order Structure:**
```python
{
    'order': List[Dict[str, Any]],  # Active items in current order
    'finished': bool               # Completion status flag
}
```

**Order History Structure:**
```python
{
    'items': List[Dict[str, Any]],     # Complete order history
    'total_cost': float,               # Running total cost
    'paid': bool,                      # Payment completion flag
    'tip_amount': float,               # Applied tip amount
    'tip_percentage': float            # Applied tip percentage
}
```

**Default State Templates:**
The system provides comprehensive default templates ensuring consistent initialization across all sessions. These templates define baseline values for conversation state, order history, current order, and payment state.

### Payment State Integration

The order state API integrates seamlessly with the payment system through atomic operations:

```mermaid
classDiagram
class PaymentState {
+float balance
+float tab_total
+Optional~int~ tip_percentage
+float tip_amount
+Optional~str~ stripe_payment_id
+Literal~pending,processing,completed~ payment_status
+Optional~str~ idempotency_key
+int version
+bool needs_reconciliation
}
class OrderState {
+Dict[] current_order
+Dict~str,Any~ history
+Dict~str,Any~ conversation
+PaymentState payment
}
class AtomicOperations {
+atomic_order_update() Tuple
+atomic_payment_complete() bool
+check_sufficient_funds() Tuple
}
OrderState --> PaymentState : "contains"
OrderState --> AtomicOperations : "uses"
```

**Diagram sources**
- [state_manager.py](file://src/utils/state_manager.py#L17-L58)
- [state_manager.py](file://src/utils/state_manager.py#L447-L508)

**Section sources**
- [state_manager.py](file://src/utils/state_manager.py#L285-L304)
- [state_manager.py](file://src/utils/state_manager.py#L17-L58)

## Architecture Overview

The Order State API follows a layered architecture with clear separation of concerns:

```mermaid
sequenceDiagram
participant Client as "Client Application"
participant Tools as "LLM Tools"
participant StateMgr as "State Manager"
participant Payment as "Payment System"
participant Storage as "Session Store"
Client->>Tools : add_to_order(item)
Tools->>StateMgr : update_order_state("add_item", item)
StateMgr->>StateMgr : validate item data
StateMgr->>Storage : append to current_order
StateMgr->>Storage : update order_history
StateMgr->>Storage : save session state
Client->>Tools : place_order()
Tools->>StateMgr : update_order_state("place_order")
StateMgr->>Storage : mark finished=True
StateMgr->>Storage : clear current_order
StateMgr->>Storage : save session state
Client->>Tools : pay_bill()
Tools->>StateMgr : update_order_state("pay_bill")
StateMgr->>Storage : set paid=True
StateMgr->>Storage : save session state
Client->>Tools : add_tip(percentage)
Tools->>StateMgr : update_order_state("add_tip", data)
StateMgr->>Storage : update tip_amount & percentage
StateMgr->>Storage : save session state
```

**Diagram sources**
- [tools.py](file://src/llm/tools.py#L842-L1039)
- [state_manager.py](file://src/utils/state_manager.py#L447-L508)

## Detailed Component Analysis

### Order State Update Mechanisms

The system provides five primary actions for order state management:

#### Add Item Action (`add_item`)
The `add_item` action processes new drink orders with comprehensive validation:

```mermaid
flowchart TD
Start([Add Item Request]) --> ValidateData["Validate Item Data"]
ValidateData --> DataValid{"Data Valid?"}
DataValid --> |No| SkipUpdate["Skip Update<br/>No Changes Made"]
DataValid --> |Yes| AppendToOrder["Append to Current Order"]
AppendToOrder --> UpdateHistory["Update Order History"]
UpdateHistory --> UpdateCost["Increment Total Cost"]
UpdateCost --> LogAction["Log Addition"]
LogAction --> SaveState["Save Session State"]
SaveState --> End([Operation Complete])
SkipUpdate --> End
```

**Diagram sources**
- [state_manager.py](file://src/utils/state_manager.py#L470-L478)

#### Place Order Action (`place_order`)
The `place_order` action finalizes orders with atomic state changes:

```mermaid
flowchart TD
Start([Place Order Request]) --> CheckOrder["Check Current Order"]
CheckOrder --> HasItems{"Has Items?"}
HasItems --> |No| RejectEmpty["Reject Empty Order"]
HasItems --> |Yes| MarkFinished["Mark Order Finished"]
MarkFinished --> ClearCurrent["Clear Current Order"]
ClearCurrent --> LogAction["Log Placement"]
LogAction --> SaveState["Save Session State"]
SaveState --> End([Order Placed])
RejectEmpty --> End
```

**Diagram sources**
- [state_manager.py](file://src/utils/state_manager.py#L480-L485)

#### Clear Order Action (`clear_order`)
The `clear_order` action resets order state while preserving history:

```mermaid
flowchart TD
Start([Clear Order Request]) --> ClearItems["Clear Current Items"]
ClearItems --> UnfinishOrder["Unmark as Finished"]
UnfinishOrder --> LogAction["Log Clearing"]
LogAction --> SaveState["Save Session State"]
SaveState --> End([Order Cleared])
```

**Diagram sources**
- [state_manager.py](file://src/utils/state_manager.py#L487-L492)

#### Add Tip Action (`add_tip`)
The `add_tip` action calculates and applies tips with validation:

```mermaid
flowchart TD
Start([Add Tip Request]) --> CheckOrder["Check Order Exists"]
CheckOrder --> HasItems{"Has Items?"}
HasItems --> |No| NoTip["No Tip Available"]
HasItems --> |Yes| CheckPaid{"Already Paid?"}
CheckPaid --> |Yes| AlreadyPaid["Already Paid"]
CheckPaid --> |No| CalcTip["Calculate Tip Amount"]
CalcTip --> ValidateTip["Validate Tip Data"]
ValidateTip --> UpdateHistory["Update Tip in History"]
UpdateHistory --> LogAction["Log Tip Addition"]
LogAction --> SaveState["Save Session State"]
SaveState --> End([Tip Added])
NoTip --> End
AlreadyPaid --> End
```

**Diagram sources**
- [state_manager.py](file://src/utils/state_manager.py#L494-L499)

#### Pay Bill Action (`pay_bill`)
The `pay_bill` action marks orders as paid:

```mermaid
flowchart TD
Start([Pay Bill Request]) --> CheckOrder["Check Order Exists"]
CheckOrder --> HasItems{"Has Items?"}
HasItems --> |No| NoBill["No Bill Available"]
HasItems --> |Yes| CheckPaid{"Already Paid?"}
CheckPaid --> |Yes| AlreadyPaid["Already Paid"]
CheckPaid --> |No| MarkPaid["Mark as Paid"]
MarkPaid --> LogAction["Log Payment"]
LogAction --> SaveState["Save Session State"]
SaveState --> End([Bill Paid])
NoBill --> End
AlreadyPaid --> End
```

**Diagram sources**
- [state_manager.py](file://src/utils/state_manager.py#L501-L505)

### Payment State Integration

The order state API integrates with payment state through atomic operations:

```mermaid
sequenceDiagram
participant Client as "Client"
participant StateMgr as "State Manager"
participant Payment as "Payment State"
participant Lock as "Session Lock"
participant Store as "Session Store"
Client->>StateMgr : atomic_order_update(item_price)
StateMgr->>Lock : acquire()
Lock-->>StateMgr : lock acquired
StateMgr->>Store : read current state
Store-->>StateMgr : current state
StateMgr->>StateMgr : validate version
StateMgr->>StateMgr : check sufficient funds
StateMgr->>StateMgr : calculate new balances
alt sufficient funds
StateMgr->>Store : update balance, tab, version
Store-->>StateMgr : success
StateMgr-->>Client : (True, "", new_balance)
else insufficient funds
StateMgr-->>Client : (False, "INSUFFICIENT_FUNDS", current_balance)
end
StateMgr->>Lock : release()
```

**Diagram sources**
- [state_manager.py](file://src/utils/state_manager.py#L685-L756)

**Section sources**
- [state_manager.py](file://src/utils/state_manager.py#L447-L508)
- [state_manager.py](file://src/utils/state_manager.py#L685-L756)

### Concurrency Control and Atomic Operations

The system implements sophisticated concurrency control using thread-safe session locks:

```mermaid
classDiagram
class SessionLockManager {
+Dict~str,Lock~ _session_locks
+Lock _session_locks_mutex
+Dict~str,float~ _session_last_access
+get_session_lock(session_id) Lock
+cleanup_session_lock(session_id) void
+cleanup_expired_session_locks(max_age) int
}
class AtomicOrderUpdate {
+int version
+float balance
+float tab_total
+atomic_order_update() Tuple
+check_sufficient_funds() Tuple
}
class AtomicPaymentComplete {
+reset_tab() void
+reset_tip() void
+set_completed() void
+atomic_payment_complete() bool
}
SessionLockManager --> AtomicOrderUpdate : "provides locks"
SessionLockManager --> AtomicPaymentComplete : "provides locks"
```

**Diagram sources**
- [state_manager.py](file://src/utils/state_manager.py#L194-L282)
- [state_manager.py](file://src/utils/state_manager.py#L685-L814)

**Section sources**
- [state_manager.py](file://src/utils/state_manager.py#L194-L282)
- [state_manager.py](file://src/utils/state_manager.py#L685-L814)

## Dependency Analysis

The Order State API has well-defined dependencies and relationships:

```mermaid
graph TB
subgraph "Core Dependencies"
SM[state_manager.py]
TL[tools.py]
PR[processor.py]
TS[test_state_manager.py]
end
subgraph "Payment Dependencies"
ST[Stripe MCP Client]
PY[payments/__init__.py]
TP[test_payment_properties.py]
end
subgraph "Validation Dependencies"
VAL[Payment State Validation]
TRANS[Status Transitions]
ERR[Error Codes]
end
SM --> TL
SM --> PR
SM --> ST
TL --> SM
PR --> SM
ST --> PY
SM --> VAL
SM --> TRANS
SM --> ERR
TS --> SM
TP --> SM
```

**Diagram sources**
- [state_manager.py](file://src/utils/state_manager.py#L66-L167)
- [tools.py](file://src/llm/tools.py#L842-L1039)

**Section sources**
- [state_manager.py](file://src/utils/state_manager.py#L66-L167)
- [tools.py](file://src/llm/tools.py#L842-L1039)

## Performance Considerations

The Order State API implements several performance optimization strategies:

### Thread-Safe Access Patterns
- Session locks prevent race conditions without blocking the entire system
- Optimistic locking reduces contention for concurrent operations
- Background cleanup tasks manage memory efficiently

### State Management Efficiency
- Deep copying of default states prevents mutation issues
- Efficient state serialization minimizes storage overhead
- Lazy initialization reduces startup costs

### Error Recovery Optimization
- Immediate rejection of invalid operations prevents wasted computation
- Graceful degradation ensures system stability under failure conditions
- Comprehensive logging enables targeted performance analysis

## Troubleshooting Guide

### Common Issues and Solutions

**Order State Inconsistency**
- Symptom: Order state appears inconsistent after concurrent operations
- Solution: Verify session locks are properly acquired and released
- Prevention: Use atomic operations for all state-changing actions

**Payment Validation Errors**
- Symptom: Payment state validation failures during updates
- Solution: Check payment state constraints and validation rules
- Prevention: Use provided validation functions before state updates

**Concurrency Conflicts**
- Symptom: Version mismatch errors during atomic operations
- Solution: Implement retry logic with exponential backoff
- Prevention: Design client applications to handle CONCURRENT_MODIFICATION gracefully

### Debugging Techniques

**State Inspection**
- Use `get_current_order_state()` to inspect current order items
- Use `get_order_history()` to examine order history
- Use `get_payment_state()` to review payment state

**Logging Analysis**
- Monitor INFO level logs for order operations
- Check DEBUG level logs for state updates
- Review ERROR level logs for validation failures

**Performance Monitoring**
- Track atomic operation success rates
- Monitor session lock contention
- Analyze payment state validation performance

**Section sources**
- [test_state_manager.py](file://tests/test_state_manager.py#L303-L370)
- [state_manager.py](file://src/utils/state_manager.py#L66-L167)

## Conclusion

The Order State API provides a robust foundation for drink ordering management in the MayaMCP system. Its comprehensive design addresses key challenges in concurrent modification, payment integration, and error recovery while maintaining high performance and reliability.

Key strengths of the system include:

- **Atomic Operations**: Ensures data consistency through atomic order updates and payment completions
- **Concurrent Safety**: Thread-safe session locks prevent race conditions without impacting performance
- **Comprehensive Validation**: Strict payment state validation prevents invalid states
- **Flexible Integration**: Seamless integration with LLM tools and UI components
- **Error Resilience**: Graceful error handling and recovery mechanisms

The API's modular design allows for easy extension and maintenance while providing clear interfaces for client applications. The extensive test coverage and property-based testing ensure reliability across complex usage scenarios.

Future enhancements could include additional payment methods, advanced tip calculation features, and expanded order history analytics capabilities.