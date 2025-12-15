# Implementation Plan

- [ ] 1. Set up security module structure
  - [ ] 1.1 Create `src/security/__init__.py` with module exports
    - Export scan_input, scan_output, ScanResult, ScanConfig, is_available
    - _Requirements: 4.1_
  - [ ] 1.2 Create `src/security/config.py` with ScanConfig dataclass
    - Define ScanConfig with prompt_injection_enabled, prompt_injection_threshold, toxicity_enabled, toxicity_threshold
    - Implement to_dict() and from_dict() methods for serialization
    - _Requirements: 5.1, 5.2_
  - [ ] 1.3 Write property test for configuration round-trip
    - **Property 4: Configuration round-trip consistency**
    - **Validates: Requirements 5.2**

- [ ] 2. Implement core scanner functionality
  - [ ] 2.1 Create `src/security/scanner.py` with ScanResult dataclass
    - Define ScanResult with is_valid, sanitized_text, blocked_reason, scanner_scores
    - _Requirements: 1.2, 2.1, 3.2_
  - [ ] 2.2 Implement is_available() function
    - Check if llm-guard is installed via import attempt
    - Return False and log warning if unavailable
    - _Requirements: 4.1, 4.2_
  - [ ] 2.3 Implement scan_input() function
    - Initialize PromptInjection and Toxicity scanners from llm-guard
    - Run scanners based on config, check thresholds
    - Return ScanResult with blocked_reason if thresholds exceeded
    - Fail open on any errors
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2_
  - [ ] 2.4 Write property test for prompt injection blocking
    - **Property 1: Prompt injection inputs are blocked**
    - **Validates: Requirements 1.2**
  - [ ] 2.5 Write property test for toxic input blocking
    - **Property 2: Toxic inputs are blocked**
    - **Validates: Requirements 2.1**

- [ ] 3. Implement output scanning
  - [ ] 3.1 Implement scan_output() function
    - Initialize Toxicity output scanner from llm-guard
    - Check toxicity threshold, replace with fallback if exceeded
    - Fail open on any errors
    - _Requirements: 3.1, 3.2, 3.3_
  - [ ] 3.2 Write property test for toxic output replacement
    - **Property 3: Toxic outputs are replaced with fallback**
    - **Validates: Requirements 3.2**

- [ ] 4. Checkpoint - Make sure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Integrate with conversation processor
  - [ ] 5.1 Add scan_input call before LLM invocation in processor.py
    - Import security module with graceful fallback
    - Call scan_input on user_input_text before processing
    - Return early with blocked message if is_valid=False
    - _Requirements: 1.1, 1.2, 2.1_
  - [ ] 5.2 Add scan_output call after LLM response in processor.py
    - Call scan_output on agent_response_text before returning
    - Use sanitized_text from result
    - _Requirements: 3.1, 3.2_
  - [ ] 5.3 Write unit tests for processor integration
    - Test that blocked inputs return rejection message
    - Test that toxic outputs are replaced
    - Test graceful degradation when security module unavailable
    - _Requirements: 1.2, 3.2, 4.1_

- [ ] 6. Add llm-guard dependency
  - [ ] 6.1 Update requirements.txt with llm-guard
    - Add llm-guard as optional dependency
    - _Requirements: 4.1_
  - [ ] 6.2 Update pyproject.toml with optional security extras
    - Add [security] extras group with llm-guard
    - _Requirements: 4.1_

- [ ] 7. Final Checkpoint - Make sure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
