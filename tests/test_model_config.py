#!/usr/bin/env python3
"""
Unit tests for src.config.model_config module.
"""

import pytest
from unittest.mock import patch, MagicMock
import os

from src.config.model_config import (
    _parse_float_env,
    _parse_int_env,
    get_model_config,
    get_generation_config,
    get_cartesia_config,
    get_known_gemini_models,
    is_valid_gemini_model,
    KNOWN_GEMINI_MODELS
)


class TestParseFloatEnv:
    """Test cases for _parse_float_env function."""

    @patch.dict(os.environ, {'TEST_FLOAT': '3.14'})
    def test_parse_float_env_valid_float(self):
        """Test parsing valid float from environment variable."""
        result = _parse_float_env('TEST_FLOAT', 1.0)
        assert result == 3.14

    @patch.dict(os.environ, {'TEST_FLOAT': '0.0'})
    def test_parse_float_env_zero(self):
        """Test parsing zero float from environment variable."""
        result = _parse_float_env('TEST_FLOAT', 1.0)
        assert result == 0.0

    @patch.dict(os.environ, {'TEST_FLOAT': '-2.5'})
    def test_parse_float_env_negative(self):
        """Test parsing negative float from environment variable."""
        result = _parse_float_env('TEST_FLOAT', 1.0)
        assert result == -2.5

    @patch.dict(os.environ, {'TEST_FLOAT': '42'})
    def test_parse_float_env_integer_string(self):
        """Test parsing integer string as float."""
        result = _parse_float_env('TEST_FLOAT', 1.0)
        assert result == 42.0

    @patch.dict(os.environ, {}, clear=True)
    def test_parse_float_env_missing_variable(self):
        """Test parsing missing environment variable returns default."""
        result = _parse_float_env('MISSING_VAR', 5.5)
        assert result == 5.5

    @patch.dict(os.environ, {'TEST_FLOAT': ''})
    def test_parse_float_env_empty_string(self):
        """Test parsing empty string environment variable returns default."""
        result = _parse_float_env('TEST_FLOAT', 7.7)
        assert result == 7.7

    @patch.dict(os.environ, {'TEST_FLOAT': 'invalid'})
    @patch('src.config.model_config.logger')
    def test_parse_float_env_invalid_value_logs_warning(self, mock_logger):
        """Test parsing invalid float logs warning and returns default."""
        result = _parse_float_env('TEST_FLOAT', 2.0)
        assert result == 2.0
        mock_logger.warning.assert_called_once_with(
            "Invalid TEST_FLOAT value 'invalid', falling back to 2.0"
        )

    @patch.dict(os.environ, {'TEST_FLOAT': 'not_a_number'})
    @patch('src.config.model_config.logger')
    def test_parse_float_env_non_numeric_string(self, mock_logger):
        """Test parsing non-numeric string returns default."""
        result = _parse_float_env('TEST_FLOAT', 3.3)
        assert result == 3.3
        mock_logger.warning.assert_called_once_with(
            "Invalid TEST_FLOAT value 'not_a_number', falling back to 3.3"
        )


class TestParseIntEnv:
    """Test cases for _parse_int_env function."""

    @patch.dict(os.environ, {'TEST_INT': '42'})
    def test_parse_int_env_valid_integer(self):
        """Test parsing valid integer from environment variable."""
        result = _parse_int_env('TEST_INT', 10)
        assert result == 42

    @patch.dict(os.environ, {'TEST_INT': '0'})
    def test_parse_int_env_zero(self):
        """Test parsing zero integer from environment variable."""
        result = _parse_int_env('TEST_INT', 10)
        assert result == 0

    @patch.dict(os.environ, {'TEST_INT': '-5'})
    def test_parse_int_env_negative(self):
        """Test parsing negative integer from environment variable."""
        result = _parse_int_env('TEST_INT', 10)
        assert result == -5

    @patch.dict(os.environ, {}, clear=True)
    def test_parse_int_env_missing_variable(self):
        """Test parsing missing environment variable returns default."""
        result = _parse_int_env('MISSING_VAR', 100)
        assert result == 100

    @patch.dict(os.environ, {'TEST_INT': ''})
    def test_parse_int_env_empty_string(self):
        """Test parsing empty string environment variable returns default."""
        result = _parse_int_env('TEST_INT', 200)
        assert result == 200

    @patch.dict(os.environ, {'TEST_INT': '3.14'})
    @patch('src.config.model_config.logger')
    def test_parse_int_env_float_string_logs_warning(self, mock_logger):
        """Test parsing float string as int logs warning and returns default."""
        result = _parse_int_env('TEST_INT', 50)
        assert result == 50
        mock_logger.warning.assert_called_once_with(
            "Invalid TEST_INT value '3.14', falling back to 50"
        )

    @patch.dict(os.environ, {'TEST_INT': 'invalid'})
    @patch('src.config.model_config.logger')
    def test_parse_int_env_invalid_value_logs_warning(self, mock_logger):
        """Test parsing invalid integer logs warning and returns default."""
        result = _parse_int_env('TEST_INT', 25)
        assert result == 25
        mock_logger.warning.assert_called_once_with(
            "Invalid TEST_INT value 'invalid', falling back to 25"
        )


