#!/usr/bin/env python3
"""
Unit tests for src.config.api_keys module.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os
import importlib



from src.config.api_keys import (
    get_api_keys,
    get_google_api_key
)


class TestApiKeys:
    """Test cases for API key management functions."""

    @patch('src.config.api_keys.os.getenv')
    def test_get_api_keys_both_present(self, mock_getenv):
        """Test get_api_keys when both keys are present."""
        mock_getenv.side_effect = lambda key: {
            'GEMINI_API_KEY': 'test_google_key',
            'CARTESIA_API_KEY': 'test_cartesia_key'
        }.get(key)
        
        result = get_api_keys()
        
        assert result == {
            'google_api_key': 'test_google_key',
            'cartesia_api_key': 'test_cartesia_key'
        }
        
        # Verify correct environment variable names were checked
        mock_getenv.assert_any_call('GEMINI_API_KEY')
        mock_getenv.assert_any_call('CARTESIA_API_KEY')

    @patch('src.config.api_keys.os.getenv')
    def test_get_api_keys_missing_keys(self, mock_getenv):
        """Test get_api_keys when keys are missing."""
        mock_getenv.return_value = None
        
        result = get_api_keys()
        
        assert result == {
            'google_api_key': None,
            'cartesia_api_key': None
        }

    @patch('src.config.api_keys.os.getenv')
    def test_get_api_keys_partial_keys(self, mock_getenv):
        """Test get_api_keys when only some keys are present."""
        mock_getenv.side_effect = lambda key: {
            'GEMINI_API_KEY': 'test_google_key',
            'CARTESIA_API_KEY': None
        }.get(key)
        
        result = get_api_keys()
        
        assert result == {
            'google_api_key': 'test_google_key',
            'cartesia_api_key': None
        }

    @patch('src.config.api_keys.os.getenv')
    def test_get_api_keys_empty_strings(self, mock_getenv):
        """Test get_api_keys when keys are empty strings."""
        mock_getenv.side_effect = lambda key: {
            'GEMINI_API_KEY': '',
            'CARTESIA_API_KEY': ''
        }.get(key)
        
        result = get_api_keys()
        
        assert result == {
            'google_api_key': '',
            'cartesia_api_key': ''
        }


    @patch('src.config.api_keys.get_api_keys')
    def test_get_google_api_key(self, mock_get_api_keys):
        """Test get_google_api_key function."""
        mock_get_api_keys.return_value = {
            'google_api_key': 'test_google_key',
            'cartesia_api_key': 'test_cartesia_key'
        }
        
        result = get_google_api_key()
        
        assert result == 'test_google_key'
        mock_get_api_keys.assert_called_once()

    @patch('src.config.api_keys.get_api_keys')
    def test_get_google_api_key_none(self, mock_get_api_keys):
        """Test get_google_api_key when key is None."""
        mock_get_api_keys.return_value = {
            'google_api_key': None,
            'cartesia_api_key': 'test_cartesia_key'
        }
        
        result = get_google_api_key()
        
        assert result is None


    @patch('dotenv.load_dotenv')
    def test_load_dotenv_called(self, mock_load_dotenv):
        """Test that load_dotenv is called during module import."""
        import src.config.api_keys
        
        # Reload the module to trigger the import-time load_dotenv call
        importlib.reload(src.config.api_keys)
        
        # Assert that load_dotenv was called once during the reload
        mock_load_dotenv.assert_called_once()

    @patch('src.config.api_keys.os.getenv')
    def test_integration_all_functions(self, mock_getenv):
        """Test integration of all API key functions together."""
        mock_getenv.side_effect = lambda key: {
            'GEMINI_API_KEY': 'integration_google_key',
            'CARTESIA_API_KEY': 'integration_cartesia_key'
        }.get(key)
        
        # Test all functions work together
        api_keys = get_api_keys()
        google_key = get_google_api_key()
        
        assert api_keys['google_api_key'] == 'integration_google_key'
        assert api_keys['cartesia_api_key'] == 'integration_cartesia_key'
        assert google_key == 'integration_google_key'

    @patch('src.config.api_keys.os.getenv')
    def test_whitespace_keys(self, mock_getenv):
        """Test handling of keys with whitespace."""
        mock_getenv.side_effect = lambda key: {
            'GEMINI_API_KEY': '  whitespace_key  ',
            'CARTESIA_API_KEY': '\t\nkey_with_newlines\t\n'
        }.get(key)
        
        result = get_api_keys()
        
        # Keys should be stripped
        assert result['google_api_key'] == 'whitespace_key'
        assert result['cartesia_api_key'] == 'key_with_newlines'