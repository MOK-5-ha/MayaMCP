"""Utilities for streaming text processing and TTS pipelining."""

import re
from typing import List

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
        # Simple sentence boundary regex - will be filtered with _is_false_boundary
        self.sentence_endings = re.compile(r'[.!?]+(?=\s|$)')
        
        # Common abbreviations that should not be treated as sentence boundaries
        self._abbreviations = {
            'mr', 'mrs', 'dr', 'prof', 'st', 'mt', 'vs', 'etc', 'eg', 'ie',
            'approx', 'lit', 'fig', 'vol', 'no', 'jr', 'sr', 'inc', 'ltd'
        }
    
    def _is_false_boundary(self, text_before: str, text_after: str) -> bool:
        """
        Check if a sentence boundary match is a false positive.
        
        Args:
            text_before: Text before the match
            text_after: Text after the match
            
        Returns:
            True if this should be rejected as a false boundary
        """
        # Check for common abbreviations followed by period
        if text_after and text_after[0] == ' ':
            # Get the word before the period from text_before
            # text_before ends with punctuation, so we need to find the last word
            words = text_before.strip().split()
            if len(words) > 0:
                # Remove punctuation from the last word to get the abbreviation
                last_word_with_punct = words[-1]
                last_word = last_word_with_punct.rstrip('.!?')
                if last_word.lower() in self._abbreviations:
                    return True
        
        return False

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
        search_start = 0
        while True:
            match = self.sentence_endings.search(self.buffer[search_start:])
            if not match:
                break

            # Calculate actual position in buffer
            actual_end = search_start + match.end()
            
            # Extract sentence up to and including the ending punctuation
            sentence = self.buffer[:actual_end].strip()
            
            # Check if this is a false boundary before accepting
            text_before = self.buffer[:actual_end]
            text_after = self.buffer[actual_end:]
            if not self._is_false_boundary(text_before, text_after):
                if sentence:
                    sentences.append(sentence)
                # Update search start and remove processed portion
                self.buffer = self.buffer[actual_end:].strip()
                search_start = 0  # Reset since we modified buffer
            else:
                # False boundary - skip this boundary and continue searching
                search_start = actual_end
                # Continue searching in the same buffer

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
