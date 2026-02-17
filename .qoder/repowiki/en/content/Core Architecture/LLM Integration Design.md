# LLM Integration Design

<cite>
**Referenced Files in This Document**
- [client.py](file://src/llm/client.py)
- [tools.py](file://src/llm/tools.py)
- [prompts.py](file://src/llm/prompts.py)
- [model_config.py](file://src/config/model_config.py)
- [api_keys.py](file://src/config/api_keys.py)
- [processor.py](file://src/conversation/processor.py)
- [phase_manager.py](file://src/conversation/phase_manager.py)
- [helpers.py](file://src/utils/helpers.py)
- [state_manager.py](file://src/utils/state_manager.py)
- [stripe_mcp.py](file://src/payments/stripe_mcp.py)
- [logging_config.py](file://src/config/logging_config.py)
- [test_llm_client.py](file://tests/test_llm_client.py)
- [test_llm_tools.py](file://tests/test_llm_tools.py)
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
This document describes the LLM integration system for MayaMCP with a focus on the Google Gemini client configuration and tool calling architecture. It explains how the LLM client abstracts external API interactions and manages model parameters, documents the tool registry pattern used for payment processing, order management, and menu access functions, and details the prompt engineering strategy including phase-based prompting and context injection. It also covers the function calling mechanism enabling bidirectional communication between LLM responses and tool execution, including tool argument validation, error handling, and retry mechanisms. Finally, it addresses integration patterns for different tool types, model configuration, API key management, and fallback strategies for external service failures.

## Project Structure
The LLM integration spans several modules:
- LLM client and configuration: Google Gemini client initialization, model parameter mapping, and API call abstraction
- Tools registry: Payment, order, and menu functions exposed to the LLM
- Prompts: System instructions and phase-specific prompts
- Conversation processor: Orchestrates LLM calls, tool execution, and state updates
- Utilities: State management, helpers, and logging configuration
- Payments: Stripe MCP client with retry and fallback logic

```mermaid
graph TB
subgraph "LLM Layer"
C["client.py<br/>Initialize LLM, call Gemini API"]
T["tools.py<br/>Tool registry and payment/order functions"]
P["prompts.py<br/>System and phase prompts"]
end
subgraph "Conversation"
PR["processor.py<br/>LLM orchestration and tool execution"]
PM["phase_manager.py<br/>Conversation phase management"]
H["helpers.py<br/>Intent detection and speech acts"]
end
subgraph "Utilities"
SM["state_manager.py<br/>Thread-safe state and atomic ops"]
LOG["logging_config.py<br/>Logging setup"]
end
subgraph "Payments"
ST["stripe_mcp.py<br/>Stripe MCP client with retries/fallback"]
end
subgraph "Config"
MC["model_config.py<br/>Model and generation config"]
AK["api_keys.py<br/>API key management"]
end
C --> MC
C --> AK
PR --> C
PR --> T
PR --> PM
PR --> H
T --> SM
T --> ST
P --> PR
LOG --> C
LOG --> PR
LOG --> T
```

**Diagram sources**
- [client.py](file://src/llm/client.py#L1-L211)
- [tools.py](file://src/llm/tools.py#L1-L1066)
- [prompts.py](file://src/llm/prompts.py#L1-L87)
- [processor.py](file://src/conversation/processor.py#L1-L456)
- [phase_manager.py](file://src/conversation/phase_manager.py#L1-L92)
- [helpers.py](file://src/utils/helpers.py#L1-L265)
- [state_manager.py](file://src/utils/state_manager.py#L1-L814)
- [stripe_mcp.py](file://src/payments/stripe_mcp.py#L1-L475)
- [model_config.py](file://src/config/model_config.py#L1-L102)
- [api_keys.py](file://src/config/api_keys.py#L1-L51)
- [logging_config.py](file://src/config/logging_config.py#L1-L51)

**Section sources**
- [client.py](file://src/llm/client.py#L1-L211)
- [tools.py](file://src/llm/tools.py#L1-L1066)
- [prompts.py](file://src/llm/prompts.py#L1-L87)
- [processor.py](file://src/conversation/processor.py#L1-L456)
- [phase_manager.py](file://src/conversation/phase_manager.py#L1-L92)
- [helpers.py](file://src/utils/helpers.py#L1-L265)
- [state_manager.py](file://src/utils/state_manager.py#L1-L814)
- [stripe_mcp.py](file://src/payments/stripe_mcp.py#L1-L475)
- [model_config.py](file://src/config/model_config.py#L1-L102)
- [api_keys.py](file://src/config/api_keys.py#L1-L51)
- [logging_config.py](file://src/config/logging_config.py#L1-L51)

## Core Components
- Google Gemini client abstraction: Initializes the LLM, binds tools, and wraps API calls with retry logic and error classification
- Tool registry pattern: Centralized tool definitions with typed responses and error codes, exposing payment, order, and menu functions
- Prompt engineering: System instructions and phase prompts guiding the LLM’s behavior and context injection
- Conversation processor: Orchestrates LLM/tool interactions, manages session context, and updates state
- State management: Thread-safe, validated state with atomic operations for concurrent safety
- Payment integration: Stripe MCP client with availability probing, retries, and fallback to simulated payments

**Section sources**
- [client.py](file://src/llm/client.py#L91-L129)
- [tools.py](file://src/llm/tools.py#L221-L800)
- [prompts.py](file://src/llm/prompts.py#L6-L87)
- [processor.py](file://src/conversation/processor.py#L83-L456)
- [state_manager.py](file://src/utils/state_manager.py#L17-L167)
- [stripe_mcp.py](file://src/payments/stripe_mcp.py#L66-L475)

## Architecture Overview
The system follows a layered architecture:
- Configuration layer: Model and API key management
- LLM client layer: Abstraction over Google Gemini with tool binding and retry logic
- Tools layer: Registry of functions callable by the LLM with validation and error handling
- Conversation layer: Orchestrates LLM/tool interactions, maintains conversation state, and applies phase-based prompting
- Utilities layer: State management, logging, and helper functions
- Payments layer: Stripe MCP client with robust retry and fallback strategies

```mermaid
sequenceDiagram
participant User as "User"
participant Processor as "ConversationProcessor"
participant LLM as "ChatGoogleGenerativeAI"
participant Tools as "Tool Registry"
participant State as "StateManager"
participant Stripe as "StripeMCPClient"
User->>Processor : "User input"
Processor->>Processor : "Detect intent/speech acts"
Processor->>LLM : "Invoke with system + history + menu"
LLM-->>Processor : "AIMessage (text or tool_calls)"
alt Tool calls present
Processor->>Tools : "Execute tool(s) with validated args"
Tools->>State : "Atomic state updates"
Tools->>Stripe : "Async payment operations (when applicable)"
Stripe-->>Tools : "Payment result or fallback"
Tools-->>Processor : "Tool response"
Processor->>LLM : "Send ToolMessage results"
LLM-->>Processor : "Final response"
else No tool calls
LLM-->>Processor : "Final response"
end
Processor->>State : "Update conversation and order state"
Processor-->>User : "Agent response + emotion tag"
```

**Diagram sources**
- [processor.py](file://src/conversation/processor.py#L275-L406)
- [client.py](file://src/llm/client.py#L130-L211)
- [tools.py](file://src/llm/tools.py#L221-L800)
- [state_manager.py](file://src/utils/state_manager.py#L685-L757)
- [stripe_mcp.py](file://src/payments/stripe_mcp.py#L183-L346)

## Detailed Component Analysis

### Google Gemini Client Configuration and API Abstraction
The client module encapsulates Google Gemini initialization, model parameter mapping, and API call abstraction with retry logic and error classification.

Key responsibilities:
- Configure the Google Generative AI SDK with an API key
- Build generation configuration from shared model parameters
- Initialize the LangChain ChatGoogleGenerativeAI instance and bind tools
- Wrap API calls with retry logic and classify errors (rate limit, auth, timeout)
- Provide a unified function to call the Gemini API with structured error handling

```mermaid
flowchart TD
Start(["Initialize LLM"]) --> Params["Load model params"]
Params --> BuildCfg["Build generation config"]
BuildCfg --> InitLLM["Initialize ChatGoogleGenerativeAI"]
InitLLM --> BindTools{"Tools provided?"}
BindTools --> |Yes| Bind["Bind tools to LLM"]
BindTools --> |No| SkipBind["Proceed without tools"]
Bind --> End(["Ready"])
SkipBind --> End
```

**Diagram sources**
- [client.py](file://src/llm/client.py#L91-L129)

**Section sources**
- [client.py](file://src/llm/client.py#L47-L129)
- [model_config.py](file://src/config/model_config.py#L31-L59)
- [api_keys.py](file://src/config/api_keys.py#L10-L51)

### Tool Registry Pattern and Function Calling Mechanism
The tools module defines a registry of functions callable by the LLM. Each tool:
- Is decorated as a LangChain tool
- Validates arguments and returns a standardized response structure
- Uses thread-local session context and a global store for state access
- Implements atomic operations for payment state updates
- Integrates with the Stripe MCP client for asynchronous payment processing

```mermaid
classDiagram
class ToolResponse {
+status : "ok"|"error"
+result : dict
}
class PaymentError {
<<enumeration>>
INSUFFICIENT_FUNDS
STRIPE_UNAVAILABLE
PAYMENT_FAILED
CONCURRENT_MODIFICATION
NETWORK_ERROR
RATE_LIMITED
INVALID_SESSION
ITEM_NOT_FOUND
PAYMENT_TIMEOUT
INVALID_TIP_PERCENTAGE
}
class StripeMCPClient {
+generate_idempotency_key(session_id) str
+create_payment_link(amount, description, idempotency_key) Dict
+check_payment_status(payment_id) str
+is_available() bool
}
class StateManager {
+atomic_order_update(...)
+atomic_payment_complete(...)
+get_payment_state(...)
+update_payment_state(...)
}
ToolResponse --> PaymentError : "uses"
StripeMCPClient --> StateManager : "reads/writes"
```

**Diagram sources**
- [tools.py](file://src/llm/tools.py#L36-L167)
- [stripe_mcp.py](file://src/payments/stripe_mcp.py#L66-L475)
- [state_manager.py](file://src/utils/state_manager.py#L685-L800)

**Section sources**
- [tools.py](file://src/llm/tools.py#L221-L800)
- [state_manager.py](file://src/utils/state_manager.py#L685-L800)
- [stripe_mcp.py](file://src/payments/stripe_mcp.py#L183-L441)

### Prompt Engineering Strategy: Phase-Based Prompting and Context Injection
The prompts module defines:
- System instructions emphasizing tool usage for orders and tips
- Phase-specific prompts for greeting, order-taking, small talk, and reorder prompts
- Combined prompt composition that injects the menu and current phase context

```mermaid
flowchart TD
Start(["Compose Prompt"]) --> GetPhase["Get current phase"]
GetPhase --> GetMenu["Get menu text"]
GetMenu --> Compose["Combine phase + system + menu"]
Compose --> Inject["Inject into LLM messages"]
Inject --> End(["Ready"])
```

**Diagram sources**
- [prompts.py](file://src/llm/prompts.py#L44-L87)

**Section sources**
- [prompts.py](file://src/llm/prompts.py#L6-L87)
- [processor.py](file://src/conversation/processor.py#L244-L271)

### Conversation Orchestration and Bidirectional Communication
The conversation processor:
- Detects intents and speech acts to decide between direct tool invocation and LLM-driven responses
- Manages session context for tools and updates conversation state
- Executes tool calls, handles malformed arguments, and sends ToolMessage results back to the LLM
- Applies RAG enhancements for casual conversation when available

```mermaid
sequenceDiagram
participant Proc as "Processor"
participant LLM as "LLM"
participant Tools as "Tools"
participant State as "State"
Proc->>LLM : "Messages (system + history + menu)"
LLM-->>Proc : "AIMessage (text or tool_calls)"
alt Tool calls
Proc->>Tools : "Invoke tool with args"
Tools->>State : "Atomic state update"
Tools-->>Proc : "Tool response"
Proc->>LLM : "ToolMessage"
LLM-->>Proc : "Final response"
else No tool calls
LLM-->>Proc : "Final response"
end
Proc->>State : "Update conversation state"
```

**Diagram sources**
- [processor.py](file://src/conversation/processor.py#L275-L406)
- [helpers.py](file://src/utils/helpers.py#L9-L70)

**Section sources**
- [processor.py](file://src/conversation/processor.py#L83-L456)
- [helpers.py](file://src/utils/helpers.py#L113-L210)
- [phase_manager.py](file://src/conversation/phase_manager.py#L42-L67)

### Payment Integration Patterns: Synchronous Operations, Asynchronous Payment Processing, and State-Managed Functions
- Synchronous operations: Balance checks and order additions use atomic state updates with optimistic locking
- Asynchronous payment processing: Stripe MCP client uses async retries and fallback to simulated payments
- State-managed functions: Payment state transitions are validated and persisted atomically

```mermaid
flowchart TD
Start(["Payment Request"]) --> CheckAvail["Check Stripe availability"]
CheckAvail --> |Available| CreateLink["Create payment link (async)"]
CheckAvail --> |Unavailable| Fallback["Create mock payment"]
CreateLink --> Poll["Poll status (async)"]
Poll --> Success{"Succeeded?"}
Success --> |Yes| AtomicComplete["Atomic payment completion"]
Success --> |No| Timeout{"Timeout?"}
Timeout --> |Yes| Error["Return timeout error"]
Timeout --> |No| Retry["Retry with backoff"]
Retry --> Poll
AtomicComplete --> End(["Payment complete"])
Fallback --> End
```

**Diagram sources**
- [stripe_mcp.py](file://src/payments/stripe_mcp.py#L183-L441)
- [state_manager.py](file://src/utils/state_manager.py#L780-L800)

**Section sources**
- [stripe_mcp.py](file://src/payments/stripe_mcp.py#L319-L346)
- [state_manager.py](file://src/utils/state_manager.py#L780-L800)

## Dependency Analysis
The LLM integration exhibits clear separation of concerns:
- LLM client depends on model configuration and API keys
- Tools depend on state management and payment clients
- Processor orchestrates LLM, tools, and state updates
- Helpers provide intent detection and speech act analysis
- Logging is centralized for consistent diagnostics

```mermaid
graph LR
MC["model_config.py"] --> C["client.py"]
AK["api_keys.py"] --> C
C --> PR["processor.py"]
PR --> T["tools.py"]
T --> SM["state_manager.py"]
T --> ST["stripe_mcp.py"]
PR --> PM["phase_manager.py"]
PR --> H["helpers.py"]
LOG["logging_config.py"] --> C
LOG --> PR
LOG --> T
```

**Diagram sources**
- [client.py](file://src/llm/client.py#L1-L211)
- [tools.py](file://src/llm/tools.py#L1-L1066)
- [processor.py](file://src/conversation/processor.py#L1-L456)
- [state_manager.py](file://src/utils/state_manager.py#L1-L814)
- [stripe_mcp.py](file://src/payments/stripe_mcp.py#L1-L475)
- [model_config.py](file://src/config/model_config.py#L1-L102)
- [api_keys.py](file://src/config/api_keys.py#L1-L51)
- [logging_config.py](file://src/config/logging_config.py#L1-L51)

**Section sources**
- [client.py](file://src/llm/client.py#L1-L211)
- [tools.py](file://src/llm/tools.py#L1-L1066)
- [processor.py](file://src/conversation/processor.py#L1-L456)
- [state_manager.py](file://src/utils/state_manager.py#L1-L814)
- [stripe_mcp.py](file://src/payments/stripe_mcp.py#L1-L475)
- [model_config.py](file://src/config/model_config.py#L1-L102)
- [api_keys.py](file://src/config/api_keys.py#L1-L51)
- [logging_config.py](file://src/config/logging_config.py#L1-L51)

## Performance Considerations
- Retry and backoff: The Gemini client uses exponential backoff for transient failures, reducing load on external services
- Async payment operations: Stripe MCP client uses non-blocking async retries and polling to avoid blocking request threads
- Caching availability: Stripe MCP client caches availability results to reduce probe overhead
- Optimistic locking: Atomic state updates minimize contention and avoid repeated reads
- RAG gating: The processor validates RAG components before invoking expensive pipelines

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
Common issues and resolutions:
- Authentication/authorization errors: Verify API keys and permissions; the client logs detailed error information
- Rate limiting: The client retries with exponential backoff; consider lowering request frequency or upgrading quotas
- Timeouts: Increase timeouts or reduce payload sizes; the client classifies timeouts and logs warnings
- Tool argument validation: Tools validate inputs and return structured errors; ensure arguments match expected types
- Payment failures: Stripe MCP falls back to simulated payments; monitor logs for detailed failure reasons
- State inconsistencies: Atomic operations and optimistic locking prevent concurrent modifications; check version mismatches

**Section sources**
- [client.py](file://src/llm/client.py#L170-L208)
- [stripe_mcp.py](file://src/payments/stripe_mcp.py#L217-L272)
- [state_manager.py](file://src/utils/state_manager.py#L685-L757)
- [tools.py](file://src/llm/tools.py#L139-L167)

## Conclusion
MayaMCP’s LLM integration provides a robust, modular architecture for conversational bartending assistance. The Google Gemini client abstraction simplifies external API interactions and model parameter management. The tool registry pattern cleanly exposes payment, order, and menu functions with strong validation and error handling. Phase-based prompting and context injection guide the LLM toward actionable tool calls. The conversation processor orchestrates bidirectional communication between LLM responses and tool execution, updating state atomically. Payment integration includes asynchronous processing with retries and fallbacks. Together, these components deliver a reliable, extensible system for AI-assisted bar operations.