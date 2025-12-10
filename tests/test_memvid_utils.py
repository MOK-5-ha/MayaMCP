#!/usr/bin/env python3
"""
Simplified unit tests for src.memvid.utils module.
Focus on functions that can be reliably tested.
"""

import pytest
from unittest.mock import patch, MagicMock
import json
import base64
import gzip

from src.memvid.utils import chunk_text


class TestChunkText:
    """Test cases for chunk_text function - the core utility that doesn't require external dependencies."""

    def test_chunk_text_short_text_single_chunk(self):
        """Test chunk_text with short text that fits in one chunk."""
        text = "This is a short text."
        chunks = chunk_text(text, chunk_size=100, overlap=10)

        assert len(chunks) == 1
        assert chunks[0] == "This is a short text."

    def test_chunk_text_exact_chunk_size(self):
        """Test chunk_text with text that is exactly chunk_size."""
        text = "x" * 50
        chunks = chunk_text(text, chunk_size=50, overlap=10)

        # With overlap, even exact chunk_size text can create multiple chunks
        # First chunk gets all 50 chars, second chunk gets the overlapping portion
        assert len(chunks) == 2
        assert chunks[0] == text
        assert chunks[1] == "x" * 10  # The overlap portion

    def test_chunk_text_simple_splitting(self):
        """Test chunk_text with simple text splitting."""
        text = "a" * 100
        chunks = chunk_text(text, chunk_size=30, overlap=5)

        # Should have multiple chunks
        assert len(chunks) > 1

        # First chunk should be 30 characters
        assert len(chunks[0]) == 30
        assert chunks[0] == "a" * 30

        # Check overlap is working correctly
        assert len(chunks[1]) == 30
        assert chunks[1] == "a" * 30

    def test_chunk_text_default_parameters(self):
        """Test chunk_text with default parameters."""
        text = "a" * 1000
        chunks = chunk_text(text)

        # Should use default chunk_size=512, overlap=32
        assert len(chunks) > 1
        assert len(chunks[0]) == 512

    def test_chunk_text_custom_parameters(self):
        """Test chunk_text with custom chunk_size and overlap."""
        text = "b" * 200
        chunks = chunk_text(text, chunk_size=50, overlap=10)

        assert len(chunks[0]) == 50
        # Verify chunks are created
        assert len(chunks) >= 4  # 200 chars with 50 chunk size and 10 overlap

    def test_chunk_text_zero_overlap(self):
        """Test chunk_text with zero overlap."""
        text = "c" * 100
        chunks = chunk_text(text, chunk_size=25, overlap=0)

        assert len(chunks) == 4  # 100/25 = 4 chunks
        assert chunks[0] == "c" * 25
        assert chunks[1] == "c" * 25
        assert chunks[2] == "c" * 25
        assert chunks[3] == "c" * 25

    def test_chunk_text_empty_string(self):
        """Test chunk_text with empty string."""
        chunks = chunk_text("", chunk_size=10, overlap=2)
        assert len(chunks) == 0

    def test_chunk_text_whitespace_only(self):
        """Test chunk_text with whitespace-only string."""
        text = "   \n\t  "
        chunks = chunk_text(text, chunk_size=10, overlap=1)
        assert len(chunks) == 1
        assert chunks[0] == ""  # Should be stripped

    def test_chunk_text_strips_whitespace(self):
        """Test chunk_text strips whitespace from chunks."""
        text = "  First chunk.  Second chunk goes here.  "
        chunks = chunk_text(text, chunk_size=15, overlap=2)

        # All chunks should be stripped
        for chunk in chunks:
            assert chunk == chunk.strip()

    def test_chunk_text_reasonable_overlap(self):
        """Test chunk_text with reasonable overlap that won't cause infinite loops."""
        text = "d" * 100
        chunks = chunk_text(text, chunk_size=30, overlap=10)

        # Should have reasonable number of chunks
        assert len(chunks) > 1
        assert len(chunks) < 20  # Shouldn't be too many

        # Each chunk should be reasonable size
        for chunk in chunks[:-1]:  # All but last chunk
            assert len(chunk) <= 30

    def test_chunk_text_overlap_too_large(self):
        """Test chunk_text raises ValueError when overlap >= chunk_size."""
        text = "Some text that doesn't matter much."
        
        # Test overlap == chunk_size
        with pytest.raises(ValueError, match="Overlap must be smaller than chunk size"):
            chunk_text(text, chunk_size=50, overlap=50)

        # Test overlap > chunk_size
        with pytest.raises(ValueError, match="Overlap must be smaller than chunk size"):
            chunk_text(text, chunk_size=50, overlap=51)


