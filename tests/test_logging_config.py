#!/usr/bin/env python3
"""
Unit tests for src.config.logging_config module.
"""

import pytest
import logging
from unittest.mock import patch, MagicMock
import os

from src.config.logging_config import setup_logging, get_logger


class TestLoggingConfig:
    """Test cases for logging configuration functions."""

    def setup_method(self):
        """Reset logging state before each test."""
        # Clear any existing handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        logging.root.setLevel(logging.WARNING)

    @patch.dict(os.environ, {}, clear=True)
    @patch('logging.basicConfig')
    def test_setup_logging_default_parameters(self, mock_basic_config):
        """Test setup_logging with default parameters."""
        logger = setup_logging()

        # Verify basicConfig was called with correct defaults
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        assert call_args['level'] == logging.INFO
        assert 'handlers' in call_args
        assert call_args['force'] is True

        # Verify correct logger is returned
        assert logger.name == "mayamcp"
        assert isinstance(logger, logging.Logger)

    @patch.dict(os.environ, {'DEBUG': 'true'})
    @patch('logging.basicConfig')
    def test_setup_logging_debug_env_true(self, mock_basic_config):
        """Test setup_logging with DEBUG environment variable set to true."""
        logger = setup_logging()

        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        assert call_args['level'] == logging.DEBUG
        assert 'handlers' in call_args
        assert call_args['force'] is True

        assert logger.name == "mayamcp"

    @patch.dict(os.environ, {'DEBUG': 'True'})
    @patch('logging.basicConfig')
    def test_setup_logging_debug_env_true_capitalized(self, mock_basic_config):
        """Test setup_logging with DEBUG environment variable set to True (capitalized)."""
        logger = setup_logging()

        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        assert call_args['level'] == logging.DEBUG
        assert 'handlers' in call_args
        assert call_args['force'] is True

        assert logger.name == "mayamcp"

    @patch.dict(os.environ, {'DEBUG': 'false'})
    @patch('logging.basicConfig')
    def test_setup_logging_debug_env_false(self, mock_basic_config):
        """Test setup_logging with DEBUG environment variable set to false."""
        logger = setup_logging()

        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        assert call_args['level'] == logging.INFO
        assert 'handlers' in call_args
        assert call_args['force'] is True

        assert logger.name == "mayamcp"

    @patch.dict(os.environ, {'DEBUG': 'invalid'})
    @patch('logging.basicConfig')
    def test_setup_logging_debug_env_invalid(self, mock_basic_config):
        """Test setup_logging with invalid DEBUG environment variable."""
        logger = setup_logging()

        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        assert call_args['level'] == logging.INFO
        assert 'handlers' in call_args
        assert call_args['force'] is True

        assert logger.name == "mayamcp"

    @patch.dict(os.environ, {}, clear=True)
    @patch('logging.basicConfig')
    def test_setup_logging_custom_level(self, mock_basic_config):
        """Test setup_logging with custom level parameter."""
        logger = setup_logging(level="WARNING")

        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        assert call_args['level'] == logging.WARNING
        assert 'handlers' in call_args
        assert call_args['force'] is True

        assert logger.name == "mayamcp"

    @patch.dict(os.environ, {}, clear=True)
    @patch('logging.basicConfig')
    def test_setup_logging_custom_level_lowercase(self, mock_basic_config):
        """Test setup_logging with custom level parameter in lowercase."""
        logger = setup_logging(level="error")

        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        assert call_args['level'] == logging.ERROR
        assert 'handlers' in call_args
        assert call_args['force'] is True

        assert logger.name == "mayamcp"

    @patch.dict(os.environ, {}, clear=True)
    @patch('logging.basicConfig')
    def test_setup_logging_custom_format(self, mock_basic_config):
        """Test setup_logging with custom format string."""
        custom_format = '%(levelname)s: %(message)s'
        logger = setup_logging(format_string=custom_format)

        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        assert call_args['level'] == logging.INFO
        assert 'handlers' in call_args
        assert call_args['force'] is True

        assert logger.name == "mayamcp"

    @patch.dict(os.environ, {}, clear=True)
    @patch('logging.basicConfig')
    def test_setup_logging_both_custom_parameters(self, mock_basic_config):
        """Test setup_logging with both custom level and format."""
        custom_format = '%(name)s - %(message)s'
        logger = setup_logging(level="CRITICAL", format_string=custom_format)

        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        assert call_args['level'] == logging.CRITICAL
        assert 'handlers' in call_args
        assert call_args['force'] is True

        assert logger.name == "mayamcp"

    @patch.dict(os.environ, {'DEBUG': 'true'})
    @patch('logging.basicConfig')
    def test_setup_logging_explicit_level_overrides_env(self, mock_basic_config):
        """Test that explicit level parameter overrides DEBUG environment variable."""
        logger = setup_logging(level="ERROR")

        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        assert call_args['level'] == logging.ERROR
        assert 'handlers' in call_args
        assert call_args['force'] is True

        assert logger.name == "mayamcp"

    @patch.dict(os.environ, {}, clear=True)
    def test_setup_logging_empty_level_string(self):
        """Test setup_logging with empty level string."""
        # Should raise AttributeError for empty string
        with pytest.raises(AttributeError):
            setup_logging(level="")

    @patch.dict(os.environ, {}, clear=True)
    def test_setup_logging_invalid_level_string(self):
        """Test setup_logging with invalid level string."""
        with pytest.raises(AttributeError):
            setup_logging(level="INVALID_LEVEL")

    @patch.dict(os.environ, {}, clear=True)
    @patch('logging.basicConfig')
    def test_setup_logging_none_format_uses_default(self, mock_basic_config):
        """Test that None format string uses default format."""
        logger = setup_logging(format_string=None)

        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        assert call_args['level'] == logging.INFO
        assert 'handlers' in call_args
        assert call_args['force'] is True

        assert logger.name == "mayamcp"

    @patch.dict(os.environ, {}, clear=True)
    @patch('logging.basicConfig')
    def test_setup_logging_empty_format_string(self, mock_basic_config):
        """Test setup_logging with empty format string."""
        logger = setup_logging(format_string="")

        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args[1]
        assert call_args['level'] == logging.INFO
        assert 'handlers' in call_args
        assert call_args['force'] is True

        assert logger.name == "mayamcp"

    @patch('logging.getLogger')
    def test_get_logger_returns_correct_logger(self, mock_get_logger):
        """Test that get_logger returns logger with correct name."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        result = get_logger("test_module")

        mock_get_logger.assert_called_once_with("test_module")
        assert result == mock_logger

    @patch('logging.getLogger')
    def test_get_logger_with_different_names(self, mock_get_logger):
        """Test get_logger with different module names."""
        mock_logger1 = MagicMock()
        mock_logger2 = MagicMock()
        mock_get_logger.side_effect = [mock_logger1, mock_logger2]

        result1 = get_logger("module1")
        result2 = get_logger("module2")

        assert mock_get_logger.call_count == 2
        mock_get_logger.assert_any_call("module1")
        mock_get_logger.assert_any_call("module2")
        assert result1 == mock_logger1
        assert result2 == mock_logger2

    @patch('logging.getLogger')
    def test_get_logger_with_empty_name(self, mock_get_logger):
        """Test get_logger with empty string name."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        result = get_logger("")

        mock_get_logger.assert_called_once_with("")
        assert result == mock_logger

    @patch('logging.getLogger')
    def test_get_logger_with_special_characters(self, mock_get_logger):
        """Test get_logger with special characters in name."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        special_name = "module.sub-module_123"
        result = get_logger(special_name)

        mock_get_logger.assert_called_once_with(special_name)
        assert result == mock_logger

    @patch.dict(os.environ, {}, clear=True)
    @patch('logging.basicConfig')
    @patch('logging.getLogger')
    def test_setup_logging_calls_logging_functions(self, mock_get_logger, mock_basic_config):
        """Test that setup_logging calls basicConfig and getLogger."""
        mock_logger = MagicMock()
        mock_logger.name = "mayamcp"
        mock_get_logger.return_value = mock_logger

        result = setup_logging()

        mock_basic_config.assert_called_once()
        mock_get_logger.assert_called_once_with("mayamcp")
        assert result == mock_logger
        assert result.name == "mayamcp"
