"""Unit tests for GCP Vertex AI Mode client initialization and environment resolution."""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.config.api_keys import get_gcp_location, get_gcp_project, is_vertex_ai_mode
from src.llm.client import _CLIENT_LOCK, get_genai_client


@pytest.fixture(autouse=True)
def reset_genai_client_singleton():
    """Reset the global genai client singleton before and after each test."""
    import src.llm.client as client_module

    with _CLIENT_LOCK:
        client_module._genai_client = None
        client_module._genai_client_project = None
        client_module._genai_client_location = None
    yield
    with _CLIENT_LOCK:
        client_module._genai_client = None
        client_module._genai_client_project = None
        client_module._genai_client_location = None


def test_api_keys_gcp_project_resolution():
    """Test get_gcp_project and is_vertex_ai_mode environment resolution."""
    with patch.dict(os.environ, {"GCP_PROJECT": "test-project-123", "GOOGLE_CLOUD_PROJECT": ""}):
        assert get_gcp_project() == "test-project-123"
        assert is_vertex_ai_mode() is True
        assert get_gcp_location() == "global"

    with patch.dict(
        os.environ,
        {"GCP_PROJECT": "", "GOOGLE_CLOUD_PROJECT": "fallback-project-456", "GCP_LOCATION": "us-central1"},
    ):
        assert get_gcp_project() == "fallback-project-456"
        assert is_vertex_ai_mode() is True
        assert get_gcp_location() == "us-central1"

    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="GCP_PROJECT or GOOGLE_CLOUD_PROJECT is not configured"):
            get_gcp_project()


def test_get_genai_client_vertex_ai_mode():
    """Test that get_genai_client creates a Vertex AI Client with mocked constructor when GCP_PROJECT is set."""
    env = {"GCP_PROJECT": "test-vertex-project", "GCP_LOCATION": "global", "GEMINI" + "_API_KEY": ""}
    mock_client_instance = MagicMock()
    with patch.dict(os.environ, env):
        with patch("src.llm.client.genai.Client", return_value=mock_client_instance) as mock_client_cls:
            client = get_genai_client()
            mock_client_cls.assert_called_once_with(vertexai=True, project="test-vertex-project", location="global")
            assert client is mock_client_instance

            # Re-fetching returns singleton
            client2 = get_genai_client()
            assert client is client2
            assert mock_client_cls.call_count == 1


def test_get_genai_client_error_when_no_credentials():
    """Test that get_genai_client raises ValueError when neither GCP_PROJECT nor GOOGLE_CLOUD_PROJECT is set."""
    env = {"GCP_PROJECT": "", "GOOGLE_CLOUD_PROJECT": "", "GEMINI" + "_API_KEY": ""}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(ValueError, match="GCP_PROJECT or GOOGLE_CLOUD_PROJECT is not configured"):
            get_genai_client()
