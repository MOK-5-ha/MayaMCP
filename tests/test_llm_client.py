#!/usr/bin/env python3
"""
Unit tests for src.llm.client module.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
import sys
import os


from src.llm.client import (
    configure_genai,
    get_generative_model,
    build_generate_config,
    get_model_name,
    get_langchain_llm_params,
    initialize_llm,
    call_gemini_api
)


class TestLLMClient:
    """Test cases for LLM client functions."""

    @patch('src.llm.client.genai.configure')
    def test_configure_genai(self, mock_configure):
        """Test configure_genai calls genai.configure with API key."""
        api_key = "test_api_key"
        
        configure_genai(api_key)
        
        mock_configure.assert_called_once_with(api_key=api_key)

    @patch('src.llm.client.genai.GenerativeModel')
    def test_get_generative_model(self, mock_generative_model):
        """Test get_generative_model returns GenerativeModel instance."""
        model_name = "gemini-1.5-flash"
        mock_model = MagicMock()
        mock_generative_model.return_value = mock_model
        
        result = get_generative_model(model_name)
        
        mock_generative_model.assert_called_once_with(model_name)
        assert result == mock_model

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
        
        expected = {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 2048
        }
        assert result == expected

    def test_build_generate_config_missing_fields(self):
        """Test build_generate_config handles missing fields."""
        config_dict = {
            "temperature": 0.5,
            "max_output_tokens": 1024
        }
        
        result = build_generate_config(config_dict)
        
        expected = {
            "temperature": 0.5,
            "top_p": None,
            "top_k": None,
            "max_output_tokens": 1024
        }
        assert result == expected

    def test_build_generate_config_empty_dict(self):
        """Test build_generate_config with empty dictionary."""
        result = build_generate_config({})
        
        expected = {
            "temperature": None,
            "top_p": None,
            "top_k": None,
            "max_output_tokens": None
        }
        assert result == expected

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

    @patch('src.llm.client.get_generative_model')
    @patch('src.llm.client.configure_genai')
    @patch('src.llm.client.get_model_name')
    @patch('src.llm.client.build_generate_config')
    def test_call_gemini_api_success(self, mock_build_config, mock_get_model_name, 
                                   mock_configure, mock_get_model):
        """Test call_gemini_api successful call."""
        # Setup mocks
        mock_get_model_name.return_value = "gemini-1.5-flash"
        mock_build_config.return_value = {"temperature": 0.7}
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_get_model.return_value = mock_model
        
        prompt_content = [{"role": "user", "content": "Test prompt"}]
        config = {"temperature": 0.7, "max_output_tokens": 1024}
        api_key = "test_api_key"
        
        result = call_gemini_api(prompt_content, config, api_key)
        
        # Verify calls
        mock_configure.assert_called_once_with(api_key)
        mock_get_model_name.assert_called_once()
        mock_build_config.assert_called_once_with(config)
        mock_get_model.assert_called_once_with("gemini-1.5-flash")
        mock_model.generate_content.assert_called_once_with(
            contents=prompt_content,
            generation_config={"temperature": 0.7}
        )
        
        assert result == mock_response

    @patch('src.llm.client.get_generative_model')
    @patch('src.llm.client.configure_genai')
    @patch('src.llm.client.get_model_name')
    @patch('src.llm.client.build_generate_config')
    def test_call_gemini_api_rate_limit_error(self, mock_build_config, mock_get_model_name,
                                            mock_configure, mock_get_model):
        """Test call_gemini_api handles rate limit error."""
        # Setup mocks
        mock_get_model_name.return_value = "gemini-1.5-flash"
        mock_build_config.return_value = {"temperature": 0.7}
        mock_model = MagicMock()
        
        # Create a custom RateLimitError class for testing
        class MockRateLimitError(Exception):
            pass
        
        rate_limit_error = MockRateLimitError("Rate limit exceeded")
        
        # Mock the GenaiRateLimitError to be our custom error class
        with patch('src.llm.client.GenaiRateLimitError', MockRateLimitError):
            mock_model.generate_content.side_effect = rate_limit_error
            mock_get_model.return_value = mock_model
            
            prompt_content = [{"role": "user", "content": "Test prompt"}]
            config = {"temperature": 0.7}
            api_key = "test_api_key"
            
            with pytest.raises(MockRateLimitError):
                call_gemini_api(prompt_content, config, api_key)

    @patch('src.llm.client.get_generative_model')
    @patch('src.llm.client.configure_genai')
    @patch('src.llm.client.get_model_name')
    @patch('src.llm.client.build_generate_config')
    @patch('src.llm.client.classify_and_log_genai_error')
    def test_call_gemini_api_generic_error(self, mock_classify_error, mock_build_config,
                                         mock_get_model_name, mock_configure, mock_get_model):
        """Test call_gemini_api handles generic errors with classification."""
        # Setup mocks
        mock_get_model_name.return_value = "gemini-1.5-flash"
        mock_build_config.return_value = {"temperature": 0.7}
        mock_model = MagicMock()
        
        generic_error = Exception("Some generic error")
        mock_model.generate_content.side_effect = generic_error
        mock_get_model.return_value = mock_model
        
        prompt_content = [{"role": "user", "content": "Test prompt"}]
        config = {"temperature": 0.7}
        api_key = "test_api_key"
        
        with pytest.raises(Exception, match="Some generic error"):
            call_gemini_api(prompt_content, config, api_key)
        
        # Verify error classification was called (retry decorator means it's called multiple times)
        assert mock_classify_error.call_count >= 1

    @patch('src.llm.client.get_generative_model')
    @patch('src.llm.client.configure_genai')
    @patch('src.llm.client.get_model_name')
    @patch('src.llm.client.build_generate_config')
    def test_call_gemini_api_timeout_error(self, mock_build_config, mock_get_model_name,
                                         mock_configure, mock_get_model):
        """Test call_gemini_api handles timeout errors."""
        # Setup mocks
        mock_get_model_name.return_value = "gemini-1.5-flash"
        mock_build_config.return_value = {"temperature": 0.7}
        mock_model = MagicMock()
        
        timeout_error = TimeoutError("Request timed out")
        mock_model.generate_content.side_effect = timeout_error
        mock_get_model.return_value = mock_model
        
        prompt_content = [{"role": "user", "content": "Test prompt"}]
        config = {"temperature": 0.7}
        api_key = "test_api_key"
        
        with pytest.raises(TimeoutError, match="Request timed out"):
            call_gemini_api(prompt_content, config, api_key)

    @patch('src.llm.client.get_generative_model')
    @patch('src.llm.client.configure_genai')
    @patch('src.llm.client.get_model_name')
    @patch('src.llm.client.build_generate_config')
    def test_call_gemini_api_http_status_codes(self, mock_build_config, mock_get_model_name,
                                              mock_configure, mock_get_model):
        """Test call_gemini_api handles HTTP status code errors."""
        # Setup mocks
        mock_get_model_name.return_value = "gemini-1.5-flash"
        mock_build_config.return_value = {"temperature": 0.7}
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        
        prompt_content = [{"role": "user", "content": "Test prompt"}]
        config = {"temperature": 0.7}
        api_key = "test_api_key"
        
        # Test 429 status code (rate limit)
        rate_limit_error = Exception("Rate limit")
        rate_limit_error.status_code = 429
        mock_model.generate_content.side_effect = rate_limit_error
        
        with pytest.raises(Exception, match="Rate limit"):
            call_gemini_api(prompt_content, config, api_key)
        
        # Test 401 status code (auth error)
        auth_error = Exception("Unauthorized")
        auth_error.status_code = 401
        mock_model.generate_content.side_effect = auth_error
        
        with pytest.raises(Exception, match="Unauthorized"):
            call_gemini_api(prompt_content, config, api_key)

    @patch('src.llm.client.get_generative_model')
    @patch('src.llm.client.configure_genai')
    @patch('src.llm.client.get_model_name')
    @patch('src.llm.client.build_generate_config')
    def test_call_gemini_api_retry_behavior(self, mock_build_config, mock_get_model_name,
                                          mock_configure, mock_get_model):
        """Test call_gemini_api retries on failure."""
        # Setup mocks
        mock_get_model_name.return_value = "gemini-1.5-flash"
        mock_build_config.return_value = {"temperature": 0.7}
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_get_model.return_value = mock_model
        
        # Configure side_effect to fail twice then succeed
        # We use a generic Exception which is caught and reraised by call_gemini_api, triggering retry
        mock_model.generate_content.side_effect = [
            Exception("Fail 1"),
            Exception("Fail 2"),
            mock_response
        ]
        
        # Determine strictness of the call_gemini_api object
        # With tenacity, .retry is an object attached to the wrapper
        original_sleep = call_gemini_api.retry.sleep
        call_gemini_api.retry.sleep = lambda x: None
        
        try:
            prompt_content = [{"role": "user", "content": "Test prompt"}]
            config = {"temperature": 0.7}
            api_key = "test_api_key"
            
            result = call_gemini_api(prompt_content, config, api_key)
            
            # Verify it was called 3 times (2 failures + 1 success)
            assert mock_model.generate_content.call_count == 3
            assert result == mock_response
            
        finally:
            # Restore sleep to avoid side effects on other tests
            call_gemini_api.retry.sleep = original_sleep

    def test_module_imports(self):
        """Test that all necessary modules are imported correctly."""
        # This test verifies imports work without errors
        from src.llm import client
        
        # Check that key dependencies are accessible
        assert hasattr(client, 'genai')
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
        with patch('src.llm.client.get_generative_model') as mock_get_model, \
             patch('src.llm.client.configure_genai'), \
             patch('src.llm.client.get_model_name') as mock_get_model_name, \
             patch('src.llm.client.build_generate_config') as mock_build_config:
            
            mock_get_model_name.return_value = "test-model"
            mock_build_config.return_value = {"temperature": 0.7}
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_model.generate_content.return_value = mock_response
            mock_get_model.return_value = mock_model
            
            call_gemini_api([], {}, "test_key")
            
            # Check debug logging calls
            mock_logger.debug.assert_any_call("Calling Gemini API...")
            mock_logger.debug.assert_any_call("Gemini API call successful.")