class TestGetModelConfig:
    """Test cases for get_model_config function."""

    @patch.dict(os.environ, {}, clear=True)
    def test_get_model_config_default_values(self):
        """Test get_model_config with default values."""
        config = get_model_config()

        expected = {
            "model_version": "gemini-3.0-flash",
            "temperature": 0.7,
            "max_output_tokens": 2048,
            "top_p": 0.95,
            "top_k": 1
        }
        assert config == expected

    @patch.dict(os.environ, {
        'GEMINI_MODEL_VERSION': 'gemini-2.5-pro',
        'TEMPERATURE': '0.9',
        'MAX_OUTPUT_TOKENS': '4096'
    })
    def test_get_model_config_custom_env_values(self):
        """Test get_model_config with custom environment values."""
        config = get_model_config()

        expected = {
            "model_version": "gemini-2.5-pro",
            "temperature": 0.9,
            "max_output_tokens": 4096,
            "top_p": 0.95,
            "top_k": 1
        }
        assert config == expected

    @patch.dict(os.environ, {
        'TEMPERATURE': 'invalid',
        'MAX_OUTPUT_TOKENS': 'not_a_number'
    })
    @patch('src.config.model_config.logger')
    def test_get_model_config_invalid_env_values_use_defaults(self, mock_logger):
        """Test get_model_config with invalid env values uses defaults."""
        config = get_model_config()

        expected = {
            "model_version": "gemini-3.0-flash",
            "temperature": 0.7,
            "max_output_tokens": 2048,
            "top_p": 0.95,
            "top_k": 1
        }
        assert config == expected
        assert mock_logger.warning.call_count == 2

    @patch.dict(os.environ, {'GEMINI_MODEL_VERSION': ''})
    def test_get_model_config_empty_model_version(self):
        """Test get_model_config with empty model version returns empty string."""
        config = get_model_config()
        assert config["model_version"] == ""


class TestGetGenerationConfig:
    """Test cases for get_generation_config function."""

    @patch('src.config.model_config.get_model_config')
    def test_get_generation_config_uses_model_config(self, mock_get_model_config):
        """Test that get_generation_config uses values from get_model_config."""
        mock_get_model_config.return_value = {
            "model_version": "test-model",
            "temperature": 0.8,
            "max_output_tokens": 1024,
            "top_p": 0.95,
            "top_k": 1
        }

        config = get_generation_config()

        expected = {
            "temperature": 0.8,
            "top_p": 0.95,
            "top_k": 1,
            "max_output_tokens": 1024
        }
        assert config == expected

    @patch('src.config.model_config.get_model_config')
    def test_get_generation_config_excludes_model_version(self, mock_get_model_config):
        """Test that get_generation_config excludes model_version."""
        mock_get_model_config.return_value = {
            "model_version": "should-not-be-included",
            "temperature": 0.5,
            "max_output_tokens": 512,
            "top_p": 0.95,
            "top_k": 1
        }

        config = get_generation_config()
        assert "model_version" not in config

    @patch.dict(os.environ, {
        'TEMPERATURE': '0.3',
        'MAX_OUTPUT_TOKENS': '8192'
    })
    def test_get_generation_config_integration(self):
        """Test get_generation_config integration with environment variables."""
        config = get_generation_config()

        assert config["temperature"] == 0.3
        assert config["max_output_tokens"] == 8192
        assert config["top_p"] == 0.95
        assert config["top_k"] == 1


