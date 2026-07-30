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
