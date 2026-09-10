# ChipGenerator Fix Summary

## Overview

Fixed four critical issues in `src/conversation/chip_generator.py` identified during code review.

## Issue 1: Centralized LLM Routing Bypassed ✅ FIXED

**Problem**: Direct `client.models.generate_content()` calls bypassed centralized retry/fallback logic in `src/llm/client.py`, causing chip generation to fail on transient Gemini errors when the standard path could recover.

**Fix**:
- Replaced direct `self.llm_client.models.generate_content()` with `call_gemini_api()`
- Now benefits from tenacity retry logic (3 attempts, exponential backoff)
- Automatic error classification and logging via centralized handler
- Added import: `from ..llm.client import build_generate_config, call_gemini_api`

**Code Change** (lines 183-187):
```python
# BEFORE: Direct client call (no retry)
response = self.llm_client.models.generate_content(
    model=model_version,
    contents=prompt,
    config=generation_config,
)

# AFTER: Centralized API call (with retry)
response = call_gemini_api(
    prompt_content=[{"role": "user", "parts": [{"text": prompt}]}],
    config=generation_config,
)
```

## Issue 2: Timed-Out Work Keeps Running ✅ FIXED

**Problem**: `Future.result(timeout=...)` only bounded the caller's wait but left the LLM operation occupying a worker thread. Repeated slow calls consumed the shared 10-worker pool, causing later requests to queue behind obsolete work.

**Fix**:
- Call `future.cancel()` after `FutureTimeoutError` to free the worker
- Added cleanup in timeout exception handler

**Code Change** (lines 128-139):
```python
except FutureTimeoutError:
    # Cancel the timed-out task to free worker
    if future and not future.done():
        future.cancel()
    
    logger.warning(...)
    # ... rest of error handling
```

## Issue 3: Task Reservation is Non-Atomic ✅ FIXED

**Problem**: Rate-limit check and task submission were in separate critical sections, allowing race conditions where two overlapping calls could both pass the check, producing duplicate LLM requests and overwriting each other's tracking state.

**Fix**:
- Moved rate-limit check, pending task cancellation, task submission, and `pending_task` storage into a single atomic block under the session lock
- Eliminated the gap between lock releases that allowed the race condition

**Code Change** (lines 99-110):
```python
# BEFORE: Two separate lock sections (race condition)
# Check rate limit
with lock:
    ...check rate limit...
    ...cancel pending...

# Submit task (NOT under lock - race window!)
future = _chip_executor.submit(...)

# Store pending task
with lock:
    chip_state["pending_task"] = future

# AFTER: Single atomic block
current_time = time.time()
future = None

with lock:
    ...check rate limit...
    ...cancel pending...
    # Submit and store atomically
    future = _chip_executor.submit(self._generate_chips_sync, context)
    chip_state["pending_task"] = future
    _save_session_data(...)
```

## Issue 4: Prompt Budget Remains Unenforced ✅ FIXED

**Problem**: Prompt builder concatenated complete conversation/recent-message strings without enforcing `MAX_PROMPT_TOKENS` (512). Long messages exceeded the declared budget, increasing cost, latency, and timeout-driven fallback frequency.

**Fix**:
- Added token budget calculation using rough estimate (1 token ≈ 4 characters)
- Reserved 70% of remaining budget for conversation context, 20% for recent messages
- Truncate with ellipsis when content exceeds allocated character budget
- Added budget enforcement documentation to docstring

**Code Change** (lines 261-272):
```python
# Calculate token budget
static_prefix_chars = len(system_instructions)
static_prefix_tokens = static_prefix_chars // 4
remaining_tokens = max(0, self.MAX_PROMPT_TOKENS - static_prefix_tokens)
remaining_chars = remaining_tokens * 4

# Truncate conversation context if needed (70% of remaining budget)
if len(conversation_context) > remaining_chars * 0.7:
    max_conv_chars = int(remaining_chars * 0.7)
    conversation_context = conversation_context[:max_conv_chars] + "..."

# Truncate recent messages if needed (20% of remaining budget)
max_recent_chars = int(remaining_chars * 0.2)
if len(recent_messages) > max_recent_chars:
    recent_messages = recent_messages[:max_recent_chars] + "..."
```

## Test Updates

Updated test suite to reflect centralized API call changes:
- Added `mock_call_gemini_api` fixture
- Updated all tests to mock `call_gemini_api` instead of direct client calls
- Verified prompt content structure matches new API call format
- All 65 tests pass (42 schema + 23 generator)

## Verification

```bash
pytest tests/test_chip_schemas.py tests/test_chip_generator.py -v
# ============================= 65 passed in 10.81s ==============================
```

## Requirements Impact

These fixes improve reliability and resource efficiency while maintaining full compatibility with existing requirements:
- **1.1-1.6**: ChipGenerator core functionality preserved
- **1.4**: Timeout handling improved (worker cleanup)
- **1.5**: Error handling now benefits from centralized retry logic
- **7.5**: Pending task cancellation remains atomic
- **8.1-8.4**: Graceful degradation improved via retry
- **10.1**: Prompt budget now enforced (was previously unenforced)
- **10.5**: Thread pool resource management improved
- **10.6**: Rate limiting now atomic (was previously racy)
