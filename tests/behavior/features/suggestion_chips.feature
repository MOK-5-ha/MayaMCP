Feature: Contextual Suggestion Chips
  As a customer at the virtual bar
  I want contextual suggestion chips after each Maya response
  So that I can quickly continue the conversation or take actions.

  Background:
    Given Maya is initialized in Vertex AI mode
    And a new user session is created

  Scenario: Greeting phase generates menu inquiry chips
    When Maya greets the user
    Then suggestion chips should be generated
    And at least one chip should be a dialogue chip
    And at least one chip should contain "menu" or "recommend" or "popular"

  Scenario Outline: Chips adapt to conversation phase
    Given the conversation is in the <phase> phase
    When Maya completes a response
    Then suggestion chips should be generated
    And the chip set should contain 3 to 6 chips
    And at least one chip should be relevant to <phase>
    
    Examples:
      | phase      |
      | greeting   |
      | ordering   |
      | payment    |
      | describing |

  Scenario: Post-order context generates payment chips
    Given the user has ordered a "Margarita" costing 14.00
    When Maya confirms the order with the price
    Then the conversation phase should be "payment"
    And suggestion chips should be generated
    And at least one chip should be an action chip with action_id "payment"
    And at least one chip should be an action chip with action_id "order_another"

  Scenario: Payment pending prioritizes payment action chip
    Given the user has ordered a drink
    And the payment status is "pending"
    When Maya completes a response
    Then suggestion chips should be generated
    And at least one chip should be an action chip with action_id "payment"
    And the payment chip should appear in the first 3 chips

  Scenario: Drink description generates follow-up chips
    Given the user has asked "What's in an Old Fashioned?"
    When Maya describes the drink ingredients
    Then the conversation phase should be "describing"
    And suggestion chips should be generated
    And at least two chips should be dialogue chips
    And the dialogue chips should contain follow-up questions or modifications

  Scenario: Chips deduplicate recent user messages
    Given the user has said "Tell me more" in the last 2 messages
    When Maya completes a response
    And suggestion chips are generated
    Then no chip should have text matching "Tell me more" (case-insensitive)

  Scenario: Action chip auto-submits
    Given Maya has suggested an action chip with action_id "payment"
    When the user clicks the "Complete payment" chip
    Then the textbox should be populated with "Complete payment"
    And the message should auto-submit without manual confirmation
    And the payment flow should be triggered

  Scenario: Dialogue chip populates without auto-submit
    Given Maya has suggested a dialogue chip "Tell me more"
    When the user clicks the "Tell me more" chip
    Then the textbox should be populated with "Tell me more"
    And the textbox should receive focus
    And the message should NOT auto-submit

  Scenario: Unrecognized action_id falls back to dialogue behavior
    Given Maya has suggested an action chip with unrecognized action_id "unknown_action"
    When the user clicks the chip
    Then the textbox should be populated with the chip text
    And the message should NOT auto-submit
    And a fallback warning should be logged

  Scenario: LLM timeout returns empty chip set
    Given the chip generation LLM call takes 4 seconds
    When Maya completes a response
    Then chip generation should timeout after 3 seconds
    And no chips should be displayed
    And a timeout warning should be logged
    And Maya's response should NOT be delayed

  Scenario: LLM validation error returns empty chip set
    Given the chip generation LLM returns invalid JSON
    When Maya completes a response
    Then chip validation should fail
    And no chips should be displayed
    And a validation error should be logged
    And Maya's response should NOT be delayed

  Scenario: Empty conversation history generates fallback chips
    Given the user session has no conversation history
    When Maya completes the first response
    Then fallback greeting chips should be generated
    And the fallback chips should include "Show me the menu"
    And the fallback chips should include "Surprise me"

  Scenario: Chips hide on user message submission
    Given suggestion chips are currently displayed
    When the user submits a new message
    Then the chips should hide immediately
    And new chips should only appear after Maya responds

  Scenario: Chips persist across UI refreshes within turn
    Given suggestion chips are displayed after Maya's response
    When the UI component refreshes
    Then the chips should remain visible
    And the chip content should not change

  Scenario: Session reset clears chips
    Given suggestion chips are currently displayed
    When the user session is reset
    Then all chip state should be cleared
    And no chips should be displayed

  Scenario: Keyboard navigation activates chips
    Given suggestion chips are displayed
    When the user presses Tab to focus a chip
    And the user presses Enter
    Then the chip should activate (populate textbox)
    And the chip should behave according to its type (auto-submit or focus)

  Scenario: Chips have minimum touch target size
    Given suggestion chips are displayed on mobile viewport
    Then each chip should have minimum 44x44 pixel touch target
    And chips should be horizontally scrollable without vertical overflow

  Scenario: Chips have accessible contrast ratio
    Given suggestion chips are displayed
    Then dialogue chips should have at least 4.5:1 contrast ratio
    And action chips should have at least 4.5:1 contrast ratio

  Scenario: Screen reader announces chip updates
    Given suggestion chips are displayed
    When new chips are generated after Maya's response
    Then the ARIA live region should announce the chip update
    And each chip should have an ARIA label indicating type and text

  Scenario: Rate limit prevents rapid chip generation
    Given chip generation completed 1 second ago
    When chip generation is triggered again
    Then generation should be skipped for rate limit
    And no new chips should be generated

  Scenario: Pending task cancellation when new message arrives
    Given chip generation is in progress
    When the user submits a new message
    Then the pending chip generation task should be cancelled
    And new chip generation should start for the new turn

  Scenario: Enter key activates focused chip
    Given suggestion chips are displayed
    And the first chip dialogue is focused
    When the user presses Enter
    Then the chip should activate and populate textbox
    And the message should NOT auto-submit

  Scenario: Space key activates focused chip
    Given suggestion chips are displayed
    And the second chip action is focused
    When the user presses Space
    Then the chip should activate and populate textbox
    And the message should auto-submit without manual confirmation

