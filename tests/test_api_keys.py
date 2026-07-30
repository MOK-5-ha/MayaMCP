#!/usr/bin/env python3
"""
Unit tests for src.config.api_keys module (GCP Vertex AI Mode).
"""

import importlib
import os
from unittest.mock import patch

import pytest

from src.config.api_keys import (
    configure_provider_env,
    get_api_keys,
    get_gcp_location,
    get_gcp_project,
)


class TestGCPVertexConfig:
    """Test cases for GCP Vertex AI Mode configuration functions."""

    def test_get_gcp_project_precedence(self, monkeypatch):
        """Test GCP_PROJECT takes precedence over GOOGLE_CLOUD_PROJECT."""
        monkeypatch.setenv("GCP_PROJECT", "primary-project")
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "secondary-project")
        assert get_gcp_project() == "primary-project"

    def test_get_gcp_project_fallback(self, monkeypatch):
        """Test fallback to GOOGLE_CLOUD_PROJECT when GCP_PROJECT is unset."""
        monkeypatch.delenv("GCP_PROJECT", raising=False)
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "secondary-project")
        assert get_gcp_project() == "secondary-project"

    def test_get_gcp_project_missing_raises_value_error(self, monkeypatch):
        """Test explicit ValueError is raised when no GCP project ID is configured."""
        monkeypatch.delenv("GCP_PROJECT", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        with pytest.raises(ValueError) as exc_info:
            get_gcp_project()
        assert "GCP_PROJECT or GOOGLE_CLOUD_PROJECT is not configured" in str(exc_info.value)

    def test_get_gcp_location_default(self, monkeypatch):
        """Test get_gcp_location defaults to 'global' when unset."""
        monkeypatch.delenv("GCP_LOCATION", raising=False)
        assert get_gcp_location() == "global"

    def test_get_gcp_location_custom(self, monkeypatch):
        """Test custom GCP_LOCATION."""
        monkeypatch.setenv("GCP_LOCATION", "us-central1")
        assert get_gcp_location() == "us-central1"

    def test_configure_provider_env_purges_stale_keys(self, monkeypatch):
        """Test configure_provider_env purges stale AI Studio keys and sets Vertex AI mode."""
        monkeypatch.setenv("GEMINI_API_KEY", "stale_key")
        monkeypatch.setenv("LLM_API_KEY", "stale_llm_key")
        monkeypatch.setenv("BACKUP_LLM_API_KEY", "stale_backup")
        monkeypatch.setenv("GCP_PROJECT", "my-vertex-project")
        monkeypatch.setenv("CARTESIA_API_KEY", "cartesia_test_key")

        result = configure_provider_env()

        assert "GEMINI_API_KEY" not in os.environ
        assert "LLM_API_KEY" not in os.environ
        assert "BACKUP_LLM_API_KEY" not in os.environ
        assert os.environ["GOOGLE_GENAI_USE_VERTEXAI"] == "true"
        assert os.environ["GEMINI_TIER"] == "paid"
        assert result["gcp_project"] == "my-vertex-project"
        assert result["cartesia_api_key"] == "cartesia_test_key"

    def test_configure_provider_env_missing_project_raises(self, monkeypatch):
        """Test configure_provider_env raises ValueError if project is missing."""
        monkeypatch.delenv("GCP_PROJECT", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        with pytest.raises(ValueError):
            configure_provider_env()

    def test_get_api_keys_legacy_compatibility(self, monkeypatch):
        """Test legacy get_api_keys helper returns GCP project info."""
        monkeypatch.setenv("GCP_PROJECT", "my-vertex-project")
        monkeypatch.setenv("GCP_LOCATION", "global")
        monkeypatch.setenv("CARTESIA_API_KEY", "test_cartesia")

        result = get_api_keys()

        assert result["google_api_key"] is None
        assert result["gcp_project"] == "my-vertex-project"
        assert result["gcp_location"] == "global"
        assert result["cartesia_api_key"] == "test_cartesia"

    @patch('dotenv.load_dotenv')
    def test_load_dotenv_called(self, mock_load_dotenv):
        """Test that load_dotenv is called during module import."""
        import src.config.api_keys
        importlib.reload(src.config.api_keys)
        mock_load_dotenv.assert_called_once()
