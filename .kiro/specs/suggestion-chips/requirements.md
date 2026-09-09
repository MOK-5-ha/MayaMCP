# Requirements Document

## Introduction

This document specifies the requirements for dynamic suggestion chips in MayaMCP, an AI bartending agent. Suggestion chips are contextual, clickable UI elements that guide users toward relevant next actions or dialogue turns. The chips refresh with every Maya response and are generated in parallel using a separate LLM call to ensure low latency and context-aware suggestions.

## Glossary

- **Maya**: The AI bartending conversational agent
- **Suggestion_Chip**: A clickable UI element displaying a short text prompt for user action
- **Dialogue_Chip**: A suggestion chip that represents a conversational response option
- **Action_Chip**: A suggestion chip that triggers a system action (payment, tip, menu)
- **Chip_Generator**: The LLM-powered component that produces contextually relevant suggestion chips
- **Conversation_Manager**: The component managing Maya's conversational state and message flow
- **UI_Component**: The Gradio-based visual interface element displaying suggestion chips
- **Structured_Output**: Pydantic v2 validated JSON schema returned by the LLM
- **Session_State**: The thread-safe per-user state including conversation history and payment status
- **Response_Stream**: The real-time text generation flow from Maya's primary LLM call

## Requirements

### Requirement 1: Chip Generation Architecture

**User Story:** As a developer, I want suggestion chips generated in parallel with Maya's response, so that chip generation does not increase response latency

#### Acceptance Criteria

1. WHEN Maya generates a response, THE Chip_Generator SHALL execute a separate LLM call in parallel with the Response_Stream
2. THE Chip_Generator SHALL accept the current conversation context as input
3. THE Chip_Generator SHALL return Structured_Output conforming to a Pydantic v2 schema
4. THE Chip_Generator SHALL complete within 3 seconds or return an empty chip set
5. IF the Chip_Generator fails, THEN THE System SHALL log the error and display no chips without blocking Maya's response
6. THE Chip_Generator SHALL use the Google Gemini model configured in the Session_State

### Requirement 2: Structured Output Schema

**User Story:** As a developer, I want chips to be type-safe and validated, so that the UI receives consistent, well-formed data

#### Acceptance Criteria

1. THE Chip_Generator SHALL output a Structured_Output containing a list of suggestion chips
2. THE Structured_Output SHALL validate each chip has a text field of 2 to 40 characters
3. THE Structured_Output SHALL validate each chip has a type field with values "dialogue" or "action"
4. THE Structured_Output SHALL validate the chip list contains 3 to 6 chips
5. IF the LLM returns invalid Structured_Output, THEN THE Chip_Generator SHALL log a validation error and return an empty chip set
6. THE Structured_Output SHALL include an optional action_id field for Action_Chip types

### Requirement 3: Context-Aware Chip Content

**User Story:** As a user, I want suggestion chips relevant to the current conversation, so that I can easily continue the interaction

#### Acceptance Criteria

1. WHEN Maya completes a drink order, THE Chip_Generator SHALL include Action_Chip options for payment or ordering another drink
2. WHEN Maya describes a drink, THE Chip_Generator SHALL include Dialogue_Chip options for follow-up questions or modifications
3. WHEN the conversation is in greeting phase, THE Chip_Generator SHALL include Dialogue_Chip options for menu inquiries or drink preferences
4. WHEN a payment is pending, THE Chip_Generator SHALL include Action_Chip options for completing payment or canceling the order
5. THE Chip_Generator SHALL not repeat chips that match the user's last 2 messages
6. THE Chip_Generator SHALL prioritize chips aligned with the current conversation phase

### Requirement 4: Chip Type Differentiation

**User Story:** As a user, I want to visually distinguish dialogue and action chips, so that I understand which chips trigger system functions

#### Acceptance Criteria

1. THE UI_Component SHALL display Dialogue_Chip instances with a neutral color scheme
2. THE UI_Component SHALL display Action_Chip instances with a distinct accent color scheme
3. THE UI_Component SHALL render all chips with rounded corners and padding for readability
4. THE UI_Component SHALL display chips in a horizontal scrollable row
5. WHEN a chip type is "action", THE UI_Component SHALL display an icon prefix indicating the action category
6. THE UI_Component SHALL ensure chip text is readable with minimum contrast ratio of 4.5:1

### Requirement 5: Chip Interaction Behavior

**User Story:** As a user, I want chips to populate my input when clicked, so that I can quickly submit suggested actions

#### Acceptance Criteria

1. WHEN a user clicks a Suggestion_Chip, THE UI_Component SHALL populate the text input field with the chip text
2. WHEN a user clicks a Dialogue_Chip, THE UI_Component SHALL focus the text input field for potential editing
3. WHEN a user clicks an Action_Chip, THE UI_Component SHALL auto-submit the text without requiring additional user action
4. THE UI_Component SHALL clear any existing text in the input field before populating chip text
5. THE UI_Component SHALL provide visual feedback (hover state) when a user hovers over a Suggestion_Chip
6. THE UI_Component SHALL support keyboard navigation for accessibility

