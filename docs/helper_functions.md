# MayaMCP Centralized Helper Functions Guide

This document catalogs the centralized helper functions located in `src/utils/helpers.py`. These DRY (Don't Repeat Yourself) utility functions promote clean, maintainable, single-responsibility code throughout MayaMCP.

---

## 1. Session & Request Utilities

### `extract_session_id(request: Any = None, default: str = "default") -> str`
- **Location**: [`src/utils/helpers.py`](file:///Users/pretermodernist/.gemini/antigravity/worktrees/MayaMCP/refactor_dry_utility_functions/src/utils/helpers.py)
- **Purpose**: Safely extracts the active `session_id` string from Gradio `gr.Request` objects, state dictionaries, or direct strings with a fallback default.
- **Use Cases**: Gradio UI callbacks, API endpoints, BYOK session handlers (`src/ui/handlers.py`, `src/ui/api_key_modal.py`).

```python
from src.utils.helpers import extract_session_id

# Example usage in Gradio handler:
session_id = extract_session_id(request)
```

---

## 2. Formatting & Conversion Utilities

### `format_currency(amount: Optional[float], default: float = 0.0) -> str`
- **Location**: [`src/utils/helpers.py`](file:///Users/pretermodernist/.gemini/antigravity/worktrees/MayaMCP/refactor_dry_utility_functions/src/utils/helpers.py)
- **Purpose**: Formats numeric floating-point values into standard USD currency strings (`$XX.XX`).
- **Use Cases**: Tab overlay, receipt formatting, payment responses, conversational logs.

```python
from src.utils.helpers import format_currency

text = f"Your total is {format_currency(12.5)}"  # Outputs: "Your total is $12.50"
```

### `safe_float(val: Any, default: float = 0.0) -> float`
- **Location**: [`src/utils/helpers.py`](file:///Users/pretermodernist/.gemini/antigravity/worktrees/MayaMCP/refactor_dry_utility_functions/src/utils/helpers.py)
- **Purpose**: Safely parses any input (strings, integers, None) to `float` without raising `ValueError` or `TypeError`.
- **Use Cases**: Numeric user inputs, API response parsing, state conversions.

```python
from src.utils.helpers import safe_float

val = safe_float("15.75", default=0.0)  # Returns: 15.75
```

---

## 3. Security & Obfuscation Utilities

### `mask_api_key(key: Optional[str], visible_chars: int = 4, suffix_chars: int = 4) -> str`
- **Location**: [`src/utils/helpers.py`](file:///Users/pretermodernist/.gemini/antigravity/worktrees/MayaMCP/refactor_dry_utility_functions/src/utils/helpers.py)
- **Purpose**: Obfuscates sensitive API keys for safe logging or debug display while retaining prefix/suffix identification.
- **Use Cases**: Client initialization logs, API key modal validation logging.

```python
from src.utils.helpers import mask_api_key

masked = mask_api_key("AIzaSy1234567890SecretKey")  # Returns: "AIza...tKey"
```

---

## 4. Response Standardization & Text Processing

### `build_response_dict(success: bool, message: str = "", data: Optional[Dict[str, Any]] = None, error_code: Optional[str] = None) -> Dict[str, Any]`
- **Location**: [`src/utils/helpers.py`](file:///Users/pretermodernist/.gemini/antigravity/worktrees/MayaMCP/refactor_dry_utility_functions/src/utils/helpers.py)
- **Purpose**: Constructs a uniform response dictionary with ISO UTC timestamps and consistent status keys.
- **Use Cases**: Tool execution outputs, security checks, payment status responses.

### `normalize_text(text: Optional[str]) -> str`
- **Location**: [`src/utils/helpers.py`](file:///Users/pretermodernist/.gemini/antigravity/worktrees/MayaMCP/refactor_dry_utility_functions/src/utils/helpers.py)
- **Purpose**: Strips leading/trailing whitespace, collapses internal whitespace, and lowercases text.
- **Use Cases**: Intent detection, keyword searches, speech act classification.

---

## 5. Conversational & Intent Detection Helpers

- `detect_order_inquiry(user_input: str)`: Detects if user is asking about order/bill.
- `detect_speech_acts(user_input: str, conversation_context: List[str])`: Intent recognition using speech act patterns.
- `determine_next_phase(current_state: Dict, order_placed: bool)`: Phase transition state machine.
- `append_to_history(history: List[Dict], user_text: str, assistant_text: str)`: Immutable chat history append helper.
