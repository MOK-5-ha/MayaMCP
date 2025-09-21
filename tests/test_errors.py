#!/usr/bin/env python3
"""
Unit tests for src.utils.errors.classify_and_log_genai_error regex-based classification.
"""

import sys
import re
import pytest

# Ensure 'src' is on sys.path
sys.path.insert(0, 'src')

from src.utils.errors import classify_and_log_genai_error


class FakeLogger:
    def __init__(self):
        self.warns = []
        self.errors = []
    def warning(self, msg: str) -> None:
        self.warns.append(msg)
    def error(self, msg: str) -> None:
        self.errors.append(msg)


def _classify(msg: str):
    lg = FakeLogger()
    classify_and_log_genai_error(Exception(msg), lg, context="in test")
    return lg


def test_rate_limit_regex_matches_variants():
    # Basic case-insensitive match with word boundaries and optional whitespace
    lg1 = _classify("Rate limit exceeded")
    assert any("Rate limit" in m for m in lg1.warns)
    assert not lg1.errors

    lg2 = _classify("hit the RATE   LIMIT please slow down")
    assert any("Rate limit" in m for m in lg2.warns)
    assert not lg2.errors


def test_rate_limit_does_not_match_unrelated_words():
    # Should not match words merely containing 'rate' fragments
    lg = _classify("Device vibrated; limiter tripped")
    # No numeric code and no proper 'rate limit' phrase -> generic error
    assert lg.warns == []
    assert any(m.startswith("Error ") for m in lg.errors)


def test_auth_regex_matches_auth_terms():
    for txt in ["auth failure", "authentication failed", "authorization denied"]:
        lg = _classify(txt)
        assert any("Authentication error" in m for m in lg.errors)
        assert lg.warns == []


def test_auth_regex_does_not_match_author_word():
    lg = _classify("author metadata missing")
    # Should not be classified as authentication error
    assert not any("Authentication error" in m for m in lg.errors)
    assert any(m.startswith("Error ") for m in lg.errors)


def test_status_codes_still_trigger_classification():
    lg = _classify("HTTP 401 Unauthorized")
    assert any("Authentication error" in m for m in lg.errors)

    lg2 = _classify("HTTP 429 Too Many Requests")
    assert any("Rate limit" in m for m in lg2.warns)

