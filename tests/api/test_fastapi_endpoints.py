"""Tests for FastAPI REST and SSE endpoints."""

import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from src.fast_api_app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_healthz_endpoint(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.text == "ok"


def test_collect_feedback(client):
    payload = {"score": 5, "comment": "Great cocktail!"}
    response = client.post("/feedback", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "success"}


def test_session_status_no_keys(client):
    response = client.get("/api/v1/session/status", headers={"X-Session-ID": "test-session-123"})
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session-123"
    assert data["has_valid_keys"] is False


def test_session_submit_keys(client):
    payload = {"gemini_key": "dummy-gemini-key", "cartesia_key": "dummy-cartesia-key"}
    response = client.post(
        "/api/v1/session/keys",
        json=payload,
        headers={"X-Session-ID": "test-session-123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["has_valid_keys"] is True


def test_session_reset(client):
    response = client.post(
        "/api/v1/session/reset",
        headers={"X-Session-ID": "test-session-123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_chat_without_keys_fails(client):
    payload = {"user_input": "Get me a whiskey neat"}
    response = client.post(
        "/api/v1/chat",
        json=payload,
        headers={"X-Session-ID": "no-keys-session"}
    )
    assert response.status_code == 400
    assert "API keys" in response.json()["detail"]


@patch("src.routers.chat.process_order")
@patch("src.routers.chat.has_valid_keys", return_value=True)
@patch("src.routers.chat.get_api_key_state", return_value={"gemini_key": "fake-key", "cartesia_key": "fake-key"})
@patch("src.routers.chat.get_session_llm")
@patch("src.routers.chat.get_session_tts")
def test_chat_successful_response(mock_tts, mock_llm, mock_keys_state, mock_has_keys, mock_process_order, client):
    mock_process_order.return_value = (
        "Here is your whiskey neat!",
        [{"role": "user", "content": "whiskey neat"}, {"role": "assistant", "content": "Here is your whiskey neat!"}],
        [],
        [{"item": "whiskey neat", "price": 12.0}],
        None
    )
    
    payload = {"user_input": "whiskey neat"}
    response = client.post(
        "/api/v1/chat",
        json=payload,
        headers={"X-Session-ID": "valid-session"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["response_text"] == "Here is your whiskey neat!"
    assert len(data["current_order"]) == 1
    assert data["current_order"][0]["item"] == "whiskey neat"


def test_payments_tab_info(client):
    response = client.get(
        "/api/v1/payments/tab",
        headers={"X-Session-ID": "test-session-123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "tab_amount" in data
    assert "balance" in data


def test_payments_add_tip(client):
    payload = {"tip_percentage": 20}
    response = client.post(
        "/api/v1/payments/tip",
        json=payload,
        headers={"X-Session-ID": "test-session-123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tip_percentage"] == 20


def test_payments_negative_tip_amount_rejected(client):
    payload = {"tip_amount": -5.0}
    response = client.post(
        "/api/v1/payments/tip",
        json=payload,
        headers={"X-Session-ID": "test-session-123"}
    )
    assert response.status_code == 422


def test_payments_both_tip_percentage_and_amount_rejected(client):
    payload = {"tip_percentage": 20, "tip_amount": 5.0}
    response = client.post(
        "/api/v1/payments/tip",
        json=payload,
        headers={"X-Session-ID": "test-session-123"}
    )
    assert response.status_code == 400
    assert "Provide either tip_percentage or tip_amount" in response.json()["detail"]


def test_add_to_order_negative_quantity_rejected():
    from src.llm.tools import add_to_order_with_balance
    result = add_to_order_with_balance(item_name="Martini", quantity=-1)
    assert result["status"] == "error"
    assert result["error"] == "INVALID_QUANTITY"


@patch("src.routers.chat.get_session_llm")
@patch("src.routers.chat.has_valid_keys", return_value=True)
@patch("src.routers.chat.get_api_key_state", return_value={"gemini_key": "fake-key"})
def test_chat_session_limit_exceeded_returns_429(mock_keys_state, mock_has_keys, mock_llm, client):
    from src.llm.session_registry import SessionLimitExceededError
    mock_llm.side_effect = SessionLimitExceededError("Bar capacity reached")
    
    payload = {"user_input": "whiskey"}
    response = client.post(
        "/api/v1/chat",
        json=payload,
        headers={"X-Session-ID": "valid-session"}
    )
    assert response.status_code == 429
    assert "Bar capacity reached" in response.json()["detail"]


def test_concurrent_session_status_and_keys_race_safety(client):
    import threading
    session_id = "race-test-session-999"
    results = []

    def call_status():
        resp = client.get("/api/v1/session/status", headers={"X-Session-ID": session_id})
        results.append(("status", resp.status_code))

    def call_submit_keys():
        payload = {"gemini_key": "race-test-key-valid"}
        resp = client.post("/api/v1/session/keys", json=payload, headers={"X-Session-ID": session_id})
        results.append(("keys", resp.status_code))

    t1 = threading.Thread(target=call_status)
    t2 = threading.Thread(target=call_submit_keys)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Verify keys are valid after concurrent operations
    status_resp = client.get("/api/v1/session/status", headers={"X-Session-ID": session_id})
    assert status_resp.json()["has_valid_keys"] is True


@patch("src.routers.chat.process_order_stream", return_value=iter([]))
@patch("src.routers.chat.has_valid_keys", return_value=True)
@patch("src.routers.chat.get_api_key_state", return_value={"gemini_key": "fake-key"})
@patch("src.routers.chat.get_session_llm")
def test_chat_stream_query_session_id_and_initial_session_event(mock_llm, mock_keys, mock_has_keys, mock_stream, client):
    response = client.get("/api/v1/chat/stream?message=hello&session_id=query-session-777")
    assert response.status_code == 200
    assert response.headers["X-Session-ID"] == "query-session-777"
    lines = response.text.split("\n\n")
    assert len(lines) >= 1
    event_data = json.loads(lines[0].replace("data: ", ""))
    assert event_data == {"type": "session", "session_id": "query-session-777"}

