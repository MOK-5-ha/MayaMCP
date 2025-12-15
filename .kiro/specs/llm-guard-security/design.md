# Design Document: LLM Guard Security Integration

## Overview

This design describes the integration of llm-guard into MayaMCP to provide basic security hardening for the bartending agent. The integration adds a security scanning layer that checks user inputs for prompt injection and toxicity, and validates LLM outputs for toxic content before returning to users.

The design follows MayaMCP's existing patterns:
- Graceful degradation (security scanning → pass-through if unavailable)
- Centralized module structure under `src/`
- Fail-open error handling to maintain conversation flow

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                    Conversation Processor                        │
│                   (src/conversation/processor.py)                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Security Module                              │
│                    (src/security/)                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  scanner.py     │  │  config.py      │  │  __init__.py    │  │
│  │  - scan_input() │  │  - ScanConfig   │  │  - exports      │  │
│  │  - scan_output()│  │  - defaults     │  │                 │  │
│  │  - ScanResult   │  │  - serialization│  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     llm-guard library                            │
│  - PromptInjection scanner                                       │
│  - Toxicity scanner (input & output)                             │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### ScanResult (dataclass)

```python
@dataclass
class ScanResult:
    is_valid: bool          # True if content passed all scanners
    sanitized_text: str     # Original or modified text
    blocked_reason: str     # Reason if blocked, empty otherwise
    scanner_scores: dict    # Scanner name → score mapping
```

### ScanConfig (dataclass)

```python
@dataclass
class ScanConfig:
    prompt_injection_enabled: bool = True
    prompt_injection_threshold: float = 0.5
    toxicity_enabled: bool = True
    toxicity_threshold: float = 0.5
    
    def to_dict(self) -> dict: ...
    
    @classmethod
    def from_dict(cls, data: dict) -> "ScanConfig": ...
```

### Scanner Functions

```python
def scan_input(text: str, config: ScanConfig = None) -> ScanResult:
    """
    Scan user input for prompt injection and toxicity.
    Returns ScanResult with is_valid=False if blocked.
    Fails open on errors.
    """

def scan_output(text: str, prompt: str = "", config: ScanConfig = None) -> ScanResult:
    """
    Scan LLM output for toxicity.
    Returns ScanResult with fallback message if toxic.
    Fails open on errors.
    """

def is_available() -> bool:
    """Check if llm-guard is installed and functional."""
```

## Data Models

### Scanner Score Dictionary

```python
scanner_scores = {
    "prompt_injection": 0.0,  # 0.0-1.0, higher = more likely injection
    "toxicity": 0.0,          # 0.0-1.0, higher = more toxic
}
```

### Rejection Messages

```python
INPUT_BLOCKED_INJECTION = "I can't process that request. Could you rephrase?"
INPUT_BLOCKED_TOXIC = "Let's keep things friendly! How can I help with drinks?"
OUTPUT_FALLBACK = "I'm not sure how to respond to that. What drink can I get you?"
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Based on the prework analysis, the following properties can be verified through property-based testing:

### Property 1: Prompt injection inputs are blocked

*For any* input that the prompt injection scanner classifies as malicious (score above threshold), the scan_input function should return a ScanResult with is_valid=False and a non-empty blocked_reason.

**Validates: Requirements 1.2**

### Property 2: Toxic inputs are blocked

*For any* input that the toxicity scanner classifies as toxic (score above threshold), the scan_input function should return a ScanResult with is_valid=False and a non-empty blocked_reason.

**Validates: Requirements 2.1**

### Property 3: Toxic outputs are replaced with fallback

*For any* LLM output that the toxicity scanner classifies as toxic (score above threshold), the scan_output function should return a ScanResult where sanitized_text equals the fallback message, not the original text.

**Validates: Requirements 3.2**

### Property 4: Configuration round-trip consistency

*For any* valid ScanConfig object, serializing to dict then deserializing should produce an equivalent ScanConfig object with identical field values.

**Validates: Requirements 5.2**

## Error Handling

All scanner operations follow fail-open semantics:

1. **Import failure**: If llm-guard is not installed, `is_available()` returns False and scan functions pass through content unchanged
2. **Scanner initialization failure**: Caught and logged, scanner operates in pass-through mode
3. **Runtime scanner error**: Caught and logged, returns ScanResult with is_valid=True and original text

Error logging uses the existing `src/config/logging_config.get_logger()` pattern.

## Testing Strategy

### Property-Based Testing

The design uses **Hypothesis** (already in the project) for property-based testing:

- Minimum 100 iterations per property test
- Each property test tagged with format: `**Feature: llm-guard-security, Property {N}: {description}**`

### Unit Tests

Unit tests cover:
- Scanner initialization and availability checking
- Pass-through behavior when llm-guard unavailable
- Configuration serialization/deserialization
- Error handling paths

### Test Approach

Tests will mock llm-guard scanners to avoid:
- Slow model loading during tests
- External dependencies in CI
- Non-deterministic scanner behavior

The mock approach allows testing the integration logic while the property tests verify the contract between our code and the scanner results.
