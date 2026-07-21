Feature: Crypto Payment Processing
  As a customer at the virtual bar
  I want to pay my tab using stablecoin on Base Sepolia
  So that my payment clears instantly and I can continue my conversation.

  Background:
    Given the crypto payment session is initialized with a balance of 100.00

  Scenario: Successful optimistic payment clears tab instantly
    Given the customer has ordered a "Martini" costing 13.00
    When the customer pays their bill
    Then the payment should succeed with a transaction hash
    And the tab should be cleared to 0.00
    And the payment response should contain a BaseScan URL
    And the payment status should be "completed"

  Scenario: Payment includes tip in total
    Given the customer has ordered a "Martini" costing 13.00
    And the customer has set a 20 percent tip
    When the customer pays their bill
    Then the payment should succeed with a transaction hash
    And the tab should be cleared to 0.00

  Scenario: Empty tab rejects payment
    When the customer pays their bill
    Then the payment should fail with error "PAYMENT_FAILED"

  Scenario: Payment without active session fails
    Given there is no active session
    When the customer pays their bill
    Then the payment should fail with error "INVALID_SESSION"

  Scenario: Simulated mode works without CDP keys
    Given CDP API keys are not configured
    And the customer has ordered a "Martini" costing 13.00
    When the customer pays their bill
    Then the payment should succeed with a transaction hash
    And the payment response should indicate simulation mode

  Scenario: Background transaction failure updates state to failed
    Given the customer has ordered a "Martini" costing 13.00
    When the customer pays their bill
    And the background transaction reports failure
    Then the payment status should be "failed"