class TestGetCartesiaConfig:
    """Test cases for get_cartesia_config function."""

    def test_get_cartesia_config_returns_expected_structure(self):
        """Test that get_cartesia_config returns expected configuration structure."""
        config = get_cartesia_config()

        expected = {
            "voice_id": "6f84f4b8-58a2-430c-8c79-688dad597532",
            "model_id": "sonic-2",
            "language": "en",
            "output_format": {
                "container": "wav",
                "sample_rate": 24000,
                "encoding": "pcm_f32le"
            }
        }
        assert config == expected

    def test_get_cartesia_config_is_immutable(self):
        """Test that get_cartesia_config returns a new dict each time."""
        config1 = get_cartesia_config()
        config2 = get_cartesia_config()

        # Modify one config
        config1["voice_id"] = "different_id"

        # Other config should be unaffected
        assert config2["voice_id"] == "6f84f4b8-58a2-430c-8c79-688dad597532"

    def test_get_cartesia_config_output_format_structure(self):
        """Test the nested output_format structure in cartesia config."""
        config = get_cartesia_config()

        output_format = config["output_format"]
        assert isinstance(output_format, dict)
        assert output_format["container"] == "wav"
        assert output_format["sample_rate"] == 24000
        assert output_format["encoding"] == "pcm_f32le"


class TestGetKnownGeminiModels:
    """Test cases for get_known_gemini_models function."""

    def test_get_known_gemini_models_returns_list(self):
        """Test that get_known_gemini_models returns a list."""
        models = get_known_gemini_models()
        assert isinstance(models, list)

    def test_get_known_gemini_models_contains_expected_models(self):
        """Test that get_known_gemini_models contains expected models."""
        models = get_known_gemini_models()

        expected_models = [
            "gemini-3.0-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-2.0-flash-001",
            "gemini-2.0-flash-exp",
        ]

        for model in expected_models:
            assert model in models

    def test_get_known_gemini_models_is_copy(self):
        """Test that get_known_gemini_models returns a copy, not the original list."""
        models1 = get_known_gemini_models()
        models2 = get_known_gemini_models()

        # Modify one list
        models1.append("new-model")

        # Other list should be unaffected
        assert "new-model" not in models2
        assert len(models2) == len(KNOWN_GEMINI_MODELS)

    def test_get_known_gemini_models_matches_constant(self):
        """Test that get_known_gemini_models matches KNOWN_GEMINI_MODELS constant."""
        models = get_known_gemini_models()
        assert models == KNOWN_GEMINI_MODELS


class TestIsValidGeminiModel:
    """Test cases for is_valid_gemini_model function."""

    def test_is_valid_gemini_model_known_models(self):
        """Test is_valid_gemini_model with known valid models."""
        valid_models = [
            "gemini-3.0-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
        ]

        for model in valid_models:
            assert is_valid_gemini_model(model) is True

    def test_is_valid_gemini_model_unknown_models(self):
        """Test is_valid_gemini_model with unknown models."""
        invalid_models = [
            "unknown-model",
            "gpt-4",
            "claude-3",
            "gemini-invalid",
        ]

        for model in invalid_models:
            assert is_valid_gemini_model(model) is False

    def test_is_valid_gemini_model_empty_string(self):
        """Test is_valid_gemini_model with empty string."""
        assert is_valid_gemini_model("") is False

    def test_is_valid_gemini_model_whitespace(self):
        """Test is_valid_gemini_model with whitespace-only string."""
        assert is_valid_gemini_model("   ") is False

    def test_is_valid_gemini_model_with_whitespace(self):
        """Test is_valid_gemini_model strips whitespace from valid model."""
        # The function calls str().strip() so this should work
        assert is_valid_gemini_model("  gemini-3.0-flash  ") is True

    def test_is_valid_gemini_model_none_input(self):
        """Test is_valid_gemini_model with None input."""
        assert is_valid_gemini_model(None) is False

    def test_is_valid_gemini_model_non_string_input(self):
        """Test is_valid_gemini_model with non-string input."""
        assert is_valid_gemini_model(123) is False
        assert is_valid_gemini_model([]) is False
        assert is_valid_gemini_model({}) is False

    def test_is_valid_gemini_model_case_sensitive(self):
        """Test is_valid_gemini_model is case-sensitive."""
        assert is_valid_gemini_model("GEMINI-2.5-FLASH-LITE") is False
        assert is_valid_gemini_model("Gemini-2.5-Flash-Lite") is False

    def test_is_valid_gemini_model_handles_attribute_error(self):
        """Test is_valid_gemini_model handles AttributeError gracefully."""
        # Object without strip method should trigger AttributeError
        class NoStripObject:
            def __str__(self):
                raise AttributeError("No strip method")

        obj = NoStripObject()
        assert is_valid_gemini_model(obj) is False

    def test_is_valid_gemini_model_handles_type_error(self):
        """Test is_valid_gemini_model handles TypeError gracefully."""
        # Object that can't be converted to string
        class NoStrObject:
            def __str__(self):
                raise TypeError("Cannot convert to string")

        obj = NoStrObject()
        assert is_valid_gemini_model(obj) is False
