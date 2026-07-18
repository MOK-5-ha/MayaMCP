Feature: Maya Bartending Agent Behavior
  As a customer at the virtual bar
  I want to interact with Maya
  So that I can order drinks, check my tab, set a tip, and chat.

  Scenario: Empathetic small talk before ordering
    Given the session is initialized with a balance of 50.00
    When the user says "Man, work has been really stressful today. I just need a drink and someone to talk to."
    Then Maya should respond empathetically
    And Maya's emotional state should be "neutral" or "thinking"

  Scenario: Order a drink with sufficient balance
    Given the session is initialized with a balance of 50.00
    When the user says "I'll have a martini, please."
    Then Maya should call the order tool for "Martini"
    And the item "Martini" should be in the current order
    And the customer tab should be 13.00
    And the customer balance should be 37.00

  Scenario: Insufficient balance rejects the order
    Given the session is initialized with a balance of 5.00
    When the user says "I want a martini."
    Then Maya should inform the user of insufficient funds
    And the current order should be empty

  Scenario: Adding a tip toggle
    Given the session is initialized with a balance of 50.00
    And the current order contains "Martini"
    When the user says "Please add a 20% tip to the bill."
    Then Maya should set the tip percentage to 20
    And the tip amount should be 2.60
    And the final total should be 15.60
