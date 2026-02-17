# Integration Testing

<cite>
**Referenced Files in This Document**
- [tests/conftest.py](file://tests/conftest.py)
- [tests/test_maya_memvid_full.py](file://tests/test_maya_memvid_full.py)
- [tests/test_processor_rag.py](file://tests/test_processor_rag.py)
- [tests/test_processor_security.py](file://tests/test_processor_security.py)
- [tests/test_state_manager.py](file://tests/test_state_manager.py)
- [tests/test_memvid.py](file://tests/test_memvid.py)
- [tests/test_llm_tools.py](file://tests/test_llm_tools.py)
- [tests/test_generation.py](file://tests/test_generation.py)
- [tests/test_session_context.py](file://tests/test_session_context.py)
- [tests/test_payment_properties.py](file://tests/test_payment_properties.py)
- [src/conversation/processor.py](file://src/conversation/processor.py)
- [src/utils/state_manager.py](file://src/utils/state_manager.py)
- [src/llm/tools.py](file://src/llm/tools.py)
- [src/rag/memvid_pipeline.py](file://src/rag/memvid_pipeline.py)
- [src/security/scanner.py](file://src/security/scanner.py)
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
10. [Appendices](#appendices)

## Introduction
This document describes integration testing in MayaMCP with a focus on validating component interactions across multi-component workflows. It covers:
- Conversation-RAG integration and Memvid coordination
- Security scanning pipelines
- LLM tool execution and payment processing workflows
- State management across components
- Test setup for external services, API keys, and optional third-party SDKs
- Patterns for data persistence, cross-component state synchronization, and error propagation
- Environment configuration, cleanup, and handling of flaky tests

## Project Structure
MayaMCP organizes integration concerns across:
- Conversation processing orchestrating LLM, tools, RAG, and security
- State management for conversation and payment lifecycles
- RAG pipelines (FAISS and Memvid) with Google Generative AI
- Payment tools backed by Stripe MCP
- Security scanning using optional llm-guard

```mermaid
graph TB
subgraph "Conversation Layer"
PRC["processor.py<br/>process_order(...)"]
PHM["phase_manager.py<br/>(used by processor)"]
end
subgraph "State & Tools"
STM["state_manager.py<br/>initialize_state(), update_order_state(), atomic_*()"]
LLMTOOLS["llm/tools.py<br/>get_all_tools(), add_to_order(), pay_bill(), ..."]
end
subgraph "RAG Pipelines"
MEMVID["memvid_pipeline.py<br/>memvid_rag_pipeline(), generate_memvid_response()"]
GENAI["google-generativeai<br/>(external)"]
end
subgraph "Security"
SCNR["security/scanner.py<br/>scan_input(), scan_output()"]
end
PRC --> SCNR
PRC --> LLMTOOLS
PRC --> PHM
PRC --> STM
PRC --> MEMVID
MEMVID --> GENAI
```

**Diagram sources**
- [src/conversation/processor.py](file://src/conversation/processor.py#L73-L200)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L1-L200)
- [src/llm/tools.py](file://src/llm/tools.py#L1-L200)
- [src/rag/memvid_pipeline.py](file://src/rag/memvid_pipeline.py#L1-L108)
- [src/security/scanner.py](file://src/security/scanner.py#L1-L137)

**Section sources**
- [tests/conftest.py](file://tests/conftest.py#L1-L130)
- [tests/test_maya_memvid_full.py](file://tests/test_maya_memvid_full.py#L1-L250)
- [tests/test_processor_rag.py](file://tests/test_processor_rag.py#L1-L83)
- [tests/test_processor_security.py](file://tests/test_processor_security.py#L1-L81)
- [tests/test_state_manager.py](file://tests/test_state_manager.py#L1-L370)
- [tests/test_memvid.py](file://tests/test_memvid.py#L1-L123)
- [tests/test_llm_tools.py](file://tests/test_llm_tools.py#L1-L704)
- [tests/test_generation.py](file://tests/test_generation.py#L1-L169)
- [tests/test_session_context.py](file://tests/test_session_context.py#L1-L242)
- [tests/test_payment_properties.py](file://tests/test_payment_properties.py#L1-L800)
- [src/conversation/processor.py](file://src/conversation/processor.py#L1-L200)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L1-L200)
- [src/llm/tools.py](file://src/llm/tools.py#L1-L200)
- [src/rag/memvid_pipeline.py](file://src/rag/memvid_pipeline.py#L1-L108)
- [src/security/scanner.py](file://src/security/scanner.py#L1-L137)

## Core Components
- Processor orchestration: Validates security, sets session context, detects intents, invokes tools, and manages conversation phases.
- State manager: Provides thread-safe, versioned state for conversation and payment, with atomic operations and validation.
- LLM tools: Encapsulate bartending operations and payment actions, returning structured success/error responses.
- RAG pipelines: Retrieve context from FAISS or Memvid and augment LLM responses.
- Security scanner: Optional input/output scanning with graceful fallbacks.

Key integration points validated by tests:
- Conversation-RAG-Memvid loop with optional FAISS
- Security scanning at input and output
- Payment tool workflows with atomic state updates and error codes
- Session context propagation through tools

**Section sources**
- [src/conversation/processor.py](file://src/conversation/processor.py#L73-L200)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L1-L200)
- [src/llm/tools.py](file://src/llm/tools.py#L1-L200)
- [src/rag/memvid_pipeline.py](file://src/rag/memvid_pipeline.py#L1-L108)
- [src/security/scanner.py](file://src/security/scanner.py#L1-L137)

## Architecture Overview
The integration flow ties together processor orchestration, state management, RAG augmentation, and security scanning.

```mermaid
sequenceDiagram
participant T as "Integration Test"
participant P as "processor.process_order"
participant S as "security.scanner"
participant L as "llm.tools"
participant SM as "state_manager"
participant MP as "memvid_pipeline"
T->>P : "process_order(user_input, session_id, llm, ...)"
P->>S : "scan_input(user_input)"
S-->>P : "ScanResult(valid)"
P->>SM : "initialize_state(session_id) on first call"
P->>L : "get_all_tools()"
alt "Order-related intent"
P->>L : "tool.invoke(...)"
L->>SM : "update_order_state()/atomic_*()"
SM-->>L : "state updated"
L-->>P : "tool result"
else "Casual conversation"
P->>MP : "memvid_rag_pipeline(query, retriever, api_key)"
MP-->>P : "Memvid-enhanced response"
end
P->>S : "scan_output(agent_response)"
S-->>P : "ScanResult(valid/sanitized)"
P-->>T : "response, updated_history, state"
```

**Diagram sources**
- [src/conversation/processor.py](file://src/conversation/processor.py#L73-L200)
- [src/security/scanner.py](file://src/security/scanner.py#L32-L96)
- [src/llm/tools.py](file://src/llm/tools.py#L1-L200)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L1-L200)
- [src/rag/memvid_pipeline.py](file://src/rag/memvid_pipeline.py#L65-L108)

## Detailed Component Analysis

### Conversation-RAG Integration and Memvid Coordination
- Tests validate that:
  - RAG is short-circuited when components are missing
  - Non-sized RAG responses do not replace base responses
  - Memvid pipeline augments responses with video memory insights
  - Full Maya-Memvid workflow initializes logging, loads API keys, sets up state, initializes LLM and Memvid store, and executes multi-turn conversations

```mermaid
sequenceDiagram
participant IT as "test_maya_memvid_full"
participant CFG as "config.get_api_keys/setup_logging"
participant ST as "utils.state_manager.initialize_state"
participant LLM as "llm.initialize_llm/get_all_tools"
participant MV as "rag.initialize_memvid_store"
participant PR as "conversation.process_order"
IT->>CFG : "setup_logging()"
IT->>CFG : "get_api_keys()"
IT->>ST : "initialize_state()"
IT->>LLM : "get_all_tools()"
IT->>LLM : "initialize_llm(api_key, tools)"
IT->>MV : "initialize_memvid_store()"
IT->>PR : "process_order(..., rag_retriever=memvid_retriever)"
PR-->>IT : "response, updated_history, state"
```

**Diagram sources**
- [tests/test_maya_memvid_full.py](file://tests/test_maya_memvid_full.py#L16-L182)
- [src/conversation/processor.py](file://src/conversation/processor.py#L73-L200)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L1-L200)
- [src/llm/tools.py](file://src/llm/tools.py#L1-L200)
- [src/rag/memvid_pipeline.py](file://src/rag/memvid_pipeline.py#L65-L108)

**Section sources**
- [tests/test_processor_rag.py](file://tests/test_processor_rag.py#L27-L82)
- [tests/test_maya_memvid_full.py](file://tests/test_maya_memvid_full.py#L16-L182)
- [tests/test_memvid.py](file://tests/test_memvid.py#L27-L117)
- [tests/test_generation.py](file://tests/test_generation.py#L49-L169)

### Security Scanning Pipelines
- Tests verify:
  - Injection attempts are blocked and return a safe message
  - Toxic outputs are sanitized and replaced with a safe fallback
  - Valid interactions pass through both input and output scanners

```mermaid
flowchart TD
Start(["User Input"]) --> ScanIn["scan_input(text)"]
ScanIn --> InValid{"Valid?"}
InValid --> |No| BlockMsg["Return blocked reason"]
InValid --> |Yes| InvokeLLM["Invoke LLM/tool"]
InvokeLLM --> ScanOut["scan_output(agent_response, prompt)"]
ScanOut --> OutValid{"Valid?"}
OutValid --> |No| Sanitize["Replace with safe fallback"]
OutValid --> |Yes| PassThrough["Return agent response"]
BlockMsg --> End(["Response"])
Sanitize --> End
PassThrough --> End
```

**Diagram sources**
- [src/security/scanner.py](file://src/security/scanner.py#L32-L96)
- [src/security/scanner.py](file://src/security/scanner.py#L98-L136)
- [tests/test_processor_security.py](file://tests/test_processor_security.py#L26-L80)

**Section sources**
- [tests/test_processor_security.py](file://tests/test_processor_security.py#L1-L81)
- [src/security/scanner.py](file://src/security/scanner.py#L1-L137)

### LLM Tool Execution and Payment Workflows
- Tests validate:
  - Tool discovery and invocation
  - Menu retrieval, recommendations, and order operations
  - Atomic payment operations with error handling and state resets
  - Property-based tests for balance deduction, insufficient funds, tab accumulation, and completion state reset

```mermaid
sequenceDiagram
participant T as "test_llm_tools"
participant L as "llm.tools.get_all_tools()"
participant A as "add_to_order.invoke(...)"
participant G as "get_menu.invoke()"
participant U as "update_order_state(...)"
participant P as "pay_bill.invoke()"
T->>L : "get_all_tools()"
T->>A : "invoke({item, modifiers, quantity})"
A->>G : "invoke()"
G-->>A : "menu text"
A->>U : "add_item"
U-->>A : "updated state"
A-->>T : "success message"
T->>P : "invoke()"
P->>U : "pay_bill"
U-->>P : "updated state"
P-->>T : "confirmation"
```

**Diagram sources**
- [tests/test_llm_tools.py](file://tests/test_llm_tools.py#L652-L677)
- [tests/test_llm_tools.py](file://tests/test_llm_tools.py#L127-L157)
- [tests/test_llm_tools.py](file://tests/test_llm_tools.py#L494-L544)
- [src/llm/tools.py](file://src/llm/tools.py#L1-L200)

**Section sources**
- [tests/test_llm_tools.py](file://tests/test_llm_tools.py#L1-L704)
- [tests/test_payment_properties.py](file://tests/test_payment_properties.py#L59-L263)
- [src/llm/tools.py](file://src/llm/tools.py#L1-L200)

### State Management Across Components
- Tests validate:
  - Initialization, copying semantics, and reset behavior
  - Order updates (add item, place order, clear order, add tip, pay bill)
  - Atomic payment operations and error propagation
  - Thread-local session context isolation and processor lifecycle

```mermaid
flowchart TD
Init["initialize_state(session_id, store)"] --> UpdateConv["update_conversation_state(...)"]
Init --> UpdateOrder["update_order_state(...)"]
UpdateOrder --> PlaceOrder{"Action: place/clear/pay/tip?"}
PlaceOrder --> |place| Finish["is_order_finished = True"]
PlaceOrder --> |clear| Unfinish["is_order_finished = False"]
PlaceOrder --> |pay| Paid["order_history.paid = True"]
PlaceOrder --> |tip| Tip["order_history.tip_* updated"]
UpdateOrder --> Atomic["atomic_order_update()/atomic_payment_complete()"]
Atomic --> Validate["validate_payment_state()"]
Validate --> Reset["reset_session_state()"]
```

**Diagram sources**
- [tests/test_state_manager.py](file://tests/test_state_manager.py#L53-L370)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L66-L167)

**Section sources**
- [tests/test_state_manager.py](file://tests/test_state_manager.py#L1-L370)
- [tests/test_session_context.py](file://tests/test_session_context.py#L118-L209)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L1-L200)

## Dependency Analysis
- Optional third-party SDKs are stubbed to enable local testing without external dependencies.
- Global fixtures configure flags for expensive resource rebuilds.
- Tests isolate and mock external integrations (LLM, RAG, security) to validate internal flows.

```mermaid
graph TB
CF["tests/conftest.py<br/>pytest fixtures & stubs"]
GM["google.generativeai<br/>(stubbed if missing)"]
LG["llm-guard<br/>(optional scanner)"]
CF --> GM
CF --> LG
```

**Diagram sources**
- [tests/conftest.py](file://tests/conftest.py#L1-L130)

**Section sources**
- [tests/conftest.py](file://tests/conftest.py#L1-L130)

## Performance Considerations
- Prefer session-scoped fixtures for shared resources (e.g., LLM clients) to reduce repeated initialization overhead.
- Use the force-rebuild flag to control expensive Memvid store rebuilds in development vs. CI.
- Avoid unnecessary retries in integration tests; rely on deterministic mocking and controlled environments.
- Keep RAG retrievers and pipelines initialized once per test session when feasible.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Missing API keys or external service credentials:
  - Tests skip when keys are absent; ensure environment variables are set or use stubs.
- Flaky external service calls:
  - Use mocks and stubs to simulate service behavior; validate error handling paths.
- State inconsistencies:
  - Ensure session context is cleared after processing; use atomic operations for payment updates.
- Cleanup failures:
  - Tests include best-effort cleanup for LLM clients, retrievers, loggers, and state resets.

**Section sources**
- [tests/test_maya_memvid_full.py](file://tests/test_maya_memvid_full.py#L196-L247)
- [tests/test_processor_security.py](file://tests/test_processor_security.py#L26-L80)
- [tests/test_generation.py](file://tests/test_generation.py#L49-L169)
- [tests/test_session_context.py](file://tests/test_session_context.py#L118-L209)

## Conclusion
MayaMCP’s integration tests validate end-to-end workflows spanning conversation orchestration, RAG augmentation (including Memvid), security scanning, payment processing, and state synchronization. By leveraging mocks, stubs, and controlled fixtures, the suite ensures robustness, reproducibility, and maintainability across component boundaries.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### Test Environment Configuration
- Optional third-party SDKs are stubbed to allow local execution without installation.
- A force-rebuild flag controls expensive resource initialization for development vs. CI.

**Section sources**
- [tests/conftest.py](file://tests/conftest.py#L1-L130)
- [tests/test_memvid.py](file://tests/test_memvid.py#L27-L64)

### Example Integration Test Patterns
- Full Maya-Memvid workflow: initialize logging, load API keys, set state, initialize LLM and Memvid, execute multi-turn conversations, validate responses and order state, and perform cleanup.
- RAG short-circuit and resilience: verify behavior when RAG components are missing or return non-sized results.
- Security scanning: verify blocking of injections and sanitization of toxic outputs.
- Payment workflows: validate atomic updates, insufficient funds handling, tab accumulation, and completion state reset.

**Section sources**
- [tests/test_maya_memvid_full.py](file://tests/test_maya_memvid_full.py#L16-L182)
- [tests/test_processor_rag.py](file://tests/test_processor_rag.py#L27-L82)
- [tests/test_processor_security.py](file://tests/test_processor_security.py#L26-L80)
- [tests/test_payment_properties.py](file://tests/test_payment_properties.py#L59-L263)