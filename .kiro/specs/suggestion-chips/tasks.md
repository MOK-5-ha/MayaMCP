# Implementation Plan: Suggestion Chips Feature

## Overview

This implementation plan delivers dynamic suggestion chips to the MayaMCP UI. Chips are contextual, clickable UI elements generated in parallel with Maya's responses using a separate LLM call. The system uses Pydantic v2 for validation, ThreadPoolExecutor for parallel execution, and Gradio components for the UI.

**All test tasks are now required for production-ready implementation.**

## Tasks

- [x] 1. Create Pydantic v2 schemas for suggestion chips
  - Create `src/schemas/chips.py` with `ChipType`, `ActionID`, `SuggestionChip`, `SuggestionChipSet`, and `ChipGenerationContext` models
  - Implement field validators for action_id requirements, unique chip texts, and length constraints
  - Add model_dump() serialization support
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [x] 1.1 Write property test for chip schema validation
    - **Property 1: Chip text uniqueness within sets**
    - **Validates: Requirements 2.5**
    - Generate random chip sets and verify no duplicate texts (case-insensitive)
    - _Requirements: 2.5_

  - [x] 1.2 Write unit tests for schema validators
    - Test action_id validation for action vs dialogue chips
    - Test length constraints (2-40 characters, 3-6 chips)
    - Test enum validation for ChipType and ActionID
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 2. Implement ChipGenerator class with parallel execution
  - Create `src/conversation/chip_generator.py` with `ChipGenerator` class
  - Implement `__init__` with session_id and optional LLM client dependency injection
  - Implement `generate_chips_async()` with ThreadPoolExecutor submission and 3-second timeout enforcement
  - Implement `_generate_chips_sync()` for actual LLM call with structured output
  - Implement `_build_chip_prompt()` with prefix invariant caching structure
  - Implement `generate_fallback_chips()` for missing context scenarios
  - Add global `_chip_executor` ThreadPoolExecutor with max_workers=10
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 10.1, 10.2, 10.4_

  - [ ] 2.1 Add rate limiting and pending task cancellation
    - Check `RATE_LIMIT_SECONDS` (2.0) before submitting new generation tasks
    - Cancel pending tasks when new user message arrives
    - Track generation count and failure count in chip state
    - _Requirements: 1.4, 1.5, 10.5, 10.6, 7.5_

  - [ ] 2.2 Write property test for timeout enforcement
    - **Property 2: Chip generation never exceeds timeout**
    - **Validates: Requirements 1.4**
    - Mock slow LLM responses and verify timeout triggers within 3 seconds
    - _Requirements: 1.4_

  - [ ] 2.3 Write unit tests for ChipGenerator
    - Test successful chip generation with valid context
    - Test timeout handling returns None
    - Test validation failure returns None
    - Test LLM failure returns None
    - Test rate limit enforcement
    - Test pending task cancellation
    - Test fallback chip generation
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 7.5, 8.1, 8.2, 8.3, 8.4_

- [ ] 3. Implement conversation phase detection
  - Add `determine_conversation_phase()` function to `src/conversation/processor.py`
  - Detect phases: greeting, ordering, describing, payment, complete
  - Use payment status and response content keywords for detection
  - Return "greeting" as default for early conversations (<3 turns)
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6_

  - [ ] 3.1 Write unit tests for phase detection
    - Test payment phase detection (pending, processing, completed)
    - Test greeting phase detection
    - Test describing phase detection (recipe keywords)
    - Test ordering phase detection (order keywords)
    - Test early conversation default to greeting
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6_

- [ ] 4. Integrate chip generation into conversation processor
  - Modify `process_user_message()` in `src/conversation/processor.py` to trigger chip generation after response completes
  - Extract last 4 conversation turns for context
  - Build `ChipGenerationContext` with turns, payment status, phase, and recent user messages
  - Instantiate `ChipGenerator` and call `generate_chips_async()`
  - Store result in session state `chip_state.current_chips`
  - Use `generate_fallback_chips()` when conversation history is empty
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 8.4_

  - [ ] 4.1 Write integration test for chip generation flow
    - Test full flow: user message → response stream → chip generation → session storage
    - Test fallback chips for empty conversation history
    - Test chip storage in session state
    - Verify non-blocking behavior (response completes before chips)
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 5. Create Gradio chip row UI component
  - Create `src/ui/chips.py` with chip styling constants and CSS
  - Implement `create_chip_row()` to create Row with 6 placeholder Button components
  - Define `DIALOGUE_CHIP_STYLE` and `ACTION_CHIP_STYLE` with gradients and accessibility
  - Define `ACTION_ICONS` dictionary mapping ActionID to emoji prefixes
  - Add responsive CSS for mobile (44x44px touch targets) and desktop
  - Add accessibility CSS: focus indicators, high contrast mode, reduced motion support
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.6, 9.1, 9.4, 9.5, 9.6_

  - [ ] 5.1 Write visual regression tests for chip styling
    - Test dialogue chip rendering (gradient, padding, border-radius)
    - Test action chip rendering (accent color, icon prefix, font-weight)
    - Test mobile responsive scaling
    - Test focus indicator visibility
    - _Requirements: 4.1, 4.2, 4.3, 4.6, 9.5, 9.6_

