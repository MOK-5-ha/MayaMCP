# State Management Patterns

<cite>
**Referenced Files in This Document**
- [state_manager.py](file://src/utils/state_manager.py)
- [api_keys.py](file://src/config/api_keys.py)
- [key_validator.py](file://src/llm/key_validator.py)
- [api_key_modal.py](file://src/ui/api_key_modal.py)
- [phase_manager.py](file://src/conversation/phase_manager.py)
- [processor.py](file://src/conversation/processor.py)
- [helpers.py](file://src/utils/helpers.py)
- [handlers.py](file://src/ui/handlers.py)
- [launcher.py](file://src/ui/launcher.py)
- [tools.py](file://src/llm/tools.py)
- [stripe_mcp.py](file://src/payments/stripe_mcp.py)
- [test_state_manager.py](file://tests/test_state_manager.py)
- [test_session_context.py](file://tests/test_session_context.py)
- [test_speech_acts.py](file://tests/test_speech_acts.py)
- [test_api_keys.py](file://tests/test_api_keys.py)
</cite>

## Update Summary
**Changes Made**
- Enhanced memory management with improved session lock tracking and cleanup procedures
- Added session expiry mechanism with background cleanup for inactive sessions
- Improved error handling for edge cases with comprehensive resource cleanup
- Strengthened concurrency control with proper isolation for complex multi-session scenarios
- Added background cleanup procedures for session locks and expired resources

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
This document describes MayaMCP's state management system with a focus on multi-dimensional state tracking and persistence across interactions. The system maintains conversation context, order history, payment information, and API key credentials for each user session. It includes robust state transition patterns for conversation phases, order states, payment workflows, and API key validation, along with helper utilities for speech act detection, order processing, and context preservation. The document explains state synchronization mechanisms between UI, conversation processor, and payment tools, enhanced concurrency control strategies for multi-user sessions, improved memory management with session expiry and cleanup procedures, and validation, cleanup, and error recovery mechanisms that ensure system stability and data integrity.

## Project Structure
MayaMCP organizes state management across several modules:
- State manager: central session store, typed payment state, API key state, validation, and atomic operations with enhanced memory management
- API key management: environment-based key retrieval, validation, and BYOK authentication
- Conversation processor: orchestrates LLM interactions, tool calls, and state updates
- Phase manager: manages conversation phases and transitions
- Helpers: speech act detection, intent classification, and casual conversation detection
- UI handlers and launcher: bridge Gradio events to state updates and render overlays
- Tools: LLM tools that operate on session state and drive payment workflows
- Payments: Stripe MCP client for payment link creation and status polling

```mermaid
graph TB
subgraph "Enhanced Memory Management Layer"
StateMgr["State Manager<br/>src/utils/state_manager.py"]
SessionLocks["Session Locks<br/>Thread-safe Dict"]
ExpiryMechanism["Session Expiry<br/>Background Cleanup"]
CleanupProcedures["Resource Cleanup<br/>Lock & Client Management"]
end
subgraph "API Key Management Layer"
APIKeys["API Keys Config<br/>src/config/api_keys.py"]
KeyValidator["Key Validator<br/>src/llm/key_validator.py"]
APIKeyModal["API Key Modal<br/>src/ui/api_key_modal.py"]
end
subgraph "UI Layer"
UI_Handlers["UI Handlers<br/>src/ui/handlers.py"]
UI_Launcher["UI Launcher<br/>src/ui/launcher.py"]
end
subgraph "Conversation Layer"
Processor["Conversation Processor<br/>src/conversation/processor.py"]
PhaseMgr["Phase Manager<br/>src/conversation/phase_manager.py"]
Helpers["Helpers<br/>src/utils/helpers.py"]
end
subgraph "Payments"
Stripe["Stripe MCP Client<br/>src/payments/stripe_mcp.py"]
end
StateMgr --> SessionLocks
StateMgr --> ExpiryMechanism
StateMgr --> CleanupProcedures
APIKeys --> KeyValidator
APIKeyModal --> StateMgr
UI_Handlers --> Processor
UI_Launcher --> UI_Handlers
Processor --> PhaseMgr
Processor --> Helpers
Processor --> StateMgr
Processor --> Tools
Tools --> StateMgr
Tools --> Stripe
PhaseMgr --> StateMgr
```

**Diagram sources**
- [state_manager.py](file://src/utils/state_manager.py#L195-L243)
- [api_keys.py](file://src/config/api_keys.py#L1-L51)
- [key_validator.py](file://src/llm/key_validator.py#L1-L87)
- [api_key_modal.py](file://src/ui/api_key_modal.py#L1-L137)
- [handlers.py](file://src/ui/handlers.py#L23-L392)
- [launcher.py](file://src/ui/launcher.py#L49-L354)
- [processor.py](file://src/conversation/processor.py#L83-L456)
- [phase_manager.py](file://src/conversation/phase_manager.py#L10-L92)
- [helpers.py](file://src/utils/helpers.py#L9-L265)
- [tools.py](file://src/llm/tools.py#L1-L1066)
- [stripe_mcp.py](file://src/payments/stripe_mcp.py#L66-L475)

**Section sources**
- [state_manager.py](file://src/utils/state_manager.py#L1-L871)
- [processor.py](file://src/conversation/processor.py#L1-L456)
- [phase_manager.py](file://src/conversation/phase_manager.py#L1-L92)
- [helpers.py](file://src/utils/helpers.py#L1-L265)
- [handlers.py](file://src/ui/handlers.py#L1-L392)
- [launcher.py](file://src/ui/launcher.py#L1-L354)
- [tools.py](file://src/llm/tools.py#L1-L1066)
- [stripe_mcp.py](file://src/payments/stripe_mcp.py#L1-L475)
- [api_keys.py](file://src/config/api_keys.py#L1-L51)
- [key_validator.py](file://src/llm/key_validator.py#L1-L87)
- [api_key_modal.py](file://src/ui/api_key_modal.py#L1-L137)

## Core Components
- Enhanced session-based state architecture: Each user session maintains a structured state dictionary with conversation, order history, current order, payment, and API key sub-states. The state manager provides initialization, getters, setters, and atomic operations with validation, plus sophisticated memory management with session expiry and cleanup.
- API key state management: Session-based storage of Gemini and Cartesia API keys with validation and thread-safe access patterns for BYOK authentication.
- Conversation phase management: The phase manager tracks conversation progression (greeting, order_taking, small_talk, reorder_prompt) and updates counters and timestamps.
- Payment state machine: Typed payment state with strict validation, enforced status transitions, and idempotency keys. Atomic operations ensure consistency under concurrent access.
- Helper utilities: Speech act detection and casual conversation classification guide RAG usage and intent routing.
- UI synchronization: Handlers and launcher synchronize state changes to the UI, animate tab/balance/tip overlays, and manage avatar emotion states.
- Enhanced concurrency control: Thread-safe session locks with expiration tracking, background cleanup procedures, and proper isolation for complex multi-session scenarios.
- Advanced persistence patterns: State stored in a distributed store (e.g., Modal Dict) or local dict for development; session locks persisted to avoid premature GC with comprehensive cleanup mechanisms.
- Comprehensive error handling: Graceful handling of edge cases with proper resource cleanup, memory leak prevention, and fail-safe operations.

**Section sources**
- [state_manager.py](file://src/utils/state_manager.py#L17-L871)
- [phase_manager.py](file://src/conversation/phase_manager.py#L10-L92)
- [helpers.py](file://src/utils/helpers.py#L9-L265)
- [handlers.py](file://src/ui/handlers.py#L23-L392)
- [launcher.py](file://src/ui/launcher.py#L49-L354)
- [tools.py](file://src/llm/tools.py#L1-L1066)
- [api_keys.py](file://src/config/api_keys.py#L1-L51)
- [key_validator.py](file://src/llm/key_validator.py#L1-L87)
- [api_key_modal.py](file://src/ui/api_key_modal.py#L1-L137)

## Architecture Overview
The state management architecture follows a layered design with enhanced memory management:
- Enhanced API key management layer handles environment-based key retrieval and validation
- UI layer receives user input and invokes handlers
- Handlers call the conversation processor with validated API keys
- Processor orchestrates LLM interactions, detects intents/speech acts, and updates state
- Phase manager updates conversation phases and counters
- Tools operate on session state and drive payment workflows
- State manager validates and persists state atomically with API key management and advanced memory management
- UI renders overlays reflecting state changes
- Background cleanup processes monitor session expiry and clean up inactive resources

```mermaid
sequenceDiagram
participant User as "User"
participant UI as "UI Launcher<br/>handlers.py"
participant Proc as "Conversation Processor<br/>processor.py"
participant PM as "Phase Manager<br/>phase_manager.py"
participant SM as "State Manager<br/>state_manager.py"
participant TL as "Tools<br/>tools.py"
participant ST as "Stripe MCP<br/>stripe_mcp.py"
User->>UI : "Text input"
UI->>Proc : "process_order(...)"
Proc->>SM : "has_valid_keys()"
Proc->>SM : "get_api_key_state()"
Proc->>PM : "get_current_phase()"
Proc->>SM : "get_*_state(...)"
Proc->>Proc : "detect_speech_acts()/detect_order_inquiry()"
alt "Order confirmation"
Proc->>TL : "add_to_order_with_balance(...)"
TL->>SM : "atomic_order_update(...)"
SM-->>TL : "success/new_balance"
TL-->>Proc : "confirmation"
Proc->>PM : "update_phase(order_placed=True)"
else "Intent-based tool"
Proc->>TL : "get_order/get_bill/pay_bill/..."
TL->>SM : "update_order_state(...)/get_payment_state(...)"
TL-->>Proc : "tool result"
end
Proc->>SM : "update_conversation_state(...)"
Proc-->>UI : "response + order state"
UI->>UI : "create_tab_overlay_html(...)"
UI-->>User : "Chatbot + audio + overlay"
Note over SM : "Background cleanup<br/>Session expiry<br/>Memory management"
```

**Diagram sources**
- [handlers.py](file://src/ui/handlers.py#L23-L184)
- [processor.py](file://src/conversation/processor.py#L83-L456)
- [phase_manager.py](file://src/conversation/phase_manager.py#L42-L67)
- [state_manager.py](file://src/utils/state_manager.py#L492-L509)
- [tools.py](file://src/llm/tools.py#L221-L1066)
- [stripe_mcp.py](file://src/payments/stripe_mcp.py#L183-L475)

## Detailed Component Analysis

### Enhanced State Manager: Multi-Dimensional Session State with Advanced Memory Management
The state manager defines:
- Typed payment state with strict validation and enforced status transitions
- Default state templates for conversation, order history, current order, and API keys
- Thread-safe session locking with expiration tracking and comprehensive cleanup
- Atomic operations for order updates and payment completion
- API key state management with session-based storage and validation
- Utility functions for tip calculation, payment totals, and validation
- Background cleanup procedures for expired session locks and resources
- Enhanced error handling for edge cases with graceful degradation

Key capabilities:
- Initialize/reset session state with deep-copied defaults including API key state
- Update conversation/order/payment state with validation
- Store and retrieve API key state with thread-safe access patterns
- Atomic order deduction with optimistic locking and version checks
- Atomic payment completion with idempotency and reconciliation flags
- Session lock management with background cleanup and memory leak prevention
- Session expiry tracking with automatic cleanup of inactive resources
- Comprehensive resource cleanup including LLM/TTS client management

```mermaid
classDiagram
class StateManager {
+initialize_state(session_id, store)
+get_conversation_state(session_id, store)
+get_order_history(session_id, store)
+get_current_order_state(session_id, store)
+get_api_key_state(session_id, store)
+set_api_keys(session_id, store, gemini_key, cartesia_key)
+has_valid_keys(session_id, store)
+update_conversation_state(...)
+update_order_state(...)
+get_payment_state(session_id, store)
+update_payment_state(updates)
+atomic_order_update(session_id, store, item_price, expected_version)
+atomic_payment_complete(session_id, store)
+set_tip(session_id, store, percentage)
+get_session_lock(session_id)
+cleanup_session_lock(session_id)
+cleanup_expired_session_locks(max_age)
+reset_session_state(session_id, store)
}
class PaymentState {
+float balance
+float tab_total
+Optional<int> tip_percentage
+float tip_amount
+Optional<string> stripe_payment_id
+string payment_status
+Optional<string> idempotency_key
+int version
+bool needs_reconciliation
}
class SessionLockManager {
+_session_locks : Dict[str, Lock]
+_session_last_access : Dict[str, float]
+get_session_lock(session_id)
+cleanup_session_lock(session_id)
+cleanup_expired_session_locks(max_age)
+SESSION_EXPIRY_SECONDS : int
}
StateManager --> PaymentState : "manages"
StateManager --> SessionLockManager : "uses"
```

**Diagram sources**
- [state_manager.py](file://src/utils/state_manager.py#L195-L243)
- [state_manager.py](file://src/utils/state_manager.py#L613-L871)

**Section sources**
- [state_manager.py](file://src/utils/state_manager.py#L17-L871)

### Enhanced API Key State Management: BYOK Authentication with Improved Security
The API key state management system provides:
- Session-based API key storage with Gemini and Cartesia keys
- Thread-safe key validation and storage with atomic operations
- Integration with Gemini key validator for runtime validation
- Per-session key isolation for multi-user environments
- Graceful handling of missing or invalid API keys with comprehensive error logging
- Encrypted storage of sensitive API keys with proper decryption on retrieval

Key capabilities:
- Store validated API keys in session state with thread-safe locking
- Retrieve API key state for session-specific LLM and TTS clients
- Check if session has valid API keys for authentication gating
- Strip whitespace from API keys and mark as validated upon successful validation
- Integrate with UI modal for user-provided keys and validation feedback
- Secure encryption and decryption of API keys with comprehensive error handling

```mermaid
flowchart TD
Start(["API Key Validation"]) --> CheckSession["Check has_valid_keys()"]
CheckSession --> |Valid| UseKeys["Use existing API keys"]
CheckSession --> |Invalid| ValidateForm["Validate Gemini key from form"]
ValidateForm --> |Valid| EncryptKeys["Encrypt keys with secure manager"]
EncryptKeys --> StoreKeys["set_api_keys() with validated keys"]
StoreKeys --> UseKeys
ValidateForm --> |Invalid| ShowError["Show validation error"]
UseKeys --> Process["Process conversation with validated keys"]
```

**Diagram sources**
- [api_key_modal.py](file://src/ui/api_key_modal.py#L83-L137)
- [key_validator.py](file://src/llm/key_validator.py#L20-L87)
- [state_manager.py](file://src/utils/state_manager.py#L821-L871)

**Section sources**
- [state_manager.py](file://src/utils/state_manager.py#L821-L871)
- [api_key_modal.py](file://src/ui/api_key_modal.py#L1-L137)
- [key_validator.py](file://src/llm/key_validator.py#L1-L87)
- [api_keys.py](file://src/config/api_keys.py#L1-L51)

### Enhanced Conversation Phase Manager: Conversation Flow Control with State Persistence
The phase manager:
- Reads and updates conversation state
- Increments turn counts and small talk counters
- Handles order placement events and resets small talk counters
- Determines next phase based on state and actions
- Decides when to use RAG for casual conversation
- Maintains state persistence across conversation transitions

```mermaid
flowchart TD
Start(["Update Phase"]) --> ReadState["Read conversation state"]
ReadState --> OrderPlaced{"Order placed?"}
OrderPlaced --> |Yes| HandleOrder["handle_order_placed()<br/>reset small_talk_count"]
OrderPlaced --> |No| NextPhase["determine_next_phase()"]
HandleOrder --> NextPhase
NextPhase --> UpdateState["update_conversation_state(phase)"]
UpdateState --> End(["Return next phase"])
```

**Diagram sources**
- [phase_manager.py](file://src/conversation/phase_manager.py#L42-L67)
- [helpers.py](file://src/utils/helpers.py#L71-L112)

**Section sources**
- [phase_manager.py](file://src/conversation/phase_manager.py#L10-L92)
- [helpers.py](file://src/utils/helpers.py#L71-L112)

### Enhanced Conversation Processor: Intent Detection and Tool Orchestration with Session Context
The processor:
- Performs security scanning on input and output
- Sets thread-local session context for tools
- Validates API key presence before processing
- Detects speech acts and order inquiries
- Routes to appropriate tools or LLM with tool-calling
- Updates conversation state and phases
- Integrates RAG enhancement for casual conversation
- Manages session context lifecycle with proper cleanup

```mermaid
sequenceDiagram
participant Proc as "Processor"
participant Detect as "Speech Act/Intent"
participant Tools as "Tools"
participant LLM as "LLM"
participant PM as "Phase Manager"
Proc->>Proc : "validate_api_key_presence()"
Proc->>Detect : "detect_speech_acts()/detect_order_inquiry()"
alt "Order confirmation"
Proc->>Tools : "add_to_order_with_balance(...)"
Tools-->>Proc : "confirmation"
Proc->>PM : "update_phase(order_placed=True)"
else "Intent-based"
Proc->>Tools : "get_order/get_bill/pay_bill/..."
Tools-->>Proc : "tool result"
else "Casual conversation"
Proc->>LLM : "invoke(messages)"
LLM-->>Proc : "AIMessage/tool_calls"
Proc->>Tools : "execute tool_calls"
Tools-->>Proc : "tool results"
end
Proc->>PM : "increment_turn/increment_small_talk/update_phase"
```

**Diagram sources**
- [processor.py](file://src/conversation/processor.py#L83-L456)
- [helpers.py](file://src/utils/helpers.py#L9-L265)
- [tools.py](file://src/llm/tools.py#L221-L1066)

**Section sources**
- [processor.py](file://src/conversation/processor.py#L83-L456)
- [helpers.py](file://src/utils/helpers.py#L9-L265)

### Enhanced UI Handlers and Launcher: State Synchronization and Overlays with Resource Management
The UI layer:
- Extracts session IDs from Gradio requests
- Validates API key presence before processing
- Invokes the processor and generates audio responses
- Updates tab/balance/tip overlays and avatar emotion states
- Provides clear-state and tip-button handlers with notifications
- Manages resource cleanup and session termination
- Integrates with state manager for proper session lifecycle management

```mermaid
sequenceDiagram
participant UI as "UI Launcher"
participant H as "Handlers"
participant Proc as "Processor"
participant SM as "State Manager"
participant TL as "Tools"
UI->>H : "handle_gradio_input(...)"
H->>SM : "has_valid_keys()"
alt "API keys missing"
H-->>UI : "prompt for API keys"
else "API keys valid"
H->>Proc : "process_order(...)"
Proc-->>H : "response + order state"
H->>SM : "get_payment_state(...)"
H->>UI : "overlay_html + audio + state updates"
end
UI->>UI : "render avatar + overlay"
Note over SM : "Cleanup expired sessions<br/>Manage resources"
```

**Diagram sources**
- [handlers.py](file://src/ui/handlers.py#L23-L184)
- [launcher.py](file://src/ui/launcher.py#L49-L354)
- [state_manager.py](file://src/utils/state_manager.py#L492-L509)
- [tools.py](file://src/llm/tools.py#L557-L648)

**Section sources**
- [handlers.py](file://src/ui/handlers.py#L23-L392)
- [launcher.py](file://src/ui/launcher.py#L49-L354)

### Enhanced Payment Tools and Stripe Integration: Atomic Workflows with Comprehensive Error Handling
Payment tools:
- Validate session context and enforce balance checks
- Use atomic operations to update balances and tabs
- Manage tip selection with toggle behavior
- Create payment links with idempotency keys and fallbacks
- Poll payment status and complete payments atomically
- Handle comprehensive error scenarios with graceful fallback
- Implement proper resource cleanup and state recovery

```mermaid
flowchart TD
Start(["Pay Bill"]) --> CheckTab["Check tab_total > 0"]
CheckTab --> |No| Error["Return PAYMENT_FAILED"]
CheckTab --> |Yes| CreateLink["create_stripe_payment()"]
CreateLink --> LinkCreated{"Link created?"}
LinkCreated --> |Yes| Poll["check_payment_status()"]
LinkCreated --> |No| Fallback["Mock payment fallback"]
Poll --> Status{"Status"}
Status --> |succeeded| Complete["atomic_payment_complete()"]
Status --> |failed| Error
Status --> |timeout| Error
Complete --> End(["Paid"])
Fallback --> End
Error --> Cleanup["Cleanup session resources"]
Cleanup --> End
```

**Diagram sources**
- [tools.py](file://src/llm/tools.py#L358-L555)
- [stripe_mcp.py](file://src/payments/stripe_mcp.py#L183-L475)
- [state_manager.py](file://src/utils/state_manager.py#L745-L780)

**Section sources**
- [tools.py](file://src/llm/tools.py#L358-L555)
- [stripe_mcp.py](file://src/payments/stripe_mcp.py#L183-L475)

### Enhanced Memory Management and Session Cleanup Procedures
The state manager now includes sophisticated memory management features:
- Thread-safe session lock tracking with last access time monitoring
- Automatic session expiry detection with configurable timeout periods
- Background cleanup procedures for expired session locks
- Comprehensive resource cleanup including LLM/TTS client management
- Fail-safe error handling for cleanup operations
- Proper isolation mechanisms for complex multi-session scenarios

Key memory management capabilities:
- Track session last access times for expiry detection
- Implement background cleanup with configurable intervals
- Provide explicit cleanup functions for controlled resource release
- Handle cleanup exceptions without affecting main application flow
- Ensure proper cleanup on session reset and application shutdown

```mermaid
flowchart TD
SessionAccess["Session Access"] --> UpdateAccess["Update Last Access Time"]
UpdateAccess --> CheckExpiry["Check Session Expiry"]
CheckExpiry --> |Expired| Cleanup["Cleanup Session Resources"]
CheckExpiry --> |Active| Continue["Continue Processing"]
Cleanup --> RemoveLock["Remove Session Lock"]
Cleanup --> ClearClients["Clear LLM/TTS Clients"]
RemoveLock --> LogCleanup["Log Cleanup Event"]
ClearClients --> LogCleanup
LogCleanup --> Continue
```

**Diagram sources**
- [state_manager.py](file://src/utils/state_manager.py#L201-L243)
- [state_manager.py](file://src/utils/state_manager.py#L492-L509)

**Section sources**
- [state_manager.py](file://src/utils/state_manager.py#L195-L243)
- [state_manager.py](file://src/utils/state_manager.py#L492-L509)

## Dependency Analysis
The state management system exhibits strong cohesion within each module and well-defined interfaces with enhanced memory management:
- API key management depends on environment configuration and key validation
- UI handlers depend on the processor and state manager with API key validation
- Processor depends on phase manager, helpers, state manager, and API key state
- Tools depend on state manager, Stripe MCP client, and validated API keys
- State manager encapsulates validation, concurrency controls, API key state, and memory management
- Enhanced cleanup procedures integrate with session lifecycle management
- Tests validate state transitions, session context, speech act detection, API key management, and memory cleanup
- Background cleanup processes coordinate with main application flow

```mermaid
graph LR
APIKeys["API Keys Config"] --> KeyValidator["Key Validator"]
KeyValidator --> StateMgr["State Manager"]
UI["UI Handlers/Launcher"] --> Proc["Conversation Processor"]
Proc --> PM["Phase Manager"]
Proc --> Help["Helpers"]
Proc --> SM["State Manager"]
Proc --> TL["Tools"]
TL --> SM
TL --> Stripe["Stripe MCP"]
SM --> Stripe
SM --> MemoryMgr["Memory Management"]
MemoryMgr --> Cleanup["Cleanup Procedures"]
Cleanup --> SessionLocks["Session Locks"]
SessionLocks --> Expiry["Expiry Detection"]
```

**Diagram sources**
- [api_keys.py](file://src/config/api_keys.py#L1-L51)
- [key_validator.py](file://src/llm/key_validator.py#L1-L87)
- [state_manager.py](file://src/utils/state_manager.py#L195-L243)
- [handlers.py](file://src/ui/handlers.py#L23-L184)
- [launcher.py](file://src/ui/launcher.py#L49-L354)
- [processor.py](file://src/conversation/processor.py#L83-L456)
- [phase_manager.py](file://src/conversation/phase_manager.py#L10-L92)
- [helpers.py](file://src/utils/helpers.py#L9-L265)
- [tools.py](file://src/llm/tools.py#L1-L1066)
- [stripe_mcp.py](file://src/payments/stripe_mcp.py#L66-L475)

**Section sources**
- [test_state_manager.py](file://tests/test_state_manager.py#L1-L344)
- [test_session_context.py](file://tests/test_session_context.py#L1-L242)
- [test_speech_acts.py](file://tests/test_speech_acts.py#L1-L163)
- [test_api_keys.py](file://tests/test_api_keys.py#L1-L287)

## Performance Considerations
- Atomic operations minimize contention and ensure consistency under concurrent access
- Optimistic locking with version checks reduces lock contention while preventing stale writes
- Thread-safe session locks prevent race conditions without global locks
- Background cleanup of expired session locks avoids memory leaks and reduces overhead
- Enhanced memory management with session expiry detection optimizes resource utilization
- API key validation uses thread-safe locks to prevent concurrent validation conflicts
- RAG enhancement is gated by casual conversation detection and availability checks to avoid unnecessary latency
- UI overlay animations use previous/current values to minimize DOM churn
- Comprehensive error handling prevents cascading failures and maintains system stability
- Resource cleanup procedures ensure proper memory management and prevent resource leaks

## Troubleshooting Guide
Common issues and recovery strategies:
- Insufficient funds: atomic order update returns a specific error code; clients should prompt retry or adjust order
- Concurrent modification: optimistic locking mismatch; clients should re-read state and retry
- Payment timeouts: payment status polling exceeds deadline; advise manual check or retry
- Session context not set: tools require a session context; ensure processor sets it before invoking tools
- API key validation failures: Gemini key validation returns specific error messages for different failure types
- API key missing: handlers check has_valid_keys() and prompt for API key submission
- Speech act detection thresholds: adjust confidence thresholds if misclassification occurs
- State validation failures: payment state validation enforces strict constraints; fix invalid fields before retry
- Memory leaks: ensure cleanup_session_lock is called on session reset; verify background cleanup processes
- Session expiry issues: check SESSION_EXPIRY_SECONDS configuration and cleanup procedure logs
- Resource cleanup failures: verify proper exception handling in cleanup procedures
- Multi-session isolation problems: ensure proper session lock management and isolation boundaries

**Section sources**
- [state_manager.py](file://src/utils/state_manager.py#L666-L871)
- [tools.py](file://src/llm/tools.py#L557-L648)
- [test_state_manager.py](file://tests/test_state_manager.py#L336-L344)
- [test_session_context.py](file://tests/test_session_context.py#L118-L209)
- [test_speech_acts.py](file://tests/test_speech_acts.py#L77-L162)
- [key_validator.py](file://src/llm/key_validator.py#L20-L87)

## Conclusion
MayaMCP's enhanced state management system provides a robust, multi-dimensional session architecture that maintains conversation context, order history, payment state, and API key credentials across interactions. The system enforces strict validation, supports atomic operations, and integrates comprehensive concurrency control with advanced memory management and session cleanup procedures. The system synchronizes state changes to the UI through overlays and animations, and it cleanly separates concerns between UI, conversation processing, and payment workflows. The enhanced API key management enables secure BYOK authentication with per-session key storage and validation. The helper utilities enable intelligent intent detection and context preservation, while sophisticated persistence patterns and comprehensive cleanup procedures ensure long-term reliability and stability. The enhanced memory management with session expiry detection, background cleanup procedures, and proper resource isolation makes the system resilient to edge cases and complex multi-session scenarios.