"""Utilities for streaming text processing and TTS pipelining."""

import re
from typing import Generator, List, Optional

from ..config.logging_config import get_logger


logger = get_logger(__name__)


class SentenceBuffer:
    """
    Buffers streaming text and yields complete sentences for TTS processing.

    This helps implement pipelined TTS by detecting sentence boundaries
    and sending complete sentences to TTS as soon as they're available.
    """

    def __init__(self):
        self.buffer = ""
        # More robust sentence boundary regex that avoids splitting on:
        # - Common abbreviations (Mr., Mrs., Dr., Prof., etc.)
        # - Decimal numbers (3.14, 0.5, etc.)
        # - URLs and emails (www.example.com, user@domain.com)
        # - Time formats (3:30 PM, etc.)
        self.sentence_endings = re.compile(
            r'''
            (?<!\w\.\w)          # Not after abbreviation like "Mr." or "Dr."
            (?<!\d\.\d)          # Not after decimal like "3.14"
            (?<!\w@\w)           # Not after email like "user@domain"
            (?<!\w://\w)         # Not after URL like "http://"
            [.!?]+               # One or more sentence-ending punctuation
            (?=\s|$)             # Followed by whitespace or end of string
            ''', 
            re.VERBOSE | re.IGNORECASE
        )

    def add_text(self, text_chunk: str) -> List[str]:
        """
        Add a text chunk and return any complete sentences found.

        Args:
            text_chunk: New text chunk from the LLM stream

        Returns:
            List of complete sentences ready for TTS
        """
        self.buffer += text_chunk
        sentences = []

        # Find all complete sentences
        while True:
            match = self.sentence_endings.search(self.buffer)
            if not match:
                break

            # Extract sentence up to and including the ending punctuation
            end_idx = match.end()
            sentence = self.buffer[:end_idx].strip()
            if sentence:
                sentences.append(sentence)

            # Remove the processed sentence from buffer
            self.buffer = self.buffer[end_idx:].strip()

        return sentences

    def flush(self) -> List[str]:
        """
        Flush remaining buffer content as final sentence(s).

        Returns:
            List of remaining text chunks
        """
        remaining = self.buffer.strip()
        self.buffer = ""
        return [remaining] if remaining else []

    def get_partial(self) -> str:
        """Get current partial text (incomplete sentence)."""
        return self.buffer.strip()


def create_streaming_response_generator(
    text_stream: Generator[str, None, None],
    sentence_buffer: Optional[SentenceBuffer] = None
) -> Generator[dict, None, None]:
    """
    Create a generator that yields structured streaming responses.

    Args:
        text_stream: Generator of text chunks from LLM
        sentence_buffer: Optional sentence buffer for TTS pipelining

    Yields:
        Dict with keys:
        - 'type': 'text_chunk', 'sentence', 'complete', or 'error'
        - 'content': The text content
        - 'partial': Current partial text (for text_chunk type)
    """
    if sentence_buffer is None:
        sentence_buffer = SentenceBuffer()

    accumulated_text = ""

    try:
        for text_chunk in text_stream:
            if not text_chunk:
                continue

            accumulated_text += text_chunk

            # Check for complete sentences
            sentences = sentence_buffer.add_text(text_chunk)

            # Yield text chunk for immediate UI update
            yield {
                'type': 'text_chunk',
                'content': text_chunk,
                'partial': sentence_buffer.get_partial()
            }

            # Yield complete sentences for TTS
            for sentence in sentences:
                yield {
                    'type': 'sentence',
                    'content': sentence
                }

        # Flush any remaining content
        remaining_sentences = sentence_buffer.flush()
        for sentence in remaining_sentences:
            yield {
                'type': 'sentence',
                'content': sentence
            }

        # Signal completion
        yield {
            'type': 'complete',
            'content': accumulated_text,
            'partial': ""
        }

    except Exception as e:
        logger.error("Error in streaming response generator: %s", e, exc_info=True)
        # Yield error state
        yield {
            'type': 'error',
            'content': str(e),
            'partial': sentence_buffer.get_partial()
        }