class TestDependencyRelatedFunctions:
    """Test cases for functions that depend on external libraries using mocking."""

    @patch('src.memvid.utils.QR_AVAILABLE', True)
    @patch('src.memvid.utils.get_memvid_config')
    @patch('src.memvid.utils.qrcode')
    def test_encode_to_qr_simple_case(self, mock_qrcode, mock_get_config):
        """Test encode_to_qr with simple successful case."""
        from src.memvid.utils import encode_to_qr

        # Setup mocks
        mock_config = {
            "qr": {
                "version": 10,
                "error_correction": "M",
                "box_size": 5,
                "border": 3,
                "fill_color": "black",
                "back_color": "white"
            }
        }
        mock_get_config.return_value = mock_config

        mock_qr_instance = MagicMock()
        mock_image = MagicMock()
        mock_qr_instance.make_image.return_value = mock_image
        mock_qrcode.QRCode.return_value = mock_qr_instance
        mock_qrcode.constants.ERROR_CORRECT_M = "ERROR_CORRECT_M"

        # Test
        result = encode_to_qr("test data")

        # Verify
        assert result == mock_image
        mock_qr_instance.add_data.assert_called_once_with("test data")
        mock_qr_instance.make.assert_called_once_with(fit=True)

    @patch('src.memvid.utils.QR_AVAILABLE', False)
    def test_functions_handle_missing_dependencies_gracefully(self):
        """Test that functions handle missing dependencies gracefully."""
        from src.memvid.utils import encode_to_qr, decode_qr, qr_to_frame, extract_frame
        import numpy as np

        # All should return None when dependencies are missing
        assert decode_qr(np.zeros((10, 10), dtype=np.uint8)) is None
        assert decode_qr("test") is None
        assert qr_to_frame(MagicMock(), (100, 100)) is None
        assert extract_frame("test.mp4", 1) is None

    @patch('src.memvid.utils.QR_AVAILABLE', False)
    def test_check_dependencies_raises_import_error(self):
        """Test that check_dependencies raises ImportError when dependencies missing."""
        from src.memvid.utils import check_dependencies

        with pytest.raises(ImportError, match="Missing dependencies"):
            check_dependencies()

    @patch('src.memvid.utils.QR_AVAILABLE', True)
    def test_check_dependencies_returns_true(self):
        """Test that check_dependencies returns True when dependencies available."""
        from src.memvid.utils import check_dependencies

        assert check_dependencies() is True


class TestUtilityFunctionIntegration:
    """Integration tests for utility functions working together."""

    def test_chunk_text_with_realistic_text(self):
        """Test chunk_text with realistic text content."""
        text = """
        This is a longer piece of text that might be used in a real application.
        It contains multiple sentences and should be chunked appropriately.
        The chunking function should handle this text properly and create
        reasonable chunks that can be processed further.
        """

        chunks = chunk_text(text, chunk_size=100, overlap=20)

        # Should create multiple chunks
        assert len(chunks) >= 2

        # Each chunk should be reasonable
        for chunk in chunks:
            assert len(chunk) <= 100
            assert len(chunk.strip()) > 0  # No empty chunks after stripping

        # Total content should be preserved (accounting for overlap)
        all_text = " ".join(chunks)
        original_words = set(text.split())
        chunked_words = set(all_text.split())

        # Most words should be preserved (allowing for some processing differences)
        preserved_words = len(original_words & chunked_words)
        assert preserved_words >= len(original_words) * 0.8  # At least 80% of words preserved

    def test_chunk_text_preserves_content_integrity(self):
        """Test that chunking preserves content integrity."""
        original_text = "The quick brown fox jumps over the lazy dog. " * 20
        chunks = chunk_text(original_text, chunk_size=50, overlap=5)

        # Should have multiple chunks
        assert len(chunks) > 1

        # When chunks are joined (removing overlap), should contain original content
        unique_content = ""
        for i, chunk in enumerate(chunks):
            if i == 0:
                unique_content += chunk
            else:
                # Remove overlap

                unique_content += chunk[5:]  # Remove overlap from start

        # The unique content should be close to original length
        # (may differ slightly due to sentence boundary handling)
        assert abs(len(unique_content) - len(original_text.strip())) < 50
