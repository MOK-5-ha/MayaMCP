"""BDD step definitions for crypto payment scenarios.

Tests the optimistic payment flow using CryptoPaymentClient,
verifying instant tab clearing, state transitions, and failure handling.
"""

import pytest
from unittest.mock import patch, MagicMock
from pytest_bdd import scenarios, given, when, then, parsers

from src.utils.state_manager import (
    get_payment_state,
    reset_session_state,
    initialize_state,
    update_payment_state,
    update_order_state,
    get_payment_total,
)
from src.llm.tools import (
    process_crypto_payment,
    set_current_session,
    set_global_store,
)

# Load scenarios from feature file
scenarios('features/crypto_payment.feature')


class CryptoTestContext:
    """Shared state across BDD steps."""
    def __init__(self):
        self.session_id = "test_crypto_bdd_session"
        self.app_state = {}
        self.result = None
        self.no_session = False
        self.mock_client = None


@pytest.fixture
def ctx():
    return CryptoTestContext()


@pytest.fixture(autouse=True)
def mock_crypto_client(ctx, monkeypatch):
    """Mock the CryptoPaymentClient to prevent real CDP SDK calls."""
    mock_client = MagicMock()
    mock_client.is_configured = False
    mock_client.generate_tx_hash.return_value = "0x" + "ab" * 32
    mock_client.process_payment_optimistically.return_value = {
        "tx_hash": "0x" + "ab" * 32,
        "url": "https://sepolia.basescan.org/tx/0x" + "ab" * 32,
        "is_simulated": True,
    }

    ctx.mock_client = mock_client

    # Patch the module-level client getter in tools.py
    monkeypatch.setattr(
        "src.llm.tools.get_crypto_client",
        lambda: mock_client
    )


# ─── Given Steps ────────────────────────────────────────────────────

@given(
    parsers.parse("the crypto payment session is initialized with a balance of {balance:f}"),
    target_fixture="ctx"
)
def step_init_crypto_session(ctx, balance):
    """Initialize a fresh session with the given balance."""
    set_global_store(ctx.app_state)
    reset_session_state(ctx.session_id, ctx.app_state)
    initialize_state(ctx.session_id, ctx.app_state)
    update_payment_state(ctx.session_id, ctx.app_state, {"balance": balance})
    set_current_session(ctx.session_id)
    return ctx


@given(parsers.parse('the customer has ordered a "{item}" costing {price:f}'))
def step_customer_ordered(ctx, item, price):
    """Add an item to the order and update tab/balance."""
    update_order_state(ctx.session_id, ctx.app_state, "add_item", {
        "name": item,
        "price": price,
        "modifiers": "no modifiers",
        "quantity": 1
    })
    payment = get_payment_state(ctx.session_id, ctx.app_state)
    update_payment_state(ctx.session_id, ctx.app_state, {
        "tab_total": payment["tab_total"] + price,
        "balance": payment["balance"] - price
    })


@given(parsers.parse("the customer has set a {percentage:d} percent tip"))
def step_set_tip(ctx, percentage):
    """Set tip percentage on the current tab."""
    payment = get_payment_state(ctx.session_id, ctx.app_state)
    tip_amount = payment["tab_total"] * (percentage / 100.0)
    update_payment_state(ctx.session_id, ctx.app_state, {
        "tip_percentage": percentage,
        "tip_amount": tip_amount
    })


@given("there is no active session")
def step_no_session(ctx):
    """Clear the session context so tools see no active session."""
    ctx.no_session = True
    set_current_session(None)


@given("CDP API keys are not configured")
def step_no_cdp_keys(ctx):
    """Ensure the mock client reports simulation mode."""
    ctx.mock_client.is_configured = False
    ctx.mock_client.process_payment_optimistically.return_value["is_simulated"] = True


# ─── When Steps ─────────────────────────────────────────────────────

@when("the customer pays their bill")
def step_pay_bill(ctx):
    """Call the process_crypto_payment tool."""
    if not ctx.no_session:
        set_current_session(ctx.session_id)
    ctx.result = process_crypto_payment()


@when("the background transaction reports failure")
def step_background_fails(ctx):
    """Simulate background transaction failure by updating state directly."""
    update_payment_state(ctx.session_id, ctx.app_state, {
        "payment_status": "failed"
    })


# ─── Then Steps ─────────────────────────────────────────────────────

@then("the payment should succeed with a transaction hash")
def step_payment_succeeds(ctx):
    """Verify the payment tool returned success with a tx_hash."""
    assert ctx.result["status"] == "ok", f"Expected ok, got: {ctx.result}"
    assert "tx_hash" in ctx.result["result"]
    assert ctx.result["result"]["tx_hash"].startswith("0x")


@then(parsers.parse("the tab should be cleared to {amount:f}"))
def step_tab_cleared(ctx, amount):
    """Verify the tab total is now the expected amount."""
    payment = get_payment_state(ctx.session_id, ctx.app_state)
    assert abs(payment["tab_total"] - amount) < 0.01, (
        f"Tab should be {amount}, got {payment['tab_total']}"
    )


@then("the payment response should contain a BaseScan URL")
def step_has_basescan_url(ctx):
    """Verify the response includes a BaseScan explorer link."""
    url = ctx.result["result"]["url"]
    assert "sepolia.basescan.org/tx/" in url


@then(parsers.parse('the payment status should be "{status}"'))
def step_check_payment_status(ctx, status):
    """Verify the payment_status field in state."""
    payment = get_payment_state(ctx.session_id, ctx.app_state)
    assert payment["payment_status"] == status, (
        f"Expected status '{status}', got '{payment['payment_status']}'"
    )


@then(parsers.parse('the payment should fail with error "{error_code}"'))
def step_payment_fails(ctx, error_code):
    """Verify the payment tool returned an error."""
    assert ctx.result["status"] == "error", f"Expected error, got: {ctx.result}"
    assert ctx.result["error"] == error_code, (
        f"Expected error code '{error_code}', got '{ctx.result['error']}'"
    )


@then("the payment response should indicate simulation mode")
def step_simulated_mode(ctx):
    """Verify the response shows is_simulated=True."""
    assert ctx.result["result"]["is_simulated"] is True
