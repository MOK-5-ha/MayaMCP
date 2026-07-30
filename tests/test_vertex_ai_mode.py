"""Unit tests for GCP Vertex AI Mode client initialization and environment resolution."""

import os
from unittest.mock import patch

import pytest
from google.genai import Client

from src.config.api_keys import get_api_keys, get_gcp_location, get_gcp_project, is_vertex_ai_mode
from src.llm.client import get_genai_client, _CLIENT_LOCK


@pytest.fixture(autouse=True)
def reset_genai_client_singleton():
    """Reset the global genai client singleton before and after each test."""
    import src.llm.client as client_module
    with _CLIENT_LOCK:
        client_module._genai_client = None
        client_module._genai_client_key = None
    yield
    with _CLIENT_LOCK:
        client_module._genai_client = None
        client_module._genai_client_key = None


def test_api_keys_gcp_project_resolution():
    """Test get_gcp_project and is_vertex_ai_mode environment resolution."""
    with patch.dict(os.environ, {"GCP_PROJECT": "test-project-123", "GOOGLE_CLOUD_PROJECT": ""}):
        assert get_gcp_project() == "test-project-123"
        assert is_vertex_ai_mode() is True
        assert get_gcp_location() == "global"

    with patch.dict(os.environ, {"GCP_PROJECT": "", "GOOGLE_CLOUD_PROJECT": "fallback-project-456", "GCP_LOCATION": "us-central1"}):
        assert get_gcp_project() == "fallback-project-456"
        assert is_vertex_ai_mode() is True
        assert get_gcp_location() == "us-central1"

    with patch.dict(os.environ, {}, clear=True):
        assert get_gcp_project() is None
        assert is_vertex_ai_mode() is False


def test_get_genai_client_vertex_ai_mode():
    """Test that get_genai_client creates a Vertex AI Client when GCP_PROJECT is set."""
    env = {"GCP_PROJECT": "gen-lang-client-0070523080", "GCP_LOCATION": "global", "GEMINI_API_KEY": ""}
    with patch.dict(os.environ, env):
        client = get_genai_client()
        assert isinstance(client, Client)
        # Re-fetching returns singleton
        client2 = get_genai_client()
        assert client is client2


def test_get_genai_client_key_fallback():
    """Test that get_genai_client falls back to AI Studio API key mode when GCP_PROJECT is unset."""
    env = {"GCP_PROJECT": "", "GOOGLE_CLOUD_PROJECT": "", "GEMINI_API_KEY": "AIzaSyDummyKey123"}
    with patch.dict(os.environ, env):
        client = get_genai_client()
        assert isinstance(client, Client)


def test_get_genai_client_error_when_no_credentials():
    """Test that get_genai_client raises ValueError when neither GCP project nor API key is set."""
    env = {"GCP_PROJECT": "", "GOOGLE_CLOUD_PROJECT": "", "GEMINI_API_KEY": ""}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ValueError, match="GCP Vertex AI configuration error"):
            get_genai_client()