- [ ] 6. Implement chip update and click handlers
  - Implement `update_chips()` in `src/ui/chips.py` to read session state and update button visibility/content
  - Add icon prefixes for action chips using `ACTION_ICONS`
  - Set ARIA labels for accessibility
  - Implement `handle_chip_click()` to process dialogue vs action chips
  - For dialogue chips: populate textbox, focus input (no auto-submit)
  - For action chips: validate action_id, populate textbox, auto-submit
  - For unrecognized action_id: fallback to dialogue behavior
  - Implement `register_chip_handlers()` to wire button click events
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [ ] 6.1 Write unit tests for chip handlers
    - Test dialogue chip click populates textbox without submit
    - Test action chip click populates and auto-submits
    - Test unrecognized action_id falls back to dialogue behavior
    - Test icon prefix addition for action chips
    - Test ARIA label generation
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 11.5, 11.6_

- [ ] 7. Wire chip components into main Gradio UI
  - Modify `src/ui/main.py` or equivalent to integrate `create_chip_row()`
  - Position chip row below chat display and above input textbox
  - Call `update_chips()` after each Maya response completes
  - Call `register_chip_handlers()` during UI initialization
  - Hide chip row when user submits message (before Maya responds)
  - Show chip row after Maya response and chips are generated
  - _Requirements: 6.1, 6.2, 6.6_

  - [ ] 7.1 Write integration test for chip lifecycle
    - Test chips hide on user message submission
    - Test chips update after Maya response
    - Test chips persist across UI refreshes within same turn
    - Test chips clear on session reset
    - _Requirements: 6.1, 6.2, 6.3, 6.5, 6.6_

- [ ] 8. Add chip state management to session store
  - Add `chip_state` dictionary to session state schema
  - Store `current_chips` (SuggestionChipSet), `last_generation_time`, `generation_count`, `failure_count`, `pending_task`
  - Ensure thread-safe access using existing session RLock
  - Implement chip state serialization with `to_dict()` for persistence
  - _Requirements: 6.3, 7.6_

  - [ ] 8.1 Write unit tests for chip state management
    - Test chip state storage in session
    - Test chip state retrieval from session
    - Test chip state serialization
    - Test thread-safe concurrent access
    - _Requirements: 6.3, 7.6_

- [ ] 9. Implement comprehensive error handling
  - Add timeout logging when chip generation exceeds 3 seconds
  - Add validation error logging when Pydantic validation fails
  - Add LLM error logging when API call fails
  - Ensure all failures return None/empty chip set without user-visible errors
  - Track failure count in chip state for monitoring
  - Log generation timing metrics for performance monitoring
  - _Requirements: 1.5, 8.1, 8.2, 8.3, 8.5, 7.6_

  - [ ] 9.1 Write property test for error handling
    - **Property 3: All chip generation errors result in empty chips, never exceptions**
    - **Validates: Requirements 1.5, 8.1, 8.2, 8.3, 8.5**
    - Inject various failure modes (timeout, validation, LLM error) and verify graceful degradation
    - _Requirements: 1.5, 8.1, 8.2, 8.3, 8.5_

- [ ] 10. Add accessibility support
  - Implement ARIA live region in chip row for screen reader announcements
  - Add keyboard navigation support (Tab, Enter, Space)
  - Ensure focus indicators with 2px outline
  - Test with screen reader (announce chip updates)
  - Verify minimum 44x44px touch targets for mobile
  - Verify 4.5:1 contrast ratio for chip text
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 4.6_

  - [ ] 10.1 Write accessibility compliance tests
    - Test ARIA label presence on all chips
    - Test keyboard focus navigation
    - Test Enter/Space key activation
    - Test touch target dimensions (44x44px minimum)
    - Test contrast ratio calculation (4.5:1 minimum)
    - _Requirements: 9.1, 9.2, 9.3, 9.5, 9.6, 4.6_

