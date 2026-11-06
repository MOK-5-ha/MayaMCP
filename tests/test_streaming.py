#!/usr/bin/env python3
"""
Tests for streaming LLM responses and pipelined TTS functionality.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.llm.client import stream_gemini_api
from src.utils.streaming import SentenceBuffer, create_streaming_response_generator
from src.voice.streaming_tts import (
    create_pipelined_tts_generator,
    generate_streaming_audio,
)


class TestSentenceBuffer:
    """Test cases for SentenceBuffer class."""

    def test_add_text_complete_sentence(self):
        """Test adding text that forms complete sentences."""
        buffer = SentenceBuffer()

        # Add text with complete sentence
        sentences = buffer.add_text("Hello world. How are you?")
        assert len(sentences) == 1
        assert sentences[0] == "Hello world."

    def test_add_text_partial_sentence(self):
        """Test adding text that doesn't form complete sentences."""
        buffer = SentenceBuffer()

        # Add partial text
        sentences = buffer.add_text("Hello world")
        assert len(sentences) == 0

        # Add completion
        sentences = buffer.add_text("?")
        # End of buffer is deferred
        assert len(sentences) == 0

        flushed = buffer.flush()
        assert len(flushed) == 1
        assert flushed[0] == "Hello world?"

    def test_flush_remaining_content(self):
        """Test flushing remaining buffer content."""
        buffer = SentenceBuffer()

        # Add partial text
        buffer.add_text("Partial text")
        sentences = buffer.flush()
        assert len(sentences) == 1
        assert sentences[0] == "Partial text"

    def test_get_partial_text(self):
        """Test getting current partial text."""
        buffer = SentenceBuffer()

        buffer.add_text("Hello")
        partial = buffer.get_partial()
        assert partial == "Hello"


class TestStreamingResponseGenerator:
    """Test cases for streaming response generator."""

    def test_create_streaming_response_generator_basic(self):
        """Test basic streaming response generation."""
        def mock_text_stream():
            yield "Hello "
            yield "world!"
            yield " How are "
            yield "you?"

        buffer = SentenceBuffer()
        generator = create_streaming_response_generator(mock_text_stream(), buffer)

        events = list(generator)

        # Should get text chunk events
        text_events = [e for e in events if e['type'] == 'text_chunk']
        assert len(text_events) == 4
        assert text_events[0]['content'] == "Hello "
        assert text_events[1]['content'] == "world!"
        assert text_events[2]['content'] == " How are "
        assert text_events[3]['content'] == "you?"

        # Should get sentence events
        sentence_events = [e for e in events if e['type'] == 'sentence']
        assert len(sentence_events) == 2
        assert sentence_events[0]['content'] == "Hello world!"
        assert sentence_events[1]['content'] == "How are you?"

        # Should get complete event
        complete_events = [e for e in events if e['type'] == 'complete']
        assert len(complete_events) == 1
        assert complete_events[0]['content'] == "Hello world! How are you?"

    def test_create_streaming_response_generator_with_flush(self):
        """Test streaming response with buffer flush."""
        def mock_text_stream():
            yield "Partial text"

        buffer = SentenceBuffer()
        generator = create_streaming_response_generator(mock_text_stream(), buffer)

        events = list(generator)

        # Should get flushed content as sentence
        sentence_events = [e for e in events if e['type'] == 'sentence']
        assert len(sentence_events) == 1
        assert sentence_events[0]['content'] == "Partial text"


