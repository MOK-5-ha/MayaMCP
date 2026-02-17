# Core Architecture

<cite>
**Referenced Files in This Document**
- [src/__init__.py](file://src/__init__.py)
- [src/conversation/processor.py](file://src/conversation/processor.py)
- [src/conversation/phase_manager.py](file://src/conversation/phase_manager.py)
- [src/ui/launcher.py](file://src/ui/launcher.py)
- [src/ui/handlers.py](file://src/ui/handlers.py)
- [src/llm/client.py](file://src/llm/client.py)
- [src/llm/tools.py](file://src/llm/tools.py)
- [src/rag/pipeline.py](file://src/rag/pipeline.py)
- [src/security/scanner.py](file://src/security/scanner.py)
- [src/payments/stripe_mcp.py](file://src/payments/stripe_mcp.py)
- [src/voice/tts.py](file://src/voice/tts.py)
- [src/utils/state_manager.py](file://src/utils/state_manager.py)
- [src/utils/helpers.py](file://src/utils/helpers.py)
- [src/config/model_config.py](file://src/config/model_config.py)
- [src/config/logging_config.py](file://src/config/logging_config.py)
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
This document describes the core system design of MayaMCP, a layered conversational AI bartender application. The architecture centers on a UI layer that captures user inputs, a conversation processing layer orchestrating LLM integration and tool execution, and a state management layer that maintains conversation context, payment state, and user session data. The system adopts the Model Context Protocol (MCP) for external integrations, supports dual RAG backends (video-based Memvid and FAISS), and integrates real-time audio synthesis via Cartesia. Cross-cutting concerns include robust error handling, graceful fallbacks, and observability.

## Project Structure
MayaNCP follows a feature-based, layered organization:
- UI Layer: Gradio-based launcher and handlers manage user events, state, and audio playback.
- Conversation Layer: Orchestrates LLM interactions, tool execution, and RAG augmentation.
- LLM Integration: Gemini client and tool registry enable function-calling conversations.
- RAG Layer: Dual pipelines for Memvid and FAISS-backed retrieval-augmented generation.
- Security: Input/output scanning with configurable policies.
- Payments: Stripe MCP client with retry, fallback, and idempotency.
- Voice: Text-to-speech with Cartesia and retry logic.
- Utilities: State management, helpers, and configuration.

```mermaid
graph TB
subgraph "UI Layer"
UI_Launcher["UI Launcher<br/>src/ui/launcher.py"]
UI_Handlers["UI Handlers<br/>src/ui/handlers.py"]
end
subgraph "Conversation Layer"
Conv_Processor["Conversation Processor<br/>src/conversation/processor.py"]
Phase_Manager["Phase Manager<br/>src/conversation/phase_manager.py"]
end
subgraph "LLM Integration"
LLM_Client["Gemini Client<br/>src/llm/client.py"]
LLM_Tools["Tools Registry<br/>src/llm/tools.py"]
end
subgraph "RAG Layer"
RAG_Pipeline["FAISS RAG Pipeline<br/>src/rag/pipeline.py"]
end
subgraph "Security"
Security_Scanner["Security Scanner<br/>src/security/scanner.py"]
end
subgraph "Payments"
Stripe_MCP["Stripe MCP Client<br/>src/payments/stripe_mcp.py"]
end
subgraph "Voice"
TTS["TTS Client<br/>src/voice/tts.py"]
end
subgraph "Utilities"
State_Manager["State Manager<br/>src/utils/state_manager.py"]
Helpers["Helpers<br/>src/utils/helpers.py"]
Model_Config["Model Config<br/>src/config/model_config.py"]
Logging_Config["Logging Config<br/>src/config/logging_config.py"]
end
UI_Launcher --> UI_Handlers
UI_Handlers --> Conv_Processor
Conv_Processor --> LLM_Client
Conv_Processor --> LLM_Tools
Conv_Processor --> RAG_Pipeline
Conv_Processor --> Security_Scanner
Conv_Processor --> State_Manager
LLM_Tools --> Stripe_MCP
UI_Handlers --> TTS
UI_Handlers --> State_Manager
Phase_Manager --> State_Manager
Model_Config --> LLM_Client
Model_Config --> TTS
Logging_Config --> LLM_Client
Logging_Config --> Conv_Processor
```

**Diagram sources**
- [src/ui/launcher.py](file://src/ui/launcher.py#L49-L354)
- [src/ui/handlers.py](file://src/ui/handlers.py#L23-L392)
- [src/conversation/processor.py](file://src/conversation/processor.py#L1-L456)
- [src/conversation/phase_manager.py](file://src/conversation/phase_manager.py#L1-L92)
- [src/llm/client.py](file://src/llm/client.py#L1-L211)
- [src/llm/tools.py](file://src/llm/tools.py#L1-L1066)
- [src/rag/pipeline.py](file://src/rag/pipeline.py#L1-L105)
- [src/security/scanner.py](file://src/security/scanner.py#L1-L137)
- [src/payments/stripe_mcp.py](file://src/payments/stripe_mcp.py#L1-L475)
- [src/voice/tts.py](file://src/voice/tts.py#L1-L200)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L1-L814)
- [src/utils/helpers.py](file://src/utils/helpers.py#L1-L265)
- [src/config/model_config.py](file://src/config/model_config.py#L1-L102)
- [src/config/logging_config.py](file://src/config/logging_config.py#L1-L51)

**Section sources**
- [src/__init__.py](file://src/__init__.py#L1-L9)
- [src/ui/launcher.py](file://src/ui/launcher.py#L49-L354)
- [src/ui/handlers.py](file://src/ui/handlers.py#L23-L392)
- [src/conversation/processor.py](file://src/conversation/processor.py#L1-L456)
- [src/conversation/phase_manager.py](file://src/conversation/phase_manager.py#L1-L92)
- [src/llm/client.py](file://src/llm/client.py#L1-L211)
- [src/llm/tools.py](file://src/llm/tools.py#L1-L1066)
- [src/rag/pipeline.py](file://src/rag/pipeline.py#L1-L105)
- [src/security/scanner.py](file://src/security/scanner.py#L1-L137)
- [src/payments/stripe_mcp.py](file://src/payments/stripe_mcp.py#L1-L475)
- [src/voice/tts.py](file://src/voice/tts.py#L1-L200)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L1-L814)
- [src/utils/helpers.py](file://src/utils/helpers.py#L1-L265)
- [src/config/model_config.py](file://src/config/model_config.py#L1-L102)
- [src/config/logging_config.py](file://src/config/logging_config.py#L1-L51)

## Core Components
- UI Layer: Provides the Gradio interface, manages session state, and routes user inputs to the conversation processor. It also handles tip interactions and renders avatar overlays reflecting payment state and emotion.
- Conversation Processor: Central orchestration engine that performs security scanning, intent detection, LLM/tool interaction loops, optional RAG augmentation, and state updates.
- LLM Integration: Initializes the Gemini model via LangChain, binds tools, and executes function calls with retries and error classification.
- Tools: A registry of payment and menu-related tools enabling atomic order updates, balance checks, tip management, and Stripe payment link creation/status polling.
- RAG Layer: Dual pipelines for retrieval-augmented generation using FAISS and Memvid backends, with graceful fallbacks and validation.
- Security: Input and output scanning with configurable thresholds and fail-open behavior.
- Payments: Stripe MCP client with availability probing, retry/backoff, idempotency, and mock fallback.
- Voice: Text-to-speech using Cartesia with retry logic, text cleaning, and pronunciation normalization.
- State Management: Thread-safe, session-scoped state with typed payment state, optimistic locking, and validation.
- Utilities: Helpers for speech act detection, phase transitions, and casual conversation detection.

**Section sources**
- [src/ui/launcher.py](file://src/ui/launcher.py#L49-L354)
- [src/ui/handlers.py](file://src/ui/handlers.py#L23-L392)
- [src/conversation/processor.py](file://src/conversation/processor.py#L1-L456)
- [src/llm/client.py](file://src/llm/client.py#L1-L211)
- [src/llm/tools.py](file://src/llm/tools.py#L1-L1066)
- [src/rag/pipeline.py](file://src/rag/pipeline.py#L1-L105)
- [src/security/scanner.py](file://src/security/scanner.py#L1-L137)
- [src/payments/stripe_mcp.py](file://src/payments/stripe_mcp.py#L1-L475)
- [src/voice/tts.py](file://src/voice/tts.py#L1-L200)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L1-L814)
- [src/utils/helpers.py](file://src/utils/helpers.py#L1-L265)

## Architecture Overview
MayaMCP employs a layered architecture:
- Presentation Layer: Gradio UI with stateful components and audio rendering.
- Application Layer: Conversation processor and handlers coordinate user events, LLM/tool execution, and RAG.
- Integration Layer: Gemini LLM, Stripe MCP, and Cartesia services.
- Persistence/State Layer: In-memory or distributed session store with typed validation and concurrency controls.

```mermaid
graph TB
Client["User"]
UI["UI Layer<br/>Gradio"]
Handler["Handlers<br/>process_order()"]
LLM["LLM Client<br/>Gemini"]
Tools["Tools Registry<br/>add_to_order, pay_bill, set_tip, get_menu"]
RAG["RAG Pipeline<br/>FAISS/Memvid"]
Sec["Security Scanner"]
Pay["Stripe MCP Client"]
TTS["Cartesia TTS"]
State["State Manager"]
Client --> UI
UI --> Handler
Handler --> LLM
Handler --> Tools
Handler --> RAG
Handler --> Sec
Tools --> Pay
Handler --> State
UI --> TTS
UI --> State
```

**Diagram sources**
- [src/ui/handlers.py](file://src/ui/handlers.py#L23-L392)
- [src/conversation/processor.py](file://src/conversation/processor.py#L1-L456)
- [src/llm/client.py](file://src/llm/client.py#L1-L211)
- [src/llm/tools.py](file://src/llm/tools.py#L1-L1066)
- [src/rag/pipeline.py](file://src/rag/pipeline.py#L1-L105)
- [src/security/scanner.py](file://src/security/scanner.py#L1-L137)
- [src/payments/stripe_mcp.py](file://src/payments/stripe_mcp.py#L1-L475)
- [src/voice/tts.py](file://src/voice/tts.py#L1-L200)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L1-L814)

## Detailed Component Analysis

### UI Layer: Gradio Launcher and Handlers
- The launcher creates the Gradio Blocks layout, defines session state variables, and wires event handlers for input submission, clearing state, and tip button interactions.
- The handlers implement the event-driven flow: parse session ID from the request, invoke the conversation processor, optionally generate voice audio via Cartesia, resolve avatar emotion states, and update the overlay with animated payment state.

```mermaid
sequenceDiagram
participant U as "User"
participant G as "Gradio UI"
participant H as "UI Handlers"
participant P as "Conversation Processor"
participant L as "LLM Client"
participant T as "Tools"
participant R as "RAG"
participant S as "Security Scanner"
participant V as "Cartesia TTS"
U->>G : "Submit message / Click tip"
G->>H : "Event callback with session state"
H->>P : "process_order(user_input, session_id, app_state)"
P->>S : "scan_input()"
alt blocked
S-->>H : "blocked_reason"
H-->>G : "display blocked message"
else allowed
P->>L : "invoke(messages)"
L-->>P : "AIMessage with tool_calls or text"
alt tool_calls
P->>T : "invoke(tool)"
T-->>P : "tool_result"
P->>L : "send ToolMessage"
L-->>P : "final response"
end
opt casual conversation
P->>R : "enhance with RAG"
R-->>P : "augmented response"
end
P->>S : "scan_output()"
S-->>H : "sanitized text"
H->>V : "get_voice_audio()"
V-->>H : "WAV bytes"
H-->>G : "update chat, overlay, audio"
end
```

**Diagram sources**
- [src/ui/launcher.py](file://src/ui/launcher.py#L49-L354)
- [src/ui/handlers.py](file://src/ui/handlers.py#L23-L392)
- [src/conversation/processor.py](file://src/conversation/processor.py#L1-L456)
- [src/llm/client.py](file://src/llm/client.py#L1-L211)
- [src/llm/tools.py](file://src/llm/tools.py#L1-L1066)
- [src/rag/pipeline.py](file://src/rag/pipeline.py#L1-L105)
- [src/security/scanner.py](file://src/security/scanner.py#L1-L137)
- [src/voice/tts.py](file://src/voice/tts.py#L1-L200)

**Section sources**
- [src/ui/launcher.py](file://src/ui/launcher.py#L49-L354)
- [src/ui/handlers.py](file://src/ui/handlers.py#L23-L392)

### Conversation Processing: Orchestrator of LLM and Tools
- Security scanning wraps both input and output, with fail-open behavior and configurable thresholds.
- Intent detection leverages speech act analysis and keyword-based detection to route to tools or general LLM responses.
- The LLM/tool loop executes until a final text response is produced; tool results are appended back to the message history.
- Optional RAG augmentation is applied for casual conversation using either Memvid or FAISS pipelines, with defensive checks and fallbacks.
- State updates track conversation phase, turn counts, and order completion, updating the phase manager accordingly.

```mermaid
flowchart TD
Start(["process_order entry"]) --> SecurityIn["scan_input()"]
SecurityIn --> InBlocked{"Input blocked?"}
InBlocked --> |Yes| BlockResp["Return blocked message"] --> End
InBlocked --> |No| InitSession["set_current_session()"]
InitSession --> FirstInteraction{"First interaction?"}
FirstInteraction --> |Yes| InitState["initialize_state()"] --> DetectIntent
FirstInteraction --> |No| DetectIntent["detect_speech_acts()<br/>detect_order_inquiry()"]
DetectIntent --> SpeechAct{"Speech act order confirmation?"}
SpeechAct --> |Yes| ExecContextual["add_to_order tool<br/>update phase"] --> SecurityOut1["scan_output()"]
SpeechAct --> |No| Intent{"Intent detected?"}
Intent --> |Yes| ExecIntent["invoke tool (get_order/get_bill/pay_bill)"] --> SecurityOut2["scan_output()"]
Intent --> |No| BuildMsg["Build LangChain messages<br/>System + History + User"]
BuildMsg --> LLMInvoke["llm.invoke(messages)"]
LLMInvoke --> HasToolCalls{"tool_calls?"}
HasToolCalls --> |Yes| ExecTools["invoke tools<br/>append ToolMessage"] --> LLMInvoke
HasToolCalls --> |No| FinalResp["agent_response_text"]
FinalResp --> Casual{"Should use RAG?"}
Casual --> |Yes| Enhance["Memvid or FAISS RAG<br/>fallback on error"] --> SecurityOut3["scan_output()"]
Casual --> |No| SecurityOut3
SecurityOut3 --> UpdateState["update phase, turn, order state"]
UpdateState --> End(["return response, history, order, audio, emotion"])
```

**Diagram sources**
- [src/conversation/processor.py](file://src/conversation/processor.py#L1-L456)
- [src/security/scanner.py](file://src/security/scanner.py#L1-L137)
- [src/utils/helpers.py](file://src/utils/helpers.py#L1-L265)
- [src/conversation/phase_manager.py](file://src/conversation/phase_manager.py#L1-L92)

**Section sources**
- [src/conversation/processor.py](file://src/conversation/processor.py#L1-L456)
- [src/utils/helpers.py](file://src/utils/helpers.py#L1-L265)
- [src/conversation/phase_manager.py](file://src/conversation/phase_manager.py#L1-L92)

### LLM Integration: Gemini Client and Tool Binding
- The Gemini client initializes the LangChain ChatGoogleGenerativeAI with model parameters from configuration, binds tools, and exposes a retry-wrapped API call.
- Tool binding enables the LLM to request tool invocations, which are executed synchronously within the processor’s loop.

```mermaid
classDiagram
class GeminiClient {
+initialize_llm(api_key, tools)
+call_gemini_api(prompt, config, api_key)
+get_model_name()
+get_langchain_llm_params()
}
class ToolsRegistry {
+get_all_tools()
+set_current_session(session_id)
+clear_current_session()
+add_to_order(...)
+pay_bill(...)
+get_menu()
+set_tip(...)
}
GeminiClient --> ToolsRegistry : "bind_tools()"
```

**Diagram sources**
- [src/llm/client.py](file://src/llm/client.py#L1-L211)
- [src/llm/tools.py](file://src/llm/tools.py#L1-L1066)

**Section sources**
- [src/llm/client.py](file://src/llm/client.py#L1-L211)
- [src/llm/tools.py](file://src/llm/tools.py#L1-L1066)

### RAG Layer: Dual Backends with Fallbacks
- The FAISS pipeline retrieves relevant passages and generates an augmented response using a configured Gemini model, with error classification and fallback messaging.
- The processor conditionally invokes Memvid or FAISS based on availability and configuration, with defensive checks and graceful degradation.

```mermaid
flowchart TD
Q["Query"] --> Choose{"RAG available?"}
Choose --> |Memvid| Memvid["memvid_rag_pipeline(query, retriever, api_key)"]
Choose --> |FAISS| FAISS["rag_pipeline(query, index, docs, api_key)"]
Memvid --> Merge["Use RAG response if non-empty"]
FAISS --> Merge
Merge --> Done["Return enhanced or original response"]
```

**Diagram sources**
- [src/conversation/processor.py](file://src/conversation/processor.py#L302-L362)
- [src/rag/pipeline.py](file://src/rag/pipeline.py#L1-L105)

**Section sources**
- [src/conversation/processor.py](file://src/conversation/processor.py#L302-L362)
- [src/rag/pipeline.py](file://src/rag/pipeline.py#L1-L105)

### Security Scanning: Input and Output
- Input scanning detects prompt injection and toxicity; output scanning filters toxic content and returns a safe fallback.
- The scanner is optional and falls back gracefully when dependencies are unavailable.

```mermaid
flowchart TD
In["User Input"] --> CheckAvail["is_available()?"]
CheckAvail --> |No| Pass["Return (is_valid=True)"]
CheckAvail --> |Yes| PI["PromptInjection scan"]
PI --> PIAllowed{"allowed?"}
PIAllowed --> |No| Block["Return blocked_reason"]
PIAllowed --> |Yes| Tox["Toxicity scan"]
Tox --> ToxA{"allowed?"}
ToxA --> |No| Block2["Return blocked_reason"]
ToxA --> |Yes| Out["Return sanitized_text"]
```

**Diagram sources**
- [src/security/scanner.py](file://src/security/scanner.py#L1-L137)

**Section sources**
- [src/security/scanner.py](file://src/security/scanner.py#L1-L137)

### Payments: Stripe MCP Client with Idempotency and Fallback
- The Stripe MCP client provides idempotent payment link creation, availability probing, and status polling with timeouts and retries.
- Fallback to mock payment is supported when the MCP server is unavailable, ensuring continuity of the user experience.

```mermaid
sequenceDiagram
participant C as "Tools"
participant SM as "StripeMCPClient"
participant MCP as "Stripe MCP Server"
C->>SM : "create_payment_link(amount, desc, idempotency_key)"
alt available
SM->>MCP : "_call_stripe_create_link(...)"
MCP-->>SM : "url, payment_id"
else unavailable
SM-->>C : "_create_mock_payment(...)"
end
C->>SM : "check_payment_status(payment_id)"
SM-->>C : "pending/succeeded/failed/timeout"
```

**Diagram sources**
- [src/llm/tools.py](file://src/llm/tools.py#L358-L472)
- [src/payments/stripe_mcp.py](file://src/payments/stripe_mcp.py#L183-L441)

**Section sources**
- [src/llm/tools.py](file://src/llm/tools.py#L358-L472)
- [src/payments/stripe_mcp.py](file://src/payments/stripe_mcp.py#L1-L475)

### Voice: Text-to-Speech with Retry and Cleaning
- The TTS client cleans text for pronunciation, initializes Cartesia, and synthesizes WAV audio with retry logic for transient failures.

```mermaid
flowchart TD
T0["Text"] --> Clean["clean_text_for_tts()"]
Clean --> Init["initialize_cartesia_client()"]
Init --> Synth["cartesia_client.tts.bytes(...)"]
Synth --> Bytes["WAV bytes"]
```

**Diagram sources**
- [src/voice/tts.py](file://src/voice/tts.py#L1-L200)

**Section sources**
- [src/voice/tts.py](file://src/voice/tts.py#L1-L200)

### State Management: Typed, Thread-Safe Sessions
- The state manager defines a typed payment state schema, enforces validation, and provides atomic operations with optimistic locking and versioning.
- Session locks prevent concurrent modifications, and background cleanup removes stale locks.

```mermaid
classDiagram
class PaymentState {
+float balance
+float tab_total
+Optional<int> tip_percentage
+float tip_amount
+Optional<string> stripe_payment_id
+enum payment_status
+int version
+bool needs_reconciliation
}
class StateManager {
+initialize_state()
+get_payment_state()
+update_payment_state()
+atomic_order_update()
+atomic_payment_complete()
+set_tip()
+get_session_lock()
+cleanup_session_lock()
}
StateManager --> PaymentState : "validates & updates"
```

**Diagram sources**
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L17-L814)

**Section sources**
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L1-L814)

### Helpers: Speech Acts and Phase Transitions
- Helpers detect speech acts (Austin’s framework), extract drink context, and determine whether input is casual conversation, guiding RAG usage and tool routing.

```mermaid
flowchart TD
U["User Input"] --> SA["detect_speech_acts()"]
SA --> IA["is_casual_conversation()"]
IA --> |Yes| UseRAG["should_use_rag = True"]
IA --> |No| UseRAG --> |No| Tools["invoke tools"]
```

**Diagram sources**
- [src/utils/helpers.py](file://src/utils/helpers.py#L113-L265)
- [src/conversation/phase_manager.py](file://src/conversation/phase_manager.py#L69-L82)

**Section sources**
- [src/utils/helpers.py](file://src/utils/helpers.py#L1-L265)
- [src/conversation/phase_manager.py](file://src/conversation/phase_manager.py#L1-L92)

## Dependency Analysis
Key dependencies and coupling:
- UI handlers depend on the conversation processor and state manager; they optionally depend on TTS and security scanning.
- The conversation processor depends on LLM client, tools, RAG pipelines, security scanner, and state manager.
- Tools depend on state manager and Stripe MCP client.
- Configuration modules supply model and TTS parameters to clients.

```mermaid
graph LR
UI["UI Handlers"] --> Proc["Conversation Processor"]
Proc --> LLM["LLM Client"]
Proc --> Tools["Tools"]
Proc --> RAG["RAG Pipeline"]
Proc --> Sec["Security Scanner"]
Tools --> Stripe["Stripe MCP Client"]
UI --> TTS["TTS"]
Proc --> State["State Manager"]
LLM --> ModelCfg["Model Config"]
TTS --> ModelCfg
Logging["Logging Config"] --> LLM
Logging --> Proc
```

**Diagram sources**
- [src/ui/handlers.py](file://src/ui/handlers.py#L23-L392)
- [src/conversation/processor.py](file://src/conversation/processor.py#L1-L456)
- [src/llm/client.py](file://src/llm/client.py#L1-L211)
- [src/llm/tools.py](file://src/llm/tools.py#L1-L1066)
- [src/rag/pipeline.py](file://src/rag/pipeline.py#L1-L105)
- [src/security/scanner.py](file://src/security/scanner.py#L1-L137)
- [src/payments/stripe_mcp.py](file://src/payments/stripe_mcp.py#L1-L475)
- [src/voice/tts.py](file://src/voice/tts.py#L1-L200)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L1-L814)
- [src/config/model_config.py](file://src/config/model_config.py#L1-L102)
- [src/config/logging_config.py](file://src/config/logging_config.py#L1-L51)

**Section sources**
- [src/ui/handlers.py](file://src/ui/handlers.py#L23-L392)
- [src/conversation/processor.py](file://src/conversation/processor.py#L1-L456)
- [src/llm/client.py](file://src/llm/client.py#L1-L211)
- [src/llm/tools.py](file://src/llm/tools.py#L1-L1066)
- [src/rag/pipeline.py](file://src/rag/pipeline.py#L1-L105)
- [src/security/scanner.py](file://src/security/scanner.py#L1-L137)
- [src/payments/stripe_mcp.py](file://src/payments/stripe_mcp.py#L1-L475)
- [src/voice/tts.py](file://src/voice/tts.py#L1-L200)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L1-L814)
- [src/config/model_config.py](file://src/config/model_config.py#L1-L102)
- [src/config/logging_config.py](file://src/config/logging_config.py#L1-L51)

## Performance Considerations
- LLM retries: The Gemini client uses exponential backoff to mitigate transient failures.
- TTS retries: Cartesia calls are retried on retryable exceptions to improve reliability.
- RAG gating: The processor validates RAG availability and gracefully falls back if components are missing or fail.
- Concurrency: Session locks and optimistic locking minimize contention and race conditions in state updates.
- Observability: Logging is centralized and configurable, aiding performance diagnostics.

[No sources needed since this section provides general guidance]

## Troubleshooting Guide
- LLM Invocation Failures: The processor catches invocation errors and returns a friendly fallback response. Check logging for detailed error context.
- Tool Execution Errors: Malformed arguments or runtime errors are caught and reported; ensure tool signatures match expectations.
- RAG Failures: If RAG components are misconfigured or unavailable, the processor logs warnings and continues with the base response.
- Security Scanner Disabled: If llm-guard is not installed, scanning is disabled; install the dependency to enable input/output filtering.
- Stripe MCP Unavailable: The client falls back to mock payments; verify availability probing and retry behavior.
- TTS Failures: Text cleaning and retry logic mitigate common issues; verify Cartesia credentials and model configuration.
- State Corruption: Atomic operations and validation protect state integrity; inspect validation errors and version mismatches.

**Section sources**
- [src/conversation/processor.py](file://src/conversation/processor.py#L275-L452)
- [src/llm/tools.py](file://src/llm/tools.py#L386-L394)
- [src/rag/pipeline.py](file://src/rag/pipeline.py#L55-L58)
- [src/security/scanner.py](file://src/security/scanner.py#L20-L30)
- [src/payments/stripe_mcp.py](file://src/payments/stripe_mcp.py#L217-L272)
- [src/voice/tts.py](file://src/voice/tts.py#L133-L200)
- [src/utils/state_manager.py](file://src/utils/state_manager.py#L654-L677)

## Conclusion
MayaNCP’s layered architecture cleanly separates presentation, orchestration, integration, and persistence concerns. The event-driven UI feeds into a robust conversation processor that leverages LLM tooling, optional RAG augmentation, and strict state management. Cross-cutting concerns like security, payments, and voice synthesis are integrated with graceful fallbacks and observability. The MCP-based design positions MayaMCP for extensible integrations and reliable operation under varied conditions.

[No sources needed since this section summarizes without analyzing specific files]

## Appendices

### System Boundaries and External Integrations
- Google Gemini: LLM inference and tool binding via LangChain.
- Stripe MCP: Payment link creation, status polling, and fallback to mock payments.
- Cartesia: Real-time text-to-speech with retry and text normalization.

```mermaid
graph TB
subgraph "Internal"
UI["UI"]
Conv["Conversation Processor"]
State["State Manager"]
end
subgraph "External"
Gemini["Google Gemini API"]
Stripe["Stripe MCP Server"]
Cartesia["Cartesia TTS"]
end
UI --> Conv
Conv --> State
Conv --> Gemini
Conv --> Stripe
UI --> Cartesia
```

**Diagram sources**
- [src/llm/client.py](file://src/llm/client.py#L91-L129)
- [src/payments/stripe_mcp.py](file://src/payments/stripe_mcp.py#L183-L441)
- [src/voice/tts.py](file://src/voice/tts.py#L112-L132)