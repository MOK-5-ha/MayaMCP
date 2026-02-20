# MayaMCP Comprehensive Performance and Latency Analysis

This document provides a detailed analysis of performance bottlenecks, latency issues, and unoptimized operations affecting the response times of the MayaMCP application. For each issue, specific locations, root causes, impacts, and recommendations are provided.

---

## 1. Synchronous LLM and Sequential TTS Generation (Highest Impact)

**Location:** 
- [src/conversation/processor.py](file:///Users/pretermodernist/MayaMCP/src/conversation/processor.py) inside [process_order()](file:///Users/pretermodernist/MayaMCP/src/conversation/processor.py#83-481) (Line 280): `ai_response = llm.invoke(messages)`
- [src/ui/handlers.py](file:///Users/pretermodernist/MayaMCP/src/ui/handlers.py) inside [handle_gradio_input()](file:///Users/pretermodernist/MayaMCP/src/ui/handlers.py#71-230) (Line 195): `audio_data = get_voice_audio(response_text, ...)`

**Nature of Bottleneck:** 
Synchronous blocking operations. The application waits for the large language model (LLM) to completely generate the full text response before returning to [handle_gradio_input](file:///Users/pretermodernist/MayaMCP/src/ui/handlers.py#71-230). Only after the text is fully available does it pass the entire response to Cartesia TTS. 

**Estimated Performance Impact:** 
Severe latency accumulation. The user experiences the combined maximum latency of the LLM generation time (often 2-5 seconds) plus the full TTS audio generation time (1-3 seconds).

**Recommendations:**
- **Streaming LLM Responses:** Replace `llm.invoke()` with `llm.stream()` and stream the chunks.
- **Pipelined TTS:** Buffer the streaming text (e.g., sentence-by-sentence) and send complete sentences to `get_voice_audio` asynchronously, yielding audio chunks to Gradio immediately so the audio can play while the LLM continues generating text.

---

## 2. Unoptimized Remote Dictionary Operations

**Location:** 
- [src/utils/state_manager.py](file:///Users/pretermodernist/MayaMCP/src/utils/state_manager.py) (Functions: [_get_session_data](file:///Users/pretermodernist/MayaMCP/src/utils/state_manager.py#312-364) and multiple state modifiers like [update_order_state](file:///Users/pretermodernist/MayaMCP/src/utils/state_manager.py#430-492), [update_conversation_state](file:///Users/pretermodernist/MayaMCP/src/utils/state_manager.py#409-429))

**Nature of Bottleneck:** 
Unoptimized storage/cache queries. The `state_manager` expects [store](file:///Users/pretermodernist/MayaMCP/src/llm/tools.py#213-219) to potentially be a `modal.Dict`. Fine-grained updates like modifying a single tip percentage trigger an immediate and full write-back: `store[session_id] = session_data` (Line 374).

**Estimated Performance Impact:** 
Moderate to High. If `modal.Dict` operates via remote procedure calls, every read and granular state write incurs network overhead. A single request mapping user -> LLM -> Tool -> State saves multiple times.

**Recommendations:**
- **Batch State Commits:** Implement a request-scoped local cache that absorbs all reads/writes within the lifecycle of [handle_gradio_input](file:///Users/pretermodernist/MayaMCP/src/ui/handlers.py#71-230), flushing to `modal.Dict` exactly once via a context manager or decorator at the end of the request.

---

## 3. Inefficient String and Loop Operations

**Location A:** [src/utils/helpers.py](file:///Users/pretermodernist/MayaMCP/src/utils/helpers.py) (Line 58) inside [detect_order_inquiry()](file:///Users/pretermodernist/MayaMCP/src/utils/helpers.py#9-70)
```python
matching_words = sum(1 for word in pattern_words if word in user_text.split())
```
**Nature:** Redundant loop operations. `user_text.split()` is re-executed inside the loop for every single word in `pattern_words`.

**Location B:** [src/rag/memvid_store.py](file:///Users/pretermodernist/MayaMCP/src/rag/memvid_store.py) (Line 113) inside `FallbackRetriever.search()`
```python
score = sum(1 for word in query_lower.split() if word in doc.lower())
```
**Nature:** `query_lower.split()` is repeatedly executed and checked inside the list comprehension for every retrieved document.

**Estimated Performance Impact:** 
Low to Moderate. While not directly breaking the app, doing constant O(N*M) text splitting on every message linearly degrades computation speed, especially for longer queries or larger prompt histories.

**Recommendations:**
- **Pre-compute:** Compute `user_words = set(user_text.split())` or `query_words = set(query_lower.split())` *before* the loop, and use O(1) set operations to calculate the overlap/score.

---

## 4. Redundant Logic and Technical Debt

**Location:** 
- [src/utils/state_manager.py](file:///Users/pretermodernist/MayaMCP/src/utils/state_manager.py) (Lines ~416-444)

**Nature:** Duplicate/Dead code paths. The functions [update_conversation_state](file:///Users/pretermodernist/MayaMCP/src/utils/state_manager.py#409-429) and [update_order_state](file:///Users/pretermodernist/MayaMCP/src/utils/state_manager.py#430-492) explicitly carry duplicate compatibility forks:
```python
    # Detect which API is being used
    if isinstance(session_id_or_updates, dict) and updates is None:
        # Old API
```

**Estimated Performance Impact:** 
Low but increases technical debt and code path complexity (maintenance overhead).

**Recommendations:**
- Refactor the codebase to eliminate the "Old API" logic entirely and standardise on explicitly passing [(session_id, store, updates)](file:///Users/pretermodernist/MayaMCP/src/mayamcp_cli.py#24-131) on all caller sides.

---

## 5. Unnecessary Dependencies (Bloat)

**Location:** 
- [requirements.txt](file:///Users/pretermodernist/MayaMCP/requirements.txt) (Line 34): `faiss-cpu>=1.10.0`
- [requirements.txt](file:///Users/pretermodernist/MayaMCP/requirements.txt) (Line 21): `matplotlib>=3.0.0`
- [src/rag/vector_store.py](file:///Users/pretermodernist/MayaMCP/src/rag/vector_store.py) (Legacy FAISS index logic)

**Nature:** Deprecated or unused dependencies loaded into memory. `faiss-cpu` is flagged in requirements as "Legacy FAISS (keeping for fallback compatibility)". The new [memvid_store.py](file:///Users/pretermodernist/MayaMCP/src/rag/memvid_store.py) provides its own built-in Python logic [FallbackRetriever](file:///Users/pretermodernist/MayaMCP/src/rag/memvid_store.py#98-132) when video assets fail.

**Estimated Performance Impact:** 
Moderate startup time and memory bloat. `faiss-cpu` is a heavy C++ binding dependency that significantly increases Docker image sizes and installation cold-start times on Modal container boots. 

**Recommendations:**
- Remove `faiss-cpu` from [requirements.txt](file:///Users/pretermodernist/MayaMCP/requirements.txt) and delete [src/rag/vector_store.py](file:///Users/pretermodernist/MayaMCP/src/rag/vector_store.py) entirely.
- Verify if `matplotlib` and `pillow` are strictly required by `qrcode` plugins; if not, remove them to drastically cut image dependencies and speed up container builds.