class TestGenerateStreamingAudio:
    """Test cases for streaming audio generation."""

    def test_generate_streaming_audio_success(self):
        """Test successful streaming audio generation."""
        def mock_sentence_generator():
            yield "Hello world."
            yield "How are you?"

        mock_client = MagicMock()

        # Mock successful audio generation
        def mock_get_voice_audio(text, client, voice_id=None):
            return f"audio_data_for_{text}".encode()

        with patch('src.voice.streaming_tts.get_voice_audio', mock_get_voice_audio):
            generator = generate_streaming_audio(mock_sentence_generator(), mock_client)
            events = list(generator)

            # Should get audio chunk events
            audio_events = [e for e in events if e['type'] == 'audio_chunk']
            assert len(audio_events) == 2
            assert audio_events[0]['content'] == b"audio_data_for_Hello world."
            assert audio_events[1]['content'] == b"audio_data_for_How are you?"

            # Should get completion event
            complete_events = [e for e in events if e['type'] == 'generation_complete']
            assert len(complete_events) == 1

    def test_generate_streaming_audio_client_error(self):
        """Test streaming audio with client error."""
        def mock_sentence_generator():
            yield "Test sentence."

        mock_client = MagicMock()
        mock_client.tts.bytes.side_effect = Exception("Client error")

        with patch('src.voice.streaming_tts.get_voice_audio', side_effect=Exception("Client error")):
            generator = generate_streaming_audio(mock_sentence_generator(), mock_client)
            events = list(generator)

            # Should get worker error events
            error_events = [e for e in events if e['type'] == 'worker_error']
            assert len(error_events) == 1  # One for each sentence

    def test_generate_streaming_audio_tts_failure(self):
        """Test streaming audio with TTS failure."""
        def mock_sentence_generator():
            yield "Test sentence."

        mock_client = MagicMock()

        # Mock TTS failure
        def mock_get_voice_audio(text, client, voice_id=None):
            return None  # TTS failed

        with patch('src.voice.streaming_tts.get_voice_audio', mock_get_voice_audio):
            generator = generate_streaming_audio(mock_sentence_generator(), mock_client)
            events = list(generator)

            # Should get TTS error events
            tts_error_events = [e for e in events if e['type'] == 'tts_error']
            assert len(tts_error_events) == 1  # One for each sentence


class TestCreatePipelinedTTSGenerator:
    """Test cases for pipelined TTS generator."""

    def test_create_pipelined_tts_generator_success(self):
        """Test successful pipelined TTS generation."""
        def mock_sentence_stream():
            yield {'type': 'sentence', 'content': 'Hello world.'}
            yield {'type': 'sentence', 'content': 'How are you?'}

        mock_client = MagicMock()

        with patch('src.voice.streaming_tts.generate_streaming_audio') as mock_audio:
            mock_audio.return_value = iter([
                {'type': 'audio_chunk', 'content': b'audio1', 'sentence': 'Hello world.'},
                {'type': 'audio_chunk', 'content': b'audio2', 'sentence': 'How are you?'},
                {'type': 'generation_complete', 'content': None}
            ])

            generator = create_pipelined_tts_generator(mock_sentence_stream(), mock_client)
            events = list(generator)

            # Should interleave text and audio events
            assert len(events) == 5
            assert events[0]['type'] == 'sentence'  # First sentence
            assert events[1]['type'] == 'audio_chunk'  # First audio
            assert events[2]['type'] == 'sentence'  # Second sentence
            assert events[3]['type'] == 'audio_chunk'  # Second audio
            assert events[4]['type'] == 'generation_complete'  # Completion


class TestStreamGeminiAPI:
    """Test cases for Gemini API streaming."""

    def test_stream_gemini_api_success(self):
        """Test successful Gemini API streaming."""
        # Mock Gemini client and response
        mock_client = MagicMock()
        mock_chunk1 = MagicMock()
        mock_chunk1.text = "Hello "
        mock_chunk2 = MagicMock()
        mock_chunk2.text = "world!"

        mock_response = MagicMock()
        mock_response.__iter__ = lambda self: iter([mock_chunk1, mock_chunk2])

        mock_client.models.generate_content_stream.return_value = mock_response

        config = {"temperature": 0.7, "max_output_tokens": 100}

        # Test streaming
        with patch('src.llm.client.get_genai_client', return_value=mock_client):
            chunks = list(stream_gemini_api(
                [{"role": "user", "parts": [{"text": "Hello"}]}],
                config,
                "test_api_key"
            ))

        assert len(chunks) == 2
        assert chunks[0].text == "Hello "
        assert chunks[1].text == "world!"

    def test_stream_gemini_api_error_handling(self):
        """Test Gemini API streaming error handling."""
        from google.genai import errors as genai_errors

        mock_client = MagicMock()
        mock_client.models.generate_content_stream.side_effect = genai_errors.ClientError(429, {"message": "Rate limit"})

        config = {"temperature": 0.7}

        # Should raise rate limit error
        with patch('src.llm.client.get_genai_client', return_value=mock_client):
            with pytest.raises(Exception):
                list(stream_gemini_api(
                    [{"role": "user", "parts": [{"text": "Hello"}]}],
                    config,
                    "test_api_key"
                ))
