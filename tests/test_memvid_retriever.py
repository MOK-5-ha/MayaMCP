#!/usr/bin/env python3
"""
Unit tests for src.memvid.retriever module.
"""

import pytest
import json
from unittest.mock import patch, MagicMock, Mock, mock_open
from pathlib import Path

from src.memvid.retriever import MemvidRetriever


class TestMemvidRetriever:
    """Test cases for MemvidRetriever class."""

    @pytest.fixture
    def sample_index_data(self):
        """Sample index data for testing."""
        return {
            "chunks": [
                {
                    "id": 0,
                    "frame": 100,
                    "text": "This is the first chunk about bartending basics"
                },
                {
                    "id": 1,
                    "frame": 200,
                    "text": "Second chunk discusses cocktail recipes"
                },
                {
                    "id": 2,
                    "frame": 300,
                    "text": "Third chunk covers customer service skills"
                }
            ],
            "total_frames": 1000
        }

    @pytest.fixture
    def sample_config(self):
        """Sample configuration for testing."""
        return {
            "video_settings": {
                "fps": 30,
                "quality": "high"
            }
        }

    @pytest.fixture
    def mock_retriever_deps(self, sample_index_data):
        """Common mocks for retriever tests (Default: ImportError for dependencies)."""
        with patch('src.memvid.retriever.check_dependencies', side_effect=ImportError()), \
             patch('builtins.open', mock_open(read_data=json.dumps(sample_index_data))), \
             patch('src.memvid.retriever.get_memvid_config', return_value={}), \
             patch('src.memvid.retriever.Path') as mock_path:
            mock_path.return_value.absolute.return_value = "/path/to/file"
            yield

    @pytest.fixture
    def retriever(self, mock_retriever_deps):
        """Initialized MemvidRetriever with mocked dependencies."""
        return MemvidRetriever("video.mp4", "index.json")

    @patch('src.memvid.retriever.check_dependencies')
    @patch('src.memvid.retriever.get_memvid_config')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.memvid.retriever.Path')
    def test_init_success_with_dependencies(self, mock_path, mock_file, mock_get_config, mock_check_deps, sample_index_data, sample_config):
        """Test successful initialization with dependencies available."""
        # Setup mocks
        mock_check_deps.return_value = None
        mock_get_config.return_value = sample_config
        mock_file.return_value.read.return_value = json.dumps(sample_index_data)
        mock_path.return_value.absolute.return_value = "/path/to/file"

        with patch.object(MemvidRetriever, '_verify_video') as mock_verify:
            # Create retriever
            retriever = MemvidRetriever("video.mp4", "index.json")

            # Assertions
            assert retriever.video_file == "/path/to/file"
            assert retriever.index_file == "/path/to/file"
            assert retriever.dependencies_available is True
            assert len(retriever.index_data['chunks']) == 3
            assert retriever._frame_cache == {}
            mock_verify.assert_called_once()

    @patch('src.memvid.retriever.check_dependencies')
    @patch('src.memvid.retriever.get_memvid_config')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.memvid.retriever.Path')
    def test_init_without_dependencies(self, mock_path, mock_file, mock_get_config, mock_check_deps, sample_index_data, sample_config):
        """Test initialization when dependencies are not available."""
        # Setup mocks
        mock_check_deps.side_effect = ImportError("OpenCV not available")
        mock_get_config.return_value = sample_config
        mock_file.return_value.read.return_value = json.dumps(sample_index_data)
        mock_path.return_value.absolute.return_value = "/path/to/file"

        with patch.object(MemvidRetriever, '_verify_video') as mock_verify:
            # Create retriever
            retriever = MemvidRetriever("video.mp4", "index.json")

            # Assertions
            assert retriever.dependencies_available is False
            mock_verify.assert_called_once()

    @patch('src.memvid.retriever.check_dependencies')
    @patch('src.memvid.retriever.get_memvid_config')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.memvid.retriever.Path')
    def test_init_with_custom_config(self, mock_path, mock_file, mock_get_config, mock_check_deps, sample_index_data):
        """Test initialization with custom config."""
        custom_config = {"custom": "settings"}
        mock_check_deps.return_value = None
        mock_file.return_value.read.return_value = json.dumps(sample_index_data)
        mock_path.return_value.absolute.return_value = "/path/to/file"

        with patch.object(MemvidRetriever, '_verify_video'):
            # Create retriever with custom config
            retriever = MemvidRetriever("video.mp4", "index.json", config=custom_config)

            # Should use custom config, not call get_memvid_config
            assert retriever.config == custom_config
            mock_get_config.assert_not_called()

    @patch('src.memvid.retriever.check_dependencies')
    @patch('src.memvid.retriever.get_memvid_config')
    @patch('builtins.open', side_effect=FileNotFoundError("Index file not found"))
    @patch('src.memvid.retriever.Path')
    def test_load_index_file_not_found(self, mock_path, mock_file, mock_get_config, mock_check_deps, sample_config):
        """Test index loading when file doesn't exist."""
        mock_check_deps.return_value = None
        mock_get_config.return_value = sample_config
        mock_path.return_value.absolute.return_value = "/path/to/file"

        with patch.object(MemvidRetriever, '_verify_video'):
            # Create retriever
            retriever = MemvidRetriever("video.mp4", "nonexistent.json")

            # Should have default empty index
            assert retriever.index_data == {"chunks": [], "total_frames": 0}

    @patch('src.memvid.retriever.check_dependencies')
    @patch('src.memvid.retriever.get_memvid_config')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.memvid.retriever.Path')
    def test_load_index_invalid_json(self, mock_path, mock_file, mock_get_config, mock_check_deps, sample_config):
        """Test index loading with invalid JSON."""
        mock_check_deps.return_value = None
        mock_get_config.return_value = sample_config
        mock_file.return_value.read.return_value = "invalid json content"
        mock_path.return_value.absolute.return_value = "/path/to/file"

        with patch.object(MemvidRetriever, '_verify_video'):
            # Create retriever
            retriever = MemvidRetriever("video.mp4", "index.json")

            # Should have default empty index
            assert retriever.index_data == {"chunks": [], "total_frames": 0}

    def test_verify_video_without_dependencies(self, sample_index_data):
        """Test video verification when dependencies not available."""
        with patch('src.memvid.retriever.check_dependencies', side_effect=ImportError()):
            with patch('builtins.open', mock_open(read_data=json.dumps(sample_index_data))):
                with patch('src.memvid.retriever.get_memvid_config', return_value={}):
                    with patch('src.memvid.retriever.Path') as mock_path:
                        mock_path.return_value.absolute.return_value = "/path/to/file"

                        # Should not raise exception
                        retriever = MemvidRetriever("video.mp4", "index.json")
                        assert retriever.dependencies_available is False

    @patch('src.memvid.retriever.check_dependencies')
    @patch('src.memvid.retriever.get_memvid_config')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.memvid.retriever.Path')
    def test_verify_video_success(self, mock_path, mock_file, mock_get_config, mock_check_deps, sample_index_data, sample_config):
        """Test that video verification is called when dependencies are available."""
        # Setup mocks
        mock_check_deps.return_value = None
        mock_get_config.return_value = sample_config
        mock_file.return_value.read.return_value = json.dumps(sample_index_data)
        mock_path.return_value.absolute.return_value = "/path/to/video.mp4"

        with patch.object(MemvidRetriever, '_verify_video') as mock_verify:
            # Create retriever
            retriever = MemvidRetriever("video.mp4", "index.json")

            # Assertions - verify that _verify_video was called
            mock_verify.assert_called_once()
            assert retriever.dependencies_available is True

    @patch('src.memvid.retriever.check_dependencies')
    @patch('src.memvid.retriever.get_memvid_config')
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.memvid.retriever.Path')
    def test_verify_video_with_exception(self, mock_path, mock_file, mock_get_config, mock_check_deps, sample_index_data, sample_config):
        """Test video verification when an exception occurs."""
        # Setup mocks
        mock_check_deps.return_value = None
        mock_get_config.return_value = sample_config
        mock_file.return_value.read.return_value = json.dumps(sample_index_data)
        mock_path.return_value.absolute.return_value = "/path/to/video.mp4"

        # Mock _verify_video to do nothing (simulate error handling internally)
        with patch.object(MemvidRetriever, '_verify_video', return_value=None):
            # Should not crash during initialization
            retriever = MemvidRetriever("video.mp4", "index.json")
            assert retriever.dependencies_available is True

    @pytest.mark.parametrize("query,top_k,expected_count,match_content", [
        ("", 5, 0, None),
        ("   \t\n  ", 5, 0, None),
        ("bartending", 5, 1, "bartending basics"),
        ("chunk", 5, 3, None),
        ("chunk", 2, 2, None),  # Top-k limit
        ("BARTENDING", 5, 1, None),  # Case insensitive
    ])
    def test_search_simple_parametrized(self, query, top_k, expected_count, match_content, retriever):
        """Parametrized tests for search_simple."""
        with patch.object(retriever, '_get_chunk_from_video', return_value=None):
            result = retriever.search_simple(query, top_k=top_k)
            assert len(result) == expected_count
            if match_content:
                assert any(match_content in r for r in result)

    def test_get_chunk_from_video_without_dependencies(self, sample_index_data):
        """Test chunk retrieval when dependencies not available."""
        with patch('src.memvid.retriever.check_dependencies', side_effect=ImportError()):
            with patch('builtins.open', mock_open(read_data=json.dumps(sample_index_data))):
                with patch('src.memvid.retriever.get_memvid_config', return_value={}):
                    with patch('src.memvid.retriever.Path') as mock_path:
                        mock_path.return_value.absolute.return_value = "/path/to/file"

                        retriever = MemvidRetriever("video.mp4", "index.json")
                        result = retriever._get_chunk_from_video(100)
                        assert result is None

    @patch('src.memvid.retriever.extract_frame')
    @patch('src.memvid.retriever.decode_qr')
    def test_get_chunk_from_video_success(self, mock_decode_qr, mock_extract_frame, sample_index_data):
        """Test successful chunk retrieval from video."""
        with patch('src.memvid.retriever.check_dependencies', return_value=None):
            with patch('builtins.open', mock_open(read_data=json.dumps(sample_index_data))):
                with patch('src.memvid.retriever.get_memvid_config', return_value={}):
                    with patch('src.memvid.retriever.Path') as mock_path:
                        mock_path.return_value.absolute.return_value = "/path/to/file"

                        # Setup mocks
                        mock_frame = MagicMock()
                        mock_extract_frame.return_value = mock_frame
                        chunk_data = {"text": "Full chunk text from video"}
                        mock_decode_qr.return_value = json.dumps(chunk_data)

                        with patch.object(MemvidRetriever, '_verify_video'):
                            retriever = MemvidRetriever("video.mp4", "index.json")
                            result = retriever._get_chunk_from_video(100)

                            # Assertions
                            mock_extract_frame.assert_called_once_with("/path/to/file", 100)
                            mock_decode_qr.assert_called_once_with(mock_frame)
                            assert result == "Full chunk text from video"

    def test_get_chunk_from_video_caching(self, sample_index_data):
        """Test that chunk retrieval uses caching."""
        with patch('src.memvid.retriever.check_dependencies', return_value=None):
            with patch('builtins.open', mock_open(read_data=json.dumps(sample_index_data))):
                with patch('src.memvid.retriever.get_memvid_config', return_value={}):
                    with patch('src.memvid.retriever.Path') as mock_path:
                        mock_path.return_value.absolute.return_value = "/path/to/file"

                        with patch.object(MemvidRetriever, '_verify_video'):
                            retriever = MemvidRetriever("video.mp4", "index.json")

                            # Pre-populate cache
                            retriever._frame_cache[100] = "Cached text"

                            # Should return cached value without calling extract/decode
                            result = retriever._get_chunk_from_video(100)
                            assert result == "Cached text"

    def test_get_all_chunks(self, sample_index_data):
        """Test getting all chunks."""
        with patch('src.memvid.retriever.check_dependencies', side_effect=ImportError()):
            with patch('builtins.open', mock_open(read_data=json.dumps(sample_index_data))):
                with patch('src.memvid.retriever.get_memvid_config', return_value={}):
                    with patch('src.memvid.retriever.Path') as mock_path:
                        mock_path.return_value.absolute.return_value = "/path/to/file"

                        retriever = MemvidRetriever("video.mp4", "index.json")

                        with patch.object(retriever, '_get_chunk_from_video', return_value=None):
                            result = retriever.get_all_chunks()
                            # Should return fallback texts from index
                            assert len(result) == 3
                            assert "bartending basics" in result[0]
                            assert "cocktail recipes" in result[1]
                            assert "customer service" in result[2]

    def test_get_chunk_by_id_found(self, sample_index_data):
        """Test getting chunk by ID when it exists."""
        with patch('src.memvid.retriever.check_dependencies', side_effect=ImportError()):
            with patch('builtins.open', mock_open(read_data=json.dumps(sample_index_data))):
                with patch('src.memvid.retriever.get_memvid_config', return_value={}):
                    with patch('src.memvid.retriever.Path') as mock_path:
                        mock_path.return_value.absolute.return_value = "/path/to/file"

                        retriever = MemvidRetriever("video.mp4", "index.json")

                        with patch.object(retriever, '_get_chunk_from_video', return_value="Full chunk text"):
                            result = retriever.get_chunk_by_id(1)
                            assert result == "Full chunk text"

    def test_get_chunk_by_id_not_found(self, sample_index_data):
        """Test getting chunk by ID when it doesn't exist."""
        with patch('src.memvid.retriever.check_dependencies', side_effect=ImportError()):
            with patch('builtins.open', mock_open(read_data=json.dumps(sample_index_data))):
                with patch('src.memvid.retriever.get_memvid_config', return_value={}):
                    with patch('src.memvid.retriever.Path') as mock_path:
                        mock_path.return_value.absolute.return_value = "/path/to/file"

                        retriever = MemvidRetriever("video.mp4", "index.json")

                        result = retriever.get_chunk_by_id(999)  # Non-existent ID
                        assert result is None

    @patch('src.memvid.retriever.time.time')
    def test_search_main_interface(self, mock_time, sample_index_data):
        """Test main search interface with timing."""
        mock_time.side_effect = [0.0, 0.5]  # Start and end times

        with patch('src.memvid.retriever.check_dependencies', side_effect=ImportError()):
            with patch('builtins.open', mock_open(read_data=json.dumps(sample_index_data))):
                with patch('src.memvid.retriever.get_memvid_config', return_value={}):
                    with patch('src.memvid.retriever.Path') as mock_path:
                        mock_path.return_value.absolute.return_value = "/path/to/file"

                        retriever = MemvidRetriever("video.mp4", "index.json")

                        with patch.object(retriever, 'search_simple', return_value=["Result 1"]) as mock_search_simple:
                            result = retriever.search("test query", top_k=3)

                            mock_search_simple.assert_called_once_with("test query", 3)
                            assert result == ["Result 1"]

    def test_get_stats(self, sample_index_data):
        """Test getting retriever statistics."""
        with patch('src.memvid.retriever.check_dependencies', side_effect=ImportError()):
            with patch('builtins.open', mock_open(read_data=json.dumps(sample_index_data))):
                with patch('src.memvid.retriever.get_memvid_config', return_value={}):
                    with patch('src.memvid.retriever.Path') as mock_path:
                        mock_path.return_value.absolute.return_value = "/absolute/path/video.mp4"

                        retriever = MemvidRetriever("video.mp4", "index.json")
                        stats = retriever.get_stats()

                        expected_stats = {
                            "video_file": "/absolute/path/video.mp4",
                            "total_chunks": 3,
                            "total_frames": 1000,
                            "cache_size": 0,
                            "dependencies_available": False
                        }
                        assert stats == expected_stats

    def test_get_stats_with_cache(self, sample_index_data):
        """Test getting stats with populated cache."""
        with patch('src.memvid.retriever.check_dependencies', side_effect=ImportError()):
            with patch('builtins.open', mock_open(read_data=json.dumps(sample_index_data))):
                with patch('src.memvid.retriever.get_memvid_config', return_value={}):
                    with patch('src.memvid.retriever.Path') as mock_path:
                        mock_path.return_value.absolute.return_value = "/path/to/file"

                        retriever = MemvidRetriever("video.mp4", "index.json")
                        # Populate cache
                        retriever._frame_cache = {100: "text1", 200: "text2"}

                        stats = retriever.get_stats()
                        assert stats["cache_size"] == 2

    def test_empty_index_data(self):
        """Test behavior with empty index data."""
        empty_index_data = {"chunks": [], "total_frames": 0}

        with patch('src.memvid.retriever.check_dependencies', side_effect=ImportError()):
            with patch('builtins.open', mock_open(read_data=json.dumps(empty_index_data))):
                with patch('src.memvid.retriever.get_memvid_config', return_value={}):
                    with patch('src.memvid.retriever.Path') as mock_path:
                        mock_path.return_value.absolute.return_value = "/path/to/file"

                        retriever = MemvidRetriever("video.mp4", "index.json")

                        # All operations should handle empty index gracefully
                        assert retriever.search_simple("test") == []
                        assert retriever.get_all_chunks() == []
                        assert retriever.get_chunk_by_id(0) is None

                        stats = retriever.get_stats()
                        assert stats["total_chunks"] == 0
                        assert stats["total_frames"] == 0
