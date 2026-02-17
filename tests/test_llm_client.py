#!/usr/bin/env python3
"""
Unit tests for src.llm.client module.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.llm.client import (
    build_generate_config,
    call_gemini_api,
    get_genai_client,
    get_langchain_llm_params,
    get_model_name,
    initialize_llm,
)


class TestLLMClient:
    """Test cases for LLM client functions."""

    def test_get_genai_client(self, monkeypatch):
        """Test get_genai_client creates a Client with the API key."""
        # Reset global state before test
        monkeypatch.setattr('src.llm.client._genai_client', None)
        monkeypatch.setattr('src.llm.client._genai_client_key', None)

        mock_client = MagicMock()
        with patch('src.llm.client.genai.Client', return_value=mock_client) as mock_ctor:
            result = get_genai_client("test_api_key")
            mock_ctor.assert_called_once_with(api_key="test_api_key")
            assert result is mock_client

    def test_get_genai_client_singleton(self, monkeypatch):
        """Test get_genai_client returns the same client on repeated calls."""
        monkeypatch.setattr('src.llm.client._genai_client', None)
        monkeypatch.setattr('src.llm.client._genai_client_key', None)

        mock_client = MagicMock()
        with patch('src.llm.client.genai.Client', return_value=mock_client) as mock_ctor:
            c1 = get_genai_client("key1")
            c2 = get_genai_client("key1")
            assert c1 is c2
            mock_ctor.assert_called_once()

    def test_get_genai_client_key_rotation(self, monkeypatch):
        """Test get_genai_client recreates client when key changes."""
        monkeypatch.setattr('src.llm.client._genai_client', None)
        monkeypatch.setattr('src.llm.client._genai_client_key', None)

        mock_client1 = MagicMock()
        mock_client2 = MagicMock()
        with patch('src.llm.client.genai.Client', side_effect=[mock_client1, mock_client2]) as mock_ctor:
            c1 = get_genai_client("key1")
            c2 = get_genai_client("key2")
            assert c1 is mock_client1
            assert c2 is mock_client2
            assert mock_ctor.call_count == 2

    def test_build_generate_config(self):
        """Test build_generate_config maps config dictionary correctly."""
        config_dict = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 2048,
            "extra_field": "should_be_ignored"
        }

        result = build_generate_config(config_dict)

        assert result.temperature == 0.7
        assert result.top_p == 0.9
        assert result.top_k == 40
        assert result.max_output_tokens == 2048

    def test_build_generate_config_missing_fields(self):
        """Test build_generate_config handles missing fields."""
        config_dict = {
            "temperature": 0.5,
            "max_output_tokens": 1024
        }

        result = build_generate_config(config_dict)

        assert result.temperature == 0.5
        assert result.top_p is None
        assert result.top_k is None
        assert result.max_output_tokens == 1024

    def test_build_generate_config_empty_dict(self):
        """Test build_generate_config with empty dictionary."""
        result = build_generate_config({})

        assert result.temperature is None
        assert result.top_p is None
        assert result.top_k is None
        assert result.max_output_tokens is None

    @patch('src.llm.client.get_model_config')
    def test_get_model_name(self, mock_get_model_config):
        """Test get_model_name returns model version from config."""
        mock_get_model_config.return_value = {
            "model_version": "gemini-1.5-pro"
        }

        result = get_model_name()

        assert result == "gemini-1.5-pro"
        mock_get_model_config.assert_called_once()

    @patch('src.llm.client.get_model_config')
    def test_get_langchain_llm_params(self, mock_get_model_config):
        """Test get_langchain_llm_params returns correct parameter dict."""
        mock_get_model_config.return_value = {
            "model_version": "gemini-1.5-flash",
            "temperature": 0.8,
            "top_p": 0.95,
            "top_k": 50,
            "max_output_tokens": 4096
        }

        result = get_langchain_llm_params()

        expected = {
            "model": "gemini-1.5-flash",
            "temperature": 0.8,
            "top_p": 0.95,
            "top_k": 50,
            "max_output_tokens": 4096
        }
        assert result == expected

    @patch('src.llm.client.ChatGoogleGenerativeAI')
    @patch('src.llm.client.get_langchain_llm_params')
    def test_initialize_llm_without_tools(self, mock_get_params, mock_chat_google):
        """Test initialize_llm without tools."""
        mock_params = {
            "model": "gemini-1.5-flash",
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 2048
        }
        mock_get_params.return_value = mock_params
        mock_llm = MagicMock()
        mock_chat_google.return_value = mock_llm

        api_key = "test_api_key"
        result = initialize_llm(api_key)

        mock_chat_google.assert_called_once_with(
            model="gemini-1.5-flash",
            temperature=0.7,
            top_p=0.9,
            top_k=40,
            max_output_tokens=2048,
            google_api_key=api_key
        )
        assert result == mock_llm

    @patch('src.llm.client.ChatGoogleGenerativeAI')
    @patch('src.llm.client.get_langchain_llm_params')
    def test_initialize_llm_with_tools(self, mock_get_params, mock_chat_google):
        """Test initialize_llm with tools."""
        mock_params = {
            "model": "gemini-1.5-flash",
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 2048
        }
        mock_get_params.return_value = mock_params
        mock_llm = MagicMock()
        mock_llm_with_tools = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm_with_tools
        mock_chat_google.return_value = mock_llm

        api_key = "test_api_key"
        tools = [{"name": "tool1"}, {"name": "tool2"}]
        result = initialize_llm(api_key, tools)

        mock_llm.bind_tools.assert_called_once_with(tools)
        assert result == mock_llm_with_tools

    @patch('src.llm.client.ChatGoogleGenerativeAI')
    @patch('src.llm.client.get_langchain_llm_params')
    def test_initialize_llm_exception(self, mock_get_params, mock_chat_google):
        """Test initialize_llm handles exceptions."""
        mock_get_params.side_effect = Exception("Config error")

        api_key = "test_api_key"

        with pytest.raises(Exception, match="Config error"):
            initialize_llm(api_key)

    @patch('src.llm.client.get_genai_client')
    @patch('src.llm.client.get_model_name')
    @patch('src.llm.client.build_generate_config')
    def test_call_gemini_api_success(self, mock_build_config, mock_get_model_name,
                                     mock_get_client):
        """Test call_gemini_api successful call."""
        mock_get_model_name.return_value = "gemini-1.5-flash"
        mock_config = MagicMock()
        mock_build_config.return_value = mock_config
        mock_response = MagicMock()
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        prompt_content = [{"role": "user", "content": "Test prompt"}]
        config = {"temperature": 0.7, "max_output_tokens": 1024}
        api_key = "test_api_key"

        result = call_gemini_api(prompt_content, config, api_key)

        # Verify calls
        mock_get_client.assert_called_once_with(api_key)
        mock_get_model_name.assert_called_once()
        mock_build_config.assert_called_once_with(config)
        mock_client.models.generate_content.assert_called_once_with(
            model="gemini-1.5-flash",
            contents=prompt_content,
            config=mock_config,
        )

        assert result == mock_response

    @patch('src.llm.client.get_genai_client')
    @patch('src.llm.client.get_model_name')
    @patch('src.llm.client.build_generate_config')
    def test_call_gemini_api_rate_limit_error(self, mock_build_config, mock_get_model_name,
                                              mock_get_client):
        """Test call_gemini_api handles rate limit error."""
        mock_get_model_name.return_value = "gemini-1.5-flash"
        mock_build_config.return_value = MagicMock()
        mock_client = MagicMock()

        # Create a custom RateLimitError class for testing
        class MockRateLimitError(Exception):
            pass

        rate_limit_error = MockRateLimitError("Rate limit exceeded")

        with patch('src.llm.client.GenaiRateLimitError', MockRateLimitError):
            mock_client.models.generate_content.side_effect = rate_limit_error
            mock_get_client.return_value = mock_client

            prompt_content = [{"role": "user", "content": "Test prompt"}]
            config = {"temperature": 0.7}
            api_key = "test_api_key"

            with pytest.raises(MockRateLimitError):
                call_gemini_api(prompt_content, config, api_key)

    @patch('src.llm.client.get_genai_client')
    @patch('src.llm.client.get_model_name')
    @patch('src.llm.client.build_generate_config')
    @patch('src.llm.client.classify_and_log_genai_error')
    def test_call_gemini_api_generic_error(self, mock_classify_error, mock_build_config,
                                           mock_get_model_name, mock_get_client):
        """Test call_gemini_api handles generic errors with classification."""
        mock_get_model_name.return_value = "gemini-1.5-flash"
        mock_build_config.return_value = MagicMock()
        mock_client = MagicMock()

        generic_error = Exception("Some generic error")
        mock_client.models.generate_content.side_effect = generic_error
        mock_get_client.return_value = mock_client

        prompt_content = [{"role": "user", "content": "Test prompt"}]
        config = {"temperature": 0.7}
        api_key = "test_api_key"

        with pytest.raises(Exception, match="Some generic error"):
            call_gemini_api(prompt_content, config, api_key)

        # Verify error classification was called (retry decorator means it's called multiple times)
        assert mock_classify_error.call_count >= 1

    @patch('src.llm.client.get_genai_client')
    @patch('src.llm.client.get_model_name')
    @patch('src.llm.client.build_generate_config')
    def test_call_gemini_api_timeout_error(self, mock_build_config, mock_get_model_name,
                                           mock_get_client):
        """Test call_gemini_api handles timeout errors."""
        mock_get_model_name.return_value = "gemini-1.5-flash"
        mock_build_config.return_value = MagicMock()
        mock_client = MagicMock()

        timeout_error = TimeoutError("Request timed out")
        mock_client.models.generate_content.side_effect = timeout_error
        mock_get_client.return_value = mock_client

        prompt_content = [{"role": "user", "content": "Test prompt"}]
        config = {"temperature": 0.7}
        api_key = "test_api_key"

        with pytest.raises(TimeoutError, match="Request timed out"):
            call_gemini_api(prompt_content, config, api_key)

    @patch('src.llm.client.get_genai_client')
    @patch('src.llm.client.get_model_name')
    @patch('src.llm.client.build_generate_config')
    def test_call_gemini_api_http_status_codes(self, mock_build_config, mock_get_model_name,
                                                mock_get_client):
        """Test call_gemini_api handles HTTP status code errors."""
        mock_get_model_name.return_value = "gemini-1.5-flash"
        mock_build_config.return_value = MagicMock()
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        prompt_content = [{"role": "user", "content": "Test prompt"}]
        config = {"temperature": 0.7}
        api_key = "test_api_key"

        # Test 429 status code (rate limit)
        rate_limit_error = Exception("Rate limit")
        rate_limit_error.status_code = 429
        mock_client.models.generate_content.side_effect = rate_limit_error

        with pytest.raises(Exception, match="Rate limit"):
            call_gemini_api(prompt_content, config, api_key)

        # Test 401 status code (auth error)
        auth_error = Exception("Unauthorized")
        auth_error.status_code = 401
        mock_client.models.generate_content.side_effect = auth_error

        with pytest.raises(Exception, match="Unauthorized"):
            call_gemini_api(prompt_content, config, api_key)

    @patch('src.llm.client.get_genai_client')
    @patch('src.llm.client.get_model_name')
    @patch('src.llm.client.build_generate_config')
    def test_call_gemini_api_retry_behavior(self, mock_build_config, mock_get_model_name,
                                            mock_get_client):
        """Test call_gemini_api retries on failure."""
        mock_get_model_name.return_value = "gemini-1.5-flash"
        mock_build_config.return_value = MagicMock()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_get_client.return_value = mock_client

        # Configure side_effect to fail twice then succeed
        mock_client.models.generate_content.side_effect = [
            Exception("Fail 1"),
            Exception("Fail 2"),
            mock_response
        ]

        original_sleep = call_gemini_api.retry.sleep
        call_gemini_api.retry.sleep = lambda x: None

        try:
            prompt_content = [{"role": "user", "content": "Test prompt"}]
            config = {"temperature": 0.7}
            api_key = "test_api_key"

            result = call_gemini_api(prompt_content, config, api_key)

            # Verify it was called 3 times (2 failures + 1 success)
            assert mock_client.models.generate_content.call_count == 3
            assert result == mock_response

        finally:
            call_gemini_api.retry.sleep = original_sleep

    def test_module_imports(self):
        """Test that all necessary modules are imported correctly."""
        from src.llm import client

        assert hasattr(client, 'get_genai_client')
        assert hasattr(client, 'ChatGoogleGenerativeAI')
        assert hasattr(client, 'logger')

    @patch('src.llm.client.logger')
    def test_logging_in_initialize_llm(self, mock_logger):
        """Test logging calls in initialize_llm."""
        with patch('src.llm.client.ChatGoogleGenerativeAI') as mock_chat_google, \
             patch('src.llm.client.get_langchain_llm_params') as mock_get_params:

            mock_params = {"model": "test", "temperature": 0.7, "top_p": 0.9,
                          "top_k": 40, "max_output_tokens": 2048}
            mock_get_params.return_value = mock_params
            mock_llm = MagicMock()
            mock_chat_google.return_value = mock_llm

            # Test without tools
            initialize_llm("test_key")
            mock_logger.info.assert_called_with(
                "Successfully initialized LangChain ChatGoogleGenerativeAI model without tools."
            )

            # Test with tools
            mock_logger.reset_mock()
            mock_llm_with_tools = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm_with_tools

            tools = [{"name": "test_tool"}]
            initialize_llm("test_key", tools)
            mock_logger.info.assert_called_with(
                "Successfully initialized LangChain ChatGoogleGenerativeAI model bound with 1 tool."
            )

    @patch('src.llm.client.logger')
    def test_logging_in_call_gemini_api(self, mock_logger):
        """Test logging calls in call_gemini_api."""
        with patch('src.llm.client.get_genai_client') as mock_get_client, \
             patch('src.llm.client.get_model_name') as mock_get_model_name, \
             patch('src.llm.client.build_generate_config') as mock_build_config:

            mock_get_model_name.return_value = "test-model"
            mock_build_config.return_value = MagicMock()
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_get_client.return_value = mock_client

            call_gemini_api([], {}, "test_key")

            # Check debug logging calls
            mock_logger.debug.assert_any_call("Calling Gemini API...")
            mock_logger.debug.assert_any_call("Gemini API call successful.")
