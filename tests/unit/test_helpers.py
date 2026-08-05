"""Unit tests for centralized helper functions in src.utils.helpers."""

from unittest.mock import MagicMock

from src.utils.helpers import (
    build_response_dict,
    extract_session_id,
    format_currency,
    mask_api_key,
    normalize_text,
    safe_float,
)


def test_extract_session_id():
    # None or empty
    assert extract_session_id(None) == "default"
    assert extract_session_id(None, default="fallback") == "fallback"

    # String input
    assert extract_session_id("session123") == "session123"
    assert extract_session_id("   ") == "default"

    # Gradio Request object mock
    req_mock = MagicMock()
    req_mock.session_hash = "hash_abc_123"
    assert extract_session_id(req_mock) == "hash_abc_123"

    # Gradio Request object mock with None session_hash
    req_mock_none = MagicMock()
    req_mock_none.session_hash = None
    assert extract_session_id(req_mock_none) == "default"

    # Dictionary input
    assert extract_session_id({"session_hash": "hash_xyz"}) == "hash_xyz"
    assert extract_session_id({"session_id": "id_xyz"}) == "id_xyz"
    assert extract_session_id({}) == "default"


def test_format_currency():
    assert format_currency(12.5) == "$12.50"
    assert format_currency(0) == "$0.00"
    assert format_currency(1000.999) == "$1001.00"
    assert format_currency(None) == "$0.00"
    assert format_currency(None, default=5.0) == "$5.00"


def test_safe_float():
    assert safe_float(12.5) == 12.5
    assert safe_float("15.75") == 15.75
    assert safe_float(None) == 0.0
    assert safe_float("invalid", default=9.9) == 9.9
    assert safe_float([1, 2], default=0.0) == 0.0


def test_mask_api_key():
    assert mask_api_key("AIzaSy1234567890SecretKey") == "AIza...tKey"
    assert mask_api_key("AIzaSy1234567890SecretKey", visible_chars=6, suffix_chars=6) == "AIzaSy...retKey"
    assert mask_api_key("short") == "****"
    assert mask_api_key(None) == "****"
    assert mask_api_key("") == "****"



def test_build_response_dict():
    res_success = build_response_dict(True, message="Order processed", data={"order_id": 42})
    assert res_success["status"] == "success"
    assert res_success["success"] is True
    assert res_success["message"] == "Order processed"
    assert res_success["data"] == {"order_id": 42}
    assert "timestamp" in res_success

    res_err = build_response_dict(False, message="Payment failed", error_code="ERR_PAYMENT")
    assert res_err["status"] == "error"
    assert res_err["success"] is False
    assert res_err["message"] == "Payment failed"
    assert res_err["error_code"] == "ERR_PAYMENT"


def test_normalize_text():
    assert normalize_text("  Hello  WORLD!  ") == "hello world!"
    assert normalize_text("") == ""
    assert normalize_text(None) == ""
