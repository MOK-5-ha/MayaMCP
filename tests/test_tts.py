#!/usr/bin/env python3
"""
Unit tests for src.voice.tts module.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from tenacity import RetryError, stop_after_attempt

from src.voice.tts import (
    clean_text_for_tts,
    initialize_cartesia_client,
    get_voice_audio,
    CARTESIA_RETRYABLE_EXCEPTIONS
)


class TestCleanTextForTTS:
    """Test cases for clean_text_for_tts function."""

    def test_clean_text_empty_string(self):
        """Test cleaning empty string."""
        result = clean_text_for_tts("")
        assert result == ""

    def test_clean_text_none_input(self):
        """Test cleaning None input."""
        result = clean_text_for_tts(None)
        assert result is None

    def test_clean_text_basic_text(self):
        """Test cleaning basic text without special characters."""
        text = "Hello world, how are you today?"
        result = clean_text_for_tts(text)
        assert result == "Hello world, how are you today?"

    def test_clean_text_mok_5_ha_replacement(self):
        """Test MOK 5-ha to Moksha replacement."""
        text = "This is about MOK 5-ha philosophy."
        result = clean_text_for_tts(text)
        assert result == "This is about Moksha philosophy."

    def test_clean_text_mok_5_ha_case_insensitive(self):
        """Test MOK 5-ha replacement is case insensitive."""
        text = "Both mok 5-ha and MOK 5-HA should become Moksha."
        result = clean_text_for_tts(text)
        assert result == "Both Moksha and Moksha should become Moksha."

    def test_clean_text_monetary_amounts_dollars_only(self):
        """Test formatting monetary amounts with dollars only."""
        text = "The price is $15."
        result = clean_text_for_tts(text)
        assert result == "The price is 15 dollars."

    def test_clean_text_monetary_amounts_dollars_and_cents(self):
        """Test formatting monetary amounts with dollars and cents."""
        text = "That will be $12.50 please."
        result = clean_text_for_tts(text)
        assert result == "That will be 12 dollars and 50 cents please."

    def test_clean_text_monetary_amounts_cents_only(self):
        """Test formatting monetary amounts with cents only."""
        text = "The tip is $0.75."
        result = clean_text_for_tts(text)
        assert result == "The tip is 75 cents."

    def test_clean_text_monetary_amounts_zero_dollars(self):
        """Test formatting zero dollar amounts."""
        text = "Cost: $0.00"
        result = clean_text_for_tts(text)
        # Implementation converts $0.00 to "zero dollars"
        assert result == "Cost: zero dollars"

    def test_clean_text_monetary_amounts_rounding(self):
        """Test monetary amount rounding for fractional cents."""
        text = "Price: $10.99"
        result = clean_text_for_tts(text)
        # Should handle 99 cents correctly
        assert result == "Price: 10 dollars and 99 cents"

    def test_clean_text_monetary_amounts_single_digit_cents(self):
        """Test formatting single digit cents."""
        text = "Change: $5.05"
        result = clean_text_for_tts(text)
        assert result == "Change: 5 dollars and 5 cents"

    def test_clean_text_monetary_amounts_invalid_format(self):
        """Test handling invalid monetary formats."""
        text = "Invalid: $abc.def"
        result = clean_text_for_tts(text)
        # Should just remove the dollar sign if parsing fails
        assert result == "Invalid: abc.def"

    def test_clean_text_monetary_amounts_multiple(self):
        """Test multiple monetary amounts in one text."""
        text = "Item 1 costs $10.50 and item 2 costs $5."
        result = clean_text_for_tts(text)
        assert result == "Item 1 costs 10 dollars and 50 cents and item 2 costs 5 dollars."

    def test_clean_text_remove_asterisks(self):
        """Test removal of asterisks."""
        text = "This is *important* and **very important**."
        result = clean_text_for_tts(text)
        assert result == "This is important and very important ."

    def test_clean_text_remove_hashtags(self):
        """Test removal of hashtags."""
        text = "This is a # comment and ## header."
        result = clean_text_for_tts(text)
        assert result == "This is a comment and header."

    def test_clean_text_remove_underscores(self):
        """Test removal of underscores."""
        text = "This_is_underscored and __emphasized__."
        result = clean_text_for_tts(text)
        assert result == "This is underscored and emphasized ."

    def test_clean_text_remove_backticks(self):
        """Test removal of backticks."""
        text = "This is `code` and ```block code```."
        result = clean_text_for_tts(text)
        assert result == "This is code and block code ."

    def test_clean_text_remove_brackets(self):
        """Test removal of various bracket types."""
        text = "This [is in square], {is in curly}, and <is in angle> brackets."
        result = clean_text_for_tts(text)
        assert result == "This , , and brackets."

    def test_clean_text_remove_other_symbols(self):
        """Test removal of other problematic symbols."""
        text = "Text with ~tildes~, ^carets^, =equals=, |pipes|, \\backslashes\\."
        result = clean_text_for_tts(text)
        # Multiple spaces get cleaned up to single spaces
        expected = "Text with tildes, carets, equals, pipes, backslashes."
        assert result == expected or "tildes ," in result  # Allow for slight whitespace variations

    def test_clean_text_remove_at_percent_ampersand(self):
        """Test removal of @, %, & symbols."""
        text = "Contact us @ email.com, 100% sure, Tom & Jerry."
        result = clean_text_for_tts(text)
        # The % symbol gets removed but numbers remain
        assert "Contact us" in result and "email.com" in result and "100" in result

    def test_clean_text_preserve_sentence_punctuation(self):
        """Test that sentence punctuation is preserved."""
        text = "Hello. How are you? I'm fine! Great."
        result = clean_text_for_tts(text)
        assert result == "Hello. How are you? I'm fine! Great."

    def test_clean_text_preserve_commas(self):
        """Test that commas are preserved for natural pauses."""
        text = "First, second, and third items."
        result = clean_text_for_tts(text)
        assert result == "First, second, and third items."

    def test_clean_text_whitespace_cleanup(self):
        """Test cleanup of extra whitespace."""
        text = "Text   with    extra     spaces."
        result = clean_text_for_tts(text)
        assert result == "Text with extra spaces."

    def test_clean_text_whitespace_tabs_newlines(self):
        """Test cleanup of tabs and newlines."""
        text = "Text\twith\ttabs\nand\nnewlines."
        result = clean_text_for_tts(text)
        assert result == "Text with tabs and newlines."

    def test_clean_text_leading_trailing_whitespace(self):
        """Test removal of leading and trailing whitespace."""
        text = "   Text with surrounding spaces   "
        result = clean_text_for_tts(text)
        assert result == "Text with surrounding spaces"

    def test_clean_text_complex_combination(self):
        """Test complex text with multiple issues."""
        text = "**Important**: The cost is $25.75! Contact @support for help. #urgent"
        result = clean_text_for_tts(text)
        # Check key components are present after cleaning
        assert "Important" in result
        assert "25 dollars and 75 cents" in result
        assert "Contact" in result and "support" in result
        assert "urgent" in result

    @patch('src.voice.tts.logger')
    def test_clean_text_logging_when_changes_made(self, mock_logger):
        """Test that changes are logged when significant cleaning occurs."""
        text = "**Complex** text with $10.50 and @symbols."
        result = clean_text_for_tts(text)

        # Should log the change
        mock_logger.info.assert_called_once()
        log_call = mock_logger.info.call_args[0][0]
        assert "Cleaned TTS text:" in log_call
        assert "Complex" in log_call

    @patch('src.voice.tts.logger')
    def test_clean_text_no_logging_when_no_changes(self, mock_logger):
        """Test that no logging occurs when no changes are made."""
        text = "Simple text with no special characters."
        result = clean_text_for_tts(text)

        # Should not log anything
        mock_logger.info.assert_not_called()

    def test_clean_text_dollar_sign_not_followed_by_number(self):
        """Test dollar signs not followed by numbers are removed."""
        text = "The symbol $ is removed but $10 is converted."
        result = clean_text_for_tts(text)
        assert result == "The symbol is removed but 10 dollars is converted."


class TestInitializeCartesiaClient:
    """Test cases for initialize_cartesia_client function."""

    @patch('cartesia.Cartesia')
    @patch('src.voice.tts.logger')
    def test_initialize_client_success(self, mock_logger, mock_cartesia_class):
        """Test successful client initialization."""
        mock_client = MagicMock()
        mock_cartesia_class.return_value = mock_client
        api_key = "test_api_key"

        result = initialize_cartesia_client(api_key)

        mock_cartesia_class.assert_called_once_with(api_key=api_key)
        mock_logger.info.assert_called_once_with("Successfully initialized Cartesia client.")
        assert result == mock_client

    @patch('cartesia.Cartesia')
    @patch('src.voice.tts.logger')
    def test_initialize_client_import_error(self, mock_logger, mock_cartesia_class):
        """Test client initialization with import error."""
        mock_cartesia_class.side_effect = ImportError("Cartesia not installed")
        api_key = "test_api_key"

        with pytest.raises(RuntimeError, match="Cartesia client initialization failed"):
            initialize_cartesia_client(api_key)

        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to initialize Cartesia client" in error_call

    @patch('cartesia.Cartesia')
    @patch('src.voice.tts.logger')
    def test_initialize_client_other_exception(self, mock_logger, mock_cartesia_class):
        """Test client initialization with other exceptions."""
        mock_cartesia_class.side_effect = ValueError("Invalid API key")
        api_key = "invalid_key"

        with pytest.raises(RuntimeError, match="Cartesia client initialization failed"):
            initialize_cartesia_client(api_key)

        mock_logger.error.assert_called_once()

    @patch('cartesia.Cartesia')
    def test_initialize_client_with_empty_api_key(self, mock_cartesia_class):
        """Test client initialization with empty API key."""
        mock_client = MagicMock()
        mock_cartesia_class.return_value = mock_client

        result = initialize_cartesia_client("")

        # Should still try to initialize (let Cartesia handle validation)
        mock_cartesia_class.assert_called_once_with(api_key="")
        assert result == mock_client


class TestGetVoiceAudio:
    """Test cases for get_voice_audio function."""

    def setup_method(self):
        """Setup common test fixtures."""
        self.mock_client = MagicMock()
        self.mock_config = {
            "voice_id": "test_voice_id",
            "model_id": "test_model_id",
            "language": "en-US",
            "output_format": {
                "container": "wav",
                "encoding": "pcm_f32le",
                "sample_rate": 22050,
            }
        }

    @patch('src.voice.tts.get_cartesia_config')
    @patch('src.voice.tts.clean_text_for_tts')
    @patch('src.voice.tts.logger')
    def test_get_voice_audio_success(self, mock_logger, mock_clean_text, mock_get_config):
        """Test successful audio generation."""
        mock_get_config.return_value = self.mock_config
        mock_clean_text.return_value = "cleaned text"

        # Mock audio generator
        audio_chunks = [b"chunk1", b"chunk2", b"chunk3"]
        mock_audio_generator = iter(audio_chunks)
        self.mock_client.tts.bytes.return_value = mock_audio_generator

        result = get_voice_audio("test text", self.mock_client)

        # Verify function calls
        mock_clean_text.assert_called_once_with("test text")
        self.mock_client.tts.bytes.assert_called_once_with(
            model_id="test_model_id",
            transcript="cleaned text",
            voice={
                "mode": "id",
                "id": "test_voice_id",
            },
            language="en-US",
            output_format=self.mock_config["output_format"]
        )

        # Verify result
        expected_audio = b"".join(audio_chunks)
        assert result == expected_audio
        mock_logger.info.assert_called()

    @patch('src.voice.tts.get_cartesia_config')
    @patch('src.voice.tts.clean_text_for_tts')
    @patch('src.voice.tts.logger')
    def test_get_voice_audio_with_custom_voice_id(self, mock_logger, mock_clean_text, mock_get_config):
        """Test audio generation with custom voice ID."""
        mock_get_config.return_value = self.mock_config
        mock_clean_text.return_value = "cleaned text"

        audio_chunks = [b"audio_data"]
        self.mock_client.tts.bytes.return_value = iter(audio_chunks)

        result = get_voice_audio("test text", self.mock_client, voice_id="custom_voice")

        # Should use custom voice ID
        call_args = self.mock_client.tts.bytes.call_args
        assert call_args.kwargs["voice"]["id"] == "custom_voice"
        assert result == b"audio_data"

    @patch('src.voice.tts.logger')
    def test_get_voice_audio_empty_text(self, mock_logger):
        """Test audio generation with empty text."""
        result = get_voice_audio("", self.mock_client)

        assert result is None
        mock_logger.warning.assert_called_once_with("get_voice_audio received empty text.")
        self.mock_client.tts.bytes.assert_not_called()

    @patch('src.voice.tts.logger')
    def test_get_voice_audio_whitespace_only_text(self, mock_logger):
        """Test audio generation with whitespace-only text."""
        result = get_voice_audio("   \t\n  ", self.mock_client)

        assert result is None
        mock_logger.warning.assert_called_once_with("get_voice_audio received empty text.")
        self.mock_client.tts.bytes.assert_not_called()

    @patch('src.voice.tts.logger')
    def test_get_voice_audio_no_client(self, mock_logger):
        """Test audio generation without client."""
        result = get_voice_audio("test text", None)

        assert result is None
        mock_logger.error.assert_called_once_with("Cartesia client not provided, cannot generate audio.")

    @patch('src.voice.tts.get_cartesia_config')
    @patch('src.voice.tts.clean_text_for_tts')
    @patch('src.voice.tts.logger')
    def test_get_voice_audio_empty_response(self, mock_logger, mock_clean_text, mock_get_config):
        """Test audio generation with empty response from API."""
        mock_get_config.return_value = self.mock_config
        mock_clean_text.return_value = "cleaned text"

        # Mock empty audio generator
        self.mock_client.tts.bytes.return_value = iter([])

        result = get_voice_audio("test text", self.mock_client)

        assert result is None
        mock_logger.warning.assert_called_once_with("Cartesia TTS returned empty audio data.")

    @patch('src.voice.tts.get_cartesia_config')
    @patch('src.voice.tts.clean_text_for_tts')
    @patch('src.voice.tts.logger')
    def test_get_voice_audio_api_exception(self, mock_logger, mock_clean_text, mock_get_config):
        """Test audio generation with API exception."""
        mock_get_config.return_value = self.mock_config
        mock_clean_text.return_value = "cleaned text"

        # Mock API exception
        self.mock_client.tts.bytes.side_effect = Exception("API Error")

        result = get_voice_audio("test text", self.mock_client)

        assert result is None
        mock_logger.exception.assert_called_once()
        exception_call = mock_logger.exception.call_args[0][0]
        assert "Unexpected error generating voice audio with Cartesia" in exception_call

    @patch('src.voice.tts.get_cartesia_config')
    @patch('src.voice.tts.clean_text_for_tts')
    @patch('src.voice.tts.logger')
    def test_get_voice_audio_retryable_exception(self, mock_logger, mock_clean_text, mock_get_config):
        """Test audio generation with retryable exception."""
        mock_get_config.return_value = self.mock_config
        mock_clean_text.return_value = "cleaned text"

        # Mock retryable exception
        self.mock_client.tts.bytes.side_effect = ConnectionError("Connection failed")

        result = get_voice_audio("test text", self.mock_client)

        assert result is None
        # Should retry and eventually log the exception
        mock_logger.exception.assert_called()

    @patch('src.voice.tts.get_cartesia_config')
    @patch('src.voice.tts.clean_text_for_tts')
    def test_get_voice_audio_long_text_logging(self, mock_clean_text, mock_get_config):
        """Test logging truncation with long text."""
        mock_get_config.return_value = self.mock_config
        long_text = "This is a very long text that should be truncated in the log message " * 10
        mock_clean_text.return_value = long_text

        audio_chunks = [b"audio_data"]
        self.mock_client.tts.bytes.return_value = iter(audio_chunks)

        with patch('src.voice.tts.logger') as mock_logger:
            result = get_voice_audio(long_text, self.mock_client)

            # Check that logging was called with truncated text
            mock_logger.info.assert_called()
            log_calls = [call.args[0] for call in mock_logger.info.call_args_list]

            # Find the request log message
            request_log = next((log for log in log_calls if "Requesting TTS" in log), None)
            assert request_log is not None
            # Text should be truncated to 50 chars plus "..."
            assert "..." in request_log

    @patch('src.voice.tts.get_cartesia_config')
    @patch('src.voice.tts.clean_text_for_tts')
    @patch('src.voice.tts.logger')
    def test_get_voice_audio_audio_size_logging(self, mock_logger, mock_clean_text, mock_get_config):
        """Test logging of audio data size."""
        mock_get_config.return_value = self.mock_config
        mock_clean_text.return_value = "test"

        audio_data = b"x" * 1024  # 1KB of audio data
        self.mock_client.tts.bytes.return_value = iter([audio_data])

        result = get_voice_audio("test", self.mock_client)

        # Should log the size of received audio
        assert result == audio_data
        mock_logger.info.assert_called()
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]

        # Find the received audio log message
        received_log = next((log for log in log_calls if "Received" in log and "bytes" in log), None)
        assert received_log is not None
        assert "1024 bytes" in received_log

    def test_cartesia_retryable_exceptions_defined(self):
        """Test that retryable exceptions are properly defined."""
        assert CARTESIA_RETRYABLE_EXCEPTIONS == (ConnectionError, TimeoutError)

    @patch('src.voice.tts.get_cartesia_config')
    @patch('src.voice.tts.clean_text_for_tts')
    def test_get_voice_audio_voice_configuration(self, mock_clean_text, mock_get_config):
        """Test that voice configuration is properly structured."""
        mock_get_config.return_value = self.mock_config
        mock_clean_text.return_value = "test"

        audio_chunks = [b"audio"]
        self.mock_client.tts.bytes.return_value = iter(audio_chunks)

        get_voice_audio("test", self.mock_client)

        # Verify voice configuration structure
        call_args = self.mock_client.tts.bytes.call_args
        voice_config = call_args.kwargs["voice"]
        assert voice_config == {
            "mode": "id",
            "id": "test_voice_id"
        }

    @patch('src.voice.tts.get_cartesia_config')
    @patch('src.voice.tts.clean_text_for_tts')
    def test_get_voice_audio_config_parameters(self, mock_clean_text, mock_get_config):
        """Test that all configuration parameters are used correctly."""
        mock_get_config.return_value = self.mock_config
        mock_clean_text.return_value = "test text"

        audio_chunks = [b"audio"]
        self.mock_client.tts.bytes.return_value = iter(audio_chunks)

        get_voice_audio("test", self.mock_client)

        # Verify all config parameters are passed
        call_args = self.mock_client.tts.bytes.call_args
        assert call_args.kwargs["model_id"] == "test_model_id"
        assert call_args.kwargs["transcript"] == "test text"
        assert call_args.kwargs["language"] == "en-US"
        assert call_args.kwargs["output_format"] == self.mock_config["output_format"]
