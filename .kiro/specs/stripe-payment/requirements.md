# Requirements Document

## Introduction

This document specifies the requirements for integrating Stripe payment functionality into MayaMCP, the AI bartending agent. The feature enables simulated payment processing using Stripe's test mode and sandbox environment, providing a realistic proof-of-concept payment experience. Users start with a pre-determined balance of $1000 and can track their running tab through a visual counter overlay on Maya's avatar image. The counter displays animated updates as drinks are added to the order.

## Glossary

- **Stripe MCP Server**: Model Context Protocol server that provides Stripe API integration for payment operations
- **Test Mode**: Stripe's sandbox environment for simulating transactions without real money
- **Tab**: Running total of drinks ordered during a session, displayed visually to the user
- **Tab Counter**: Visual UI element overlaid on Maya's avatar showing the current tab amount
- **User Balance**: Pre-determined amount of money ($1000) available for the user to spend
- **Payment Link**: Stripe-generated URL for completing payment transactions
- **Animation**: Visual effect applied when the tab amount changes
- **Count-Up Animation**: Animation where the displayed number increments rapidly from the old value to the new value, creating a "counting up" effect
- **Pulse Effect**: Brief scale increase (1.0 to 1.1 to 1.0) applied to the counter during updates to draw attention
- **Tab Overlay**: Semi-transparent container positioned at the bottom-left of Maya's avatar containing the tab counter and balance display
- **Overlay Layout**: Tab counter on the left, balance display on the right, vertically center-aligned with 12px horizontal gap between them
- **Tip**: Optional gratuity amount added to the tab before payment
- **Tip Percentage**: Pre-defined tip options (10%, 15%, 20%) calculated from the current tab total
- **Tip Buttons**: Interactive UI elements in the Tab_Overlay allowing users to select a tip percentage
- **Selected Tip**: The currently chosen tip amount, displayed alongside the tab total

## Requirements

### Requirement 1

**User Story:** As a user, I want to have a starting balance of $1000, so that I can order drinks and simulate a realistic bar experience.

#### Acceptance Criteria

1. WHEN a new session starts THEN the Payment_System SHALL initialize the user balance to $1000.00
2. WHEN a user orders a drink THEN the Payment_System SHALL deduct the drink price from the user balance
3. WHEN the user balance is less than the drink price THEN the Payment_System SHALL reject the order, return an "INSUFFICIENT_FUNDS" error code, and Maya SHALL respond with a friendly message indicating the user cannot afford the drink and stating their current balance
4. WHEN the user requests their balance THEN the Payment_System SHALL display the current remaining balance
5. WHEN an order is rejected due to insufficient funds THEN the Payment_System SHALL preserve the current order state without clearing any items

### Requirement 2

**User Story:** As a user, I want to see my running tab displayed on Maya's avatar, so that I can track my spending in real-time.

#### Acceptance Criteria

1. WHEN the Gradio UI loads THEN the Tab_Overlay SHALL appear at the bottom-left of Maya's avatar with 16px padding from edges, displaying from top to bottom: (1) "Tab: $0.00" on the left and "Balance: $1000.00" on the right with 12px horizontal gap, (2) tip buttons row (hidden when tab is $0), (3) tip and total row (hidden when no tip selected)
2. WHEN a drink is added to the order THEN the Tab_Counter SHALL update to show the new total tab amount
3. WHEN the tab amount changes THEN the Tab_Counter SHALL animate using a count-up animation from the previous value to the new value with a pulse effect
4. WHILE the session is active THEN the Tab_Overlay SHALL remain visible with a semi-transparent dark background (rgba 0,0,0,0.7) for readability

### Requirement 3

**User Story:** As a user, I want to pay my tab using Stripe, so that I can complete my bar experience with a simulated payment.

#### Acceptance Criteria

1. WHEN a user requests to pay their bill THEN the Payment_System SHALL create a Stripe payment link using test mode
2. WHEN a Stripe payment link is created THEN the Payment_System SHALL return the link to the user for payment completion
3. WHEN a payment is processed successfully THEN the Payment_System SHALL mark the bill as paid and reset the tab counter
4. IF the Stripe MCP server is unavailable THEN the Payment_System SHALL fall back to the existing mock payment flow with a warning message

