# Pre-existing Test Failures

14 tests are currently failing due to bugs unrelated to the `google-genai` SDK migration.
These are tracked here for future resolution.

## Root Causes

### 1. `extract_emotion` UnboundLocalError in `processor.py` (8 tests)

`extract_emotion()` is defined inside a conditional branch at line ~175 of
`src/conversation/processor.py`. When the code takes a different branch,
`extract_emotion` is not defined, yet line 428 tries to call it unconditionally.
This also causes `process_order` to return 5 values instead of the 6 that
`src/ui/handlers.py:86` expects, cascading into the UI handler failures.

**Affected tests:**

| # | Test | Error |
|---|------|-------|
| 1 | `test_maya_memvid_full.py::test_maya_memvid_full` | `ValueError: too many values to unpack (expected 5)` |
| 2 | `test_processor_rag.py::test_rag_short_circuits_when_components_missing` | `ValueError: too many values to unpack (expected 5)` |
| 3 | `test_processor_rag.py::test_safe_length_check_with_non_sized_rag_response` | `ValueError: too many values to unpack (expected 5)` |
| 4 | `test_processor_security.py::test_processor_replaces_toxic_output` | `ValueError: too many values to unpack (expected 5)` |
| 5 | `test_processor_security.py::test_processor_allows_valid_interaction` | `ValueError: too many values to unpack (expected 5)` |
| 6 | `test_session_context.py::TestSessionContextInProcessor::test_process_order_sets_session_context` | `UnboundLocalError: extract_emotion` |
| 7 | `test_ui_handlers.py::TestHandleGradioInput::test_handle_gradio_input_successful_processing` | `ValueError: not enough values to unpack (expected 6, got 5)` |
| 8 | `test_ui_handlers.py::TestHandleGradioInput::test_handle_gradio_input_tts_failure` | `ValueError: not enough values to unpack (expected 6, got 5)` |

**Fix:** Move `extract_emotion()` definition to module level or to the top of
`process_order()` so it is always in scope.

### 2. UI handler / process_order return-value mismatch (2 tests)

`src/ui/handlers.py:86` expects 6 return values from `process_order`, but the
error path only returns 5. Downstream, audio and emotion state are never set.

| # | Test | Error |
|---|------|-------|
| 9 | `test_ui_handlers.py::TestHandleGradioInput::test_handle_gradio_input_with_rag_components` | `assert None == b'audio_data'` |
| 10 | (same root cause as #7-8 above) | |

**Fix:** Ensure `process_order` always returns a consistent 6-tuple. Update
callers and tests to match.

### 3. UI launcher state count drift (2 tests)

The Gradio interface was updated (likely an added State component) but the test
assertions still expect the old counts.

| # | Test | Error |
|---|------|-------|
| 11 | `test_ui_launcher.py::TestLaunchBartenderInterface::test_launch_bartender_interface_with_default_avatar` | `assert 9 == 8` (State call count) |
| 12 | `test_ui_launcher.py::TestLaunchBartenderInterface::test_launch_bartender_interface_event_handlers` | `assert 7 == 6` (submit inputs length) |

**Fix:** Update assertions to match the current number of Gradio State components.

### 4. Memvid retriever missing-dependency guard (2 tests)

Tests expect `FileNotFoundError` / `json.JSONDecodeError` from `load_index`,
but the constructor raises `ImportError` earlier because optional Memvid
dependencies (qreader, cv2) are not installed in the test environment.

| # | Test | Error |
|---|------|-------|
| 13 | `test_memvid_retriever.py::TestMemvidRetriever::test_load_index_file_not_found` | `ImportError` (dependencies not available) |
| 14 | `test_memvid_retriever.py::TestMemvidRetriever::test_load_index_invalid_json` | `ImportError` (dependencies not available) |

There is also a related failure:

| # | Test | Error |
|---|------|-------|
| -- | `test_memvid_retriever.py::TestMemvidRetriever::test_empty_index_data` | Same `ImportError` from constructor |

**Fix:** Either mock the dependency check in these tests, or skip them when
Memvid dependencies are unavailable.