### Requirement 6: Chip Lifecycle Management

**User Story:** As a user, I want chips to refresh with each Maya response, so that suggestions stay relevant to the conversation

#### Acceptance Criteria

1. WHEN Maya completes a response, THE System SHALL display the newly generated chip set
2. WHEN the user submits a message, THE System SHALL hide the current chip set until Maya responds
3. THE System SHALL maintain only the most recent chip set in Session_State
4. THE System SHALL not display chips if the Chip_Generator returns an empty set
5. THE System SHALL clear chips when the session is reset or terminated
6. THE System SHALL persist chips across UI component refreshes within the same conversation turn

### Requirement 7: Integration with Conversation Manager

**User Story:** As a developer, I want chip generation integrated with the conversation flow, so that chips are produced consistently without code duplication

#### Acceptance Criteria

1. THE Conversation_Manager SHALL invoke the Chip_Generator after Maya's response text is complete
2. THE Conversation_Manager SHALL pass the last 4 conversation turns as context to the Chip_Generator
3. THE Conversation_Manager SHALL include the current Session_State payment status in the chip generation context
4. THE Conversation_Manager SHALL not block the Response_Stream while waiting for chip generation
5. IF chip generation is still pending when a new user message arrives, THEN THE System SHALL cancel the pending chip generation task
6. THE Conversation_Manager SHALL log chip generation timing metrics for performance monitoring

### Requirement 8: Fallback and Error Handling

**User Story:** As a user, I want the system to degrade gracefully if chip generation fails, so that I can continue the conversation without disruption

#### Acceptance Criteria

1. IF the Chip_Generator times out, THEN THE System SHALL log a timeout warning and proceed without chips
2. IF the LLM returns malformed JSON, THEN THE System SHALL log a parsing error and proceed without chips
3. IF the Structured_Output validation fails, THEN THE System SHALL log the validation errors and proceed without chips
4. IF the Session_State is missing conversation history, THEN THE Chip_Generator SHALL generate generic greeting chips
5. THE System SHALL not display error messages to the user when chip generation fails
6. THE System SHALL track chip generation failure rate as a system health metric

### Requirement 9: Accessibility and Responsiveness

**User Story:** As a user with accessibility needs, I want chips to be navigable and usable, so that I can interact with Maya effectively

#### Acceptance Criteria

1. THE UI_Component SHALL provide ARIA labels for all Suggestion_Chip elements
2. THE UI_Component SHALL support keyboard focus and activation via Enter or Space keys
3. THE UI_Component SHALL announce chip updates to screen readers using ARIA live regions
4. THE UI_Component SHALL scale chips responsively for mobile and desktop viewports
5. THE UI_Component SHALL ensure touch targets are minimum 44x44 pixels for mobile accessibility
6. THE UI_Component SHALL maintain visual focus indicators with minimum 2px outline

### Requirement 10: Performance and Resource Constraints

**User Story:** As a system operator, I want chip generation to be resource-efficient, so that it does not degrade overall system performance

#### Acceptance Criteria

1. THE Chip_Generator SHALL use a maximum of 512 tokens for the chip generation prompt
2. THE Chip_Generator SHALL request a maximum of 200 output tokens from the LLM
3. THE Chip_Generator SHALL cache the conversation context representation to minimize memory overhead
4. THE Chip_Generator SHALL reuse the existing Gemini client connection from Session_State
5. THE System SHALL limit concurrent chip generation requests to 10 per user session
6. THE System SHALL rate-limit chip generation to 1 request per 2 seconds per session

### Requirement 11: Action Chip Routing

**User Story:** As a user, I want action chips to trigger the correct system functions, so that I can complete tasks efficiently

#### Acceptance Criteria

1. WHEN an Action_Chip with action_id "payment" is clicked, THE System SHALL route to the payment flow
2. WHEN an Action_Chip with action_id "tip" is clicked, THE System SHALL route to the tip selection interface
3. WHEN an Action_Chip with action_id "menu" is clicked, THE System SHALL display the drink menu
4. WHEN an Action_Chip with action_id "cancel" is clicked, THE System SHALL cancel the current order and reset Session_State
5. THE System SHALL validate action_id values against a predefined action registry
6. IF an Action_Chip has an unrecognized action_id, THEN THE System SHALL treat it as a Dialogue_Chip and populate the text input without auto-submit

### Requirement 12: Testing and Validation Hooks

**User Story:** As a QA engineer, I want chip generation to be testable in isolation, so that I can verify behavior without full system integration

#### Acceptance Criteria

1. THE Chip_Generator SHALL accept a mock conversation context for unit testing
2. THE Chip_Generator SHALL support dependency injection for the LLM client
3. THE System SHALL provide a test mode flag that returns deterministic chip sets for UI testing
4. THE System SHALL expose chip generation metrics via logging for integration testing
5. THE UI_Component SHALL support programmatic chip injection for visual regression testing
6. THE System SHALL provide a debug endpoint that returns the raw Structured_Output for inspection
