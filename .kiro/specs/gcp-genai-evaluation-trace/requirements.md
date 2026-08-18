# Requirements Document: MayaMCP v2.0.0

**Status**: Active  
**Author**: MayaMCP Architecture Team  
**Last Updated**: 2026-08-18  
**Derived From**: [`design.md`](file:///Users/pretermodernist/Developer/Personal/MayaMCP/.kiro/specs/gcp-genai-evaluation-trace/design.md)

---

## 1. User Stories

### User Story 1: Conversational Bartending & Persona (`US-1`)
- **As a** bar patron using the MayaMCP interface,
- **I want** to engage in natural, multi-turn conversation with Maya (the AI bartender),
- **So that** I receive engaging drink recommendations, bar trivia, and friendly service tailored to my tastes.

### User Story 2: Drink Ordering & Tab Tracking (`US-2`)
- **As a** patron ordering beverages,
- **I want** Maya to parse my order items, calculate itemized pricing, and update my open tab in real-time,
- **So that** I can see an accurate itemized total and live avatar tab overlay before settling my bill.

### User Story 3: Optimistic Stablecoin Payments on Base Sepolia (`US-3`)
- **As a** patron paying my bill with crypto,
- **I want** instant optimistic settlement of my tab with support for tip percentages (10%, 15%, 20%),
- **So that** my tab clears immediately while blockchain confirmation proceeds asynchronously in the background.

### User Story 4: Low-Latency Streaming Audio Synthesis (`US-4`)
- **As a** patron listening to Maya,
- **I want** streaming voice output synthesized via Cartesia TTS with sub-second time-to-first-audio,
- **So that** conversation feels fluid, natural, and free of awkward lag.

### User Story 5: Video & Vector Memory Retrieval (`US-5`)
- **As a** returning patron,
- **I want** Maya to recall past drink preferences and bar knowledge via Memvid video-memory and FAISS embeddings,
- **So that** my interactions are personalized and accurately grounded in bar recipes.

### User Story 6: Bring Your Own Key (BYOK) Security (`US-6`)
- **As a** security-conscious user,
- **I want** to securely supply my own Gemini and Cartesia API keys in the UI without server-side storage,
- **So that** my credentials remain encrypted in memory and expire upon session termination.

### User Story 7: Cloud-Native Telemetry & Google Cloud Trace (`US-7`)
- **As an** engineer or operator,
- **I want** all conversational turns, tool executions, and LLM requests instrumented via OpenTelemetry GenAI Semantic Conventions and exported directly to Google Cloud Trace,
- **So that** I have real-time visibility into token usage, latency breakdowns, and agent reasoning paths without third-party SaaS vendors.

### User Story 8: Automated Vertex AI Evaluation & Agent-as-a-Judge (`US-8`)
- **As an** ML/Agent engineer,
- **I want** automated evaluation suites running on Google Cloud Vertex AI Gen AI Evaluation Service (`EvalTask`) and Google Antigravity Agent-as-a-Judge,
- **So that** I can quantitatively benchmark response groundedness, tool trajectory precision, and payment recovery logic with pure GCP Application Default Credentials (ADC).

---

## 2. Functional Requirements

### 2.1 Core Agent & Conversation Engine
- **`FR-1.1`**: The system MUST utilize Google ADK (`google-adk`) and `google-genai` SDK for agent reasoning and tool invocation.
- **`FR-1.2`**: The LLM client MUST be obtained via [`get_genai_client()`](file:///Users/pretermodernist/Developer/Personal/MayaMCP/src/llm/client.py) supporting Vertex AI Standard Mode (`vertex=True`) and Google AI Studio fallbacks.
- **`FR-1.3`**: Conversational phase transitions (`GREETING` $\to$ `ORDERING` $\to$ `CLOSING`) MUST be managed deterministically by the phase manager.

### 2.2 State Management & Locking
- **`FR-2.1`**: All state modifications MUST be guarded by per-session `RLock` instances.
- **`FR-2.2`**: Payment status transitions MUST allow `pending → processing → completed → failed` to support asynchronous background payment failure simulation.
- **`FR-2.3`**: Deadlock prevention invariant: `_session_locks_mutex` MUST NEVER be held while acquiring a per-session `RLock`.

### 2.3 Web3 Payments & Deterministic Testing
- **`FR-3.1`**: Stablecoin payments MUST execute optimistically, returning a transaction hash immediately while dispatching on-chain verification in a background daemon thread.
- **`FR-3.2`**: Order totals of exactly `$99.99` MUST deterministically trigger simulated background payment failure to test "register malfunction" recovery workflows.

### 2.4 Multimodal RAG Pipeline
- **`FR-4.1`**: Memory retrieval MUST follow the graceful fallback chain: Memvid $\to$ FAISS vector store $\to$ ungrounded generation.

### 2.5 Observability & Google Cloud Trace (`Req-OTel`)
- **`FR-5.1`**: Telemetry MUST instrument every LLM call and agent step using OpenTelemetry standard GenAI attributes:
  - `gen_ai.system`: `"gemini"` or `"vertex_ai"`
  - `gen_ai.request.model`: Model version string
  - `gen_ai.request.temperature`: Sampling temperature
  - `gen_ai.usage.input_tokens`: Prompt token count
  - `gen_ai.usage.output_tokens`: Completion token count
  - `gen_ai.evaluation.metric_name`: Name of active metric (during eval)
  - `gen_ai.evaluation.score`: Metric grade score (during eval)
- **`FR-5.2`**: Spans MUST export directly to Google Cloud Trace using `opentelemetry-exporter-gcp-trace`.
- **`FR-5.3`**: If running in an unauthenticated or offline environment, telemetry MUST gracefully degrade to local non-blocking Python standard logging without raising uncaught exceptions.

### 2.6 Vertex AI Gen AI Evaluation Engine (`Req-Eval`)
- **`FR-6.1`**: Automated evaluation pipelines MUST use `vertexai.preview.evaluation.EvalTask`.
- **`FR-6.2`**: The evaluation suite MUST compute Pointwise metrics (`faithfulness`, `response_quality`) against cocktail recipe ground truth.
- **`FR-6.3`**: The evaluation suite MUST compute Agent Trajectory metrics (`trajectory_precision`, `trajectory_recall`, `trajectory_exact_match`) for multi-turn tool calling workflows (`add_to_order`, `process_crypto_payment`).
- **`FR-6.4`**: Agent-as-a-Judge evaluations MUST run using `google-antigravity.Agent` in Vertex AI Standard Mode (`vertex=True`) and validate structured outputs against Pydantic rubrics.

---

## 3. Non-Functional Requirements

### 3.1 Security & Zero-SaaS Isolation (`NFR-1`)
- **`NFR-1.1`**: The application and test suites MUST NOT require third-party SaaS tokens (`WANDB_API_KEY`, `WEAVE_API_KEY`, `LANGSMITH_API_KEY`).
- **`NFR-1.2`**: All GCP access MUST resolve via Google Cloud Application Default Credentials (ADC) or explicit service account paths (`GOOGLE_APPLICATION_CREDENTIALS`).
- **`NFR-1.3`**: User API keys provided in BYOK mode MUST be encrypted in-memory using Fernet symmetric encryption (`MAYA_MASTER_KEY`).

### 3.2 Performance, Latency & Rate Limits (`NFR-2`)
- **`NFR-2.1`**: Time-to-First-Token (TTFT) for streaming text generation MUST be $<500\text{ms}$ under paid Vertex AI tier.
- **`NFR-2.2`**: Evaluation suites MUST adapt concurrency based on `GEMINI_TIER`:
  - `GEMINI_TIER=paid`: Parallel execution (10+ workers) on Vertex AI.
  - `GEMINI_TIER=free`: Sequential execution (1 worker, 15 RPM throttling).

### 3.3 Offline Test Resilience (`NFR-3`)
- **`NFR-3.1`**: Standard pytest execution (`pytest -m "not slow"`) MUST execute 100% offline with zero external network calls by utilizing native SDK test doubles and stubs in [`tests/conftest.py`](file:///Users/pretermodernist/Developer/Personal/MayaMCP/tests/conftest.py).
- **`NFR-3.2`**: Global rate limiter limits in tests MUST be bypassed (`MAYA_SESSION_RATE_LIMIT=9999`) to prevent false-negative token exhaustion errors during test runs.

### 3.4 Context Caching & Cost Efficiency (`NFR-4`)
- **`NFR-4.1`**: Evaluation prompts with $>32\text{k}$ static tokens MUST structure static instructions, recipes, and rubrics as a contiguous prompt prefix to leverage GCP's 90% implicit context cache discount.