### Requirement 4

**User Story:** As a developer, I want the Stripe integration to use test mode, so that no real money is involved in transactions.

#### Acceptance Criteria

1. WHEN the Stripe MCP server is configured THEN the Payment_System SHALL use Stripe test API keys exclusively
2. WHEN creating payment links THEN the Payment_System SHALL use Stripe's test mode sandbox environment
3. WHEN displaying payment information THEN the Payment_System SHALL indicate that transactions are simulated

### Requirement 5

**User Story:** As a user, I want the tab counter animation to be visually appealing, so that I have an engaging experience when ordering drinks.

#### Acceptance Criteria

1. WHEN a new item is added to the tab THEN the Tab_Counter SHALL display a count-up animation incrementing from the previous total to the new total
2. WHEN the count-up animation plays THEN the Tab_Counter SHALL complete the animation within 500 milliseconds
3. WHEN multiple items are added rapidly THEN the Tab_Counter SHALL queue animations to prevent visual overlap
4. WHEN the count-up animation plays THEN the Tab_Counter SHALL apply a pulse effect to draw user attention

### Requirement 6

**User Story:** As a user, I want to see my remaining balance alongside my tab, so that I know how much I can still spend.

#### Acceptance Criteria

1. WHEN the UI displays the tab counter THEN the Balance_Display SHALL appear to the right of the Tab_Counter within the Tab_Overlay, vertically center-aligned with 12px horizontal gap
2. WHEN the balance changes THEN the Balance_Display SHALL update with the same count-up animation and pulse effect as the tab counter
3. WHEN the balance falls below $50 THEN the Balance_Display SHALL change text color from white to orange (#FFA500) to indicate low funds
4. WHEN the balance reaches $0 THEN the Balance_Display SHALL change text color to red (#FF4444) to indicate depleted funds

### Requirement 7

**User Story:** As a user, I want to add a tip for Maya's service, so that I can show appreciation for a great bartending experience.

#### Acceptance Criteria

1. WHEN the Tab_Overlay displays a non-zero tab THEN the Tip_Buttons SHALL appear below the tab and balance display showing three options: 10%, 15%, and 20%
2. WHEN a user clicks a Tip_Button THEN the Payment_System SHALL calculate the tip amount as the selected percentage of the current tab total, replacing any previously selected tip
3. WHEN a tip is selected THEN the Tab_Overlay SHALL display both "Tip: $X.XX" and "Total: $X.XX" simultaneously below the tip buttons, with the tip amount on the left and total on the right, both updating immediately when the tip selection changes
4. WHEN a tip is selected THEN the Total display SHALL show the sum of tab amount plus tip amount in the format "Total: $X.XX"
5. WHEN a user clicks a different Tip_Button THEN the Payment_System SHALL replace the previous tip with the newly calculated tip amount
6. WHEN a user clicks the currently selected Tip_Button THEN the Payment_System SHALL remove the tip (toggle behavior)
7. WHEN the tab total is $0.00 THEN the Tip_Buttons SHALL be hidden or disabled
8. WHEN a tip option is selected THEN the corresponding Tip_Button SHALL be visually distinguished from unselected buttons using a highlighted background color (#4CAF50) and the visual state SHALL update immediately on select, replace, and toggle actions to reflect the active or none state
9. WHEN a payment is processed THEN the Payment_System SHALL include the tip amount in the total charged
10. WHEN a payment is completed successfully THEN the Payment_System SHALL reset the tip amount to $0.00 along with the tab
11. WHEN a user clicks a Tip_Button THEN the UI SHALL notify Maya of the tip selection including the percentage and calculated amount, and Maya SHALL respond conversationally acknowledging the tip with gratitude
12. WHEN a user removes a tip by clicking the selected Tip_Button THEN the UI SHALL notify Maya of the tip removal, and Maya SHALL respond conversationally acknowledging the change without disappointment or offense