- [ ] 11. Implement testing and validation hooks
  - Add `test_mode` flag to ChipGenerator for deterministic output
  - Support LLM client dependency injection in ChipGenerator constructor
  - Add debug logging for chip generation context and results
  - Create mock conversation context factory for unit tests
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [ ] 11.1 Write unit tests for testing hooks
    - Test test_mode returns deterministic chips
    - Test dependency injection with mock LLM client
    - Test mock context factory produces valid contexts
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [ ] 12. Add context-aware chip content generation
  - Implement prompt instructions for post-order payment chips
  - Implement prompt instructions for drink description follow-up chips
  - Implement prompt instructions for greeting phase menu inquiry chips
  - Implement prompt instructions for pending payment action chips
  - Add deduplication logic to filter recent user messages (last 2)
  - Add conversation phase priority weighting in prompt
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ] 12.1 Write integration tests for context-aware generation
    - Test post-order context generates payment and order-another chips
    - Test drink description context generates follow-up question chips
    - Test greeting context generates menu inquiry chips
    - Test pending payment context prioritizes payment action chip
    - Test deduplication filters recent user messages
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 13. Optimize performance and resource usage
  - Verify chip generation prompt stays under 512 tokens
  - Verify LLM max_output_tokens set to 200
  - Implement conversation context caching in ChipGenerator._cache
  - Reuse existing Gemini client from session state (no new connections)
  - Verify concurrent request limit (10 max via ThreadPoolExecutor)
  - Verify rate limit enforcement (1 per 2 seconds per session)
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

  - [ ] 13.1 Write performance tests
    - Test prompt token count stays under 512
    - Test output token limit enforcement (200)
    - Test concurrent generation request limit (10)
    - Test rate limit enforcement timing (2 seconds)
    - _Requirements: 10.1, 10.2, 10.5, 10.6_

- [ ] 14. Final integration and end-to-end testing
  - Run full conversation flow with chip generation enabled
  - Test all conversation phases (greeting, ordering, describing, payment, complete)
  - Test all action chip types (payment, tip, menu, cancel, order_another)
  - Verify accessibility with screen reader and keyboard-only navigation
  - Verify mobile responsive behavior on small viewports
  - Verify graceful degradation when chip generation fails
  - Ensure all tests pass (unit, integration, property-based, BDD)
  - _Requirements: All requirements_

  - [ ] 14.1 Write end-to-end integration tests
    - Test complete user journey: greeting → ordering → description → payment with chips at each phase
    - Test all action chip routing (payment, tip, menu, cancel, order_another)
    - Test failure scenarios (timeout, validation error, LLM error)
    - Test session lifecycle (chips clear on reset)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 11.1, 11.2, 11.3, 11.4, 11.5, 6.5_

  - [ ] 14.2 Write BDD acceptance tests for conversation phase flows
    - Create `tests/behavior/features/suggestion_chips.feature` with Gherkin scenarios (see template below)
    - Implement step definitions in `tests/behavior/test_suggestion_chips.py`
    - Use `pytest-bdd` to integrate with existing test suite
    - Map BDD scenarios to existing fixtures and helpers (session state, mock LLM client)
    - Run BDD tests alongside integration tests in CI/CD
    - _Requirements: All requirements (acceptance testing coverage)_

## BDD Feature File Content

`tests/behavior/features/suggestion_chips.feature` should contain scenarios covering:
- Greeting phase chip generation with menu inquiry chips
- Ordering phase chip generation with payment and order-another chips  
- Payment pending phase chip generation with payment action chip priority
- Drink description phase chip generation with follow-up dialogue chips
- Chip deduplication (no recent message repeats)
- Action chip auto-submit behavior
- Dialogue chip focus-but-no-submit behavior
- Graceful degradation on LLM timeout/failure
- Keyboard navigation and accessibility
- Session reset clears chips

See design document for complete Gherkin feature file template with 18 detailed scenarios.

## Notes

- **All test tasks are now required** (no optional markers)
- BDD tests provide executable acceptance criteria for product/design stakeholders
- BDD scenarios map directly to requirements for full traceability
- Step definitions reuse existing fixtures and mocks from unit/integration tests
- BDD tests run alongside pytest suite in CI/CD pipeline
- Chip generation runs in parallel thread pool and never blocks Maya's response stream
- All failures result in empty chip sets with logging, never user-visible errors
- UI components follow WCAG 2.1 AA accessibility guidelines with ARIA support
- The system supports dependency injection for testing (mock LLM clients, mock contexts)
- Property-based tests validate universal correctness properties from the design document

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["1.1", "1.2", "2"] },
    { "id": 2, "tasks": ["2.1", "2.2", "2.3", "3"] },
    { "id": 3, "tasks": ["3.1", "4"] },
    { "id": 4, "tasks": ["4.1", "5", "8"] },
    { "id": 5, "tasks": ["5.1", "6", "8.1"] },
    { "id": 6, "tasks": ["6.1", "7", "9"] },
    { "id": 7, "tasks": ["7.1", "9.1", "10", "11", "12"] },
    { "id": 8, "tasks": ["10.1", "11.1", "12.1", "13"] },
    { "id": 9, "tasks": ["13.1", "14"] },
    { "id": 10, "tasks": ["14.1", "14.2"] }
  ]
}
```
