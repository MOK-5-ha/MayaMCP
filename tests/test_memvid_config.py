#!/usr/bin/env python3
"""
Unit tests for src.memvid.config module.
"""

import pytest
from unittest.mock import patch
import copy

from src.memvid.config import (
    get_memvid_config,
    QR_VERSION,
    QR_ERROR_CORRECTION,
    QR_BOX_SIZE,
    QR_BORDER,
    QR_FILL_COLOR,
    QR_BACK_COLOR,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_OVERLAP,
    VIDEO_FPS,
    FRAME_HEIGHT,
    FRAME_WIDTH
)


class TestMemvidConstants:
    """Test cases for memvid configuration constants."""

    def test_qr_constants_have_expected_values(self):
        """Test that QR constants have expected values."""
        assert QR_VERSION == 10
        assert QR_ERROR_CORRECTION == 'M'
        assert QR_BOX_SIZE == 5
        assert QR_BORDER == 3
        assert QR_FILL_COLOR == "black"
        assert QR_BACK_COLOR == "white"

    def test_chunking_constants_have_expected_values(self):
        """Test that chunking constants have expected values."""
        assert DEFAULT_CHUNK_SIZE == 512
        assert DEFAULT_OVERLAP == 32

    def test_video_constants_have_expected_values(self):
        """Test that video constants have expected values."""
        assert VIDEO_FPS == 15
        assert FRAME_HEIGHT == 256
        assert FRAME_WIDTH == 256

    def test_constants_are_correct_types(self):
        """Test that constants have correct types."""
        assert isinstance(QR_VERSION, int)
        assert isinstance(QR_ERROR_CORRECTION, str)
        assert isinstance(QR_BOX_SIZE, int)
        assert isinstance(QR_BORDER, int)
        assert isinstance(QR_FILL_COLOR, str)
        assert isinstance(QR_BACK_COLOR, str)
        assert isinstance(DEFAULT_CHUNK_SIZE, int)
        assert isinstance(DEFAULT_OVERLAP, int)
        assert isinstance(VIDEO_FPS, int)
        assert isinstance(FRAME_HEIGHT, int)
        assert isinstance(FRAME_WIDTH, int)


class TestGetMemvidConfig:
    """Test cases for get_memvid_config function."""

    def test_get_memvid_config_returns_dict(self):
        """Test that get_memvid_config returns a dictionary."""
        config = get_memvid_config()
        assert isinstance(config, dict)

    def test_get_memvid_config_has_expected_top_level_keys(self):
        """Test that config has all expected top-level keys."""
        config = get_memvid_config()
        expected_keys = {"qr", "video", "chunking", "retrieval"}
        assert set(config.keys()) == expected_keys

    def test_get_memvid_config_qr_section(self):
        """Test the QR section of the config."""
        config = get_memvid_config()
        qr_config = config["qr"]

        expected_qr = {
            "version": 10,
            "error_correction": 'M',
            "box_size": 5,
            "border": 3,
            "fill_color": "black",
            "back_color": "white",
        }
        assert qr_config == expected_qr

    def test_get_memvid_config_qr_section_types(self):
        """Test the QR section has correct types."""
        config = get_memvid_config()
        qr_config = config["qr"]

        assert isinstance(qr_config["version"], int)
        assert isinstance(qr_config["error_correction"], str)
        assert isinstance(qr_config["box_size"], int)
        assert isinstance(qr_config["border"], int)
        assert isinstance(qr_config["fill_color"], str)
        assert isinstance(qr_config["back_color"], str)

    def test_get_memvid_config_video_section(self):
        """Test the video section of the config."""
        config = get_memvid_config()
        video_config = config["video"]

        expected_video = {
            "fps": 15,
            "frame_height": 256,
            "frame_width": 256,
        }
        assert video_config == expected_video

    def test_get_memvid_config_video_section_types(self):
        """Test the video section has correct types."""
        config = get_memvid_config()
        video_config = config["video"]

        assert isinstance(video_config["fps"], int)
        assert isinstance(video_config["frame_height"], int)
        assert isinstance(video_config["frame_width"], int)

    def test_get_memvid_config_chunking_section(self):
        """Test the chunking section of the config."""
        config = get_memvid_config()
        chunking_config = config["chunking"]

        expected_chunking = {
            "chunk_size": 512,
            "overlap": 32,
        }
        assert chunking_config == expected_chunking

    def test_get_memvid_config_chunking_section_types(self):
        """Test the chunking section has correct types."""
        config = get_memvid_config()
        chunking_config = config["chunking"]

        assert isinstance(chunking_config["chunk_size"], int)
        assert isinstance(chunking_config["overlap"], int)

    def test_get_memvid_config_retrieval_section(self):
        """Test the retrieval section of the config."""
        config = get_memvid_config()
        retrieval_config = config["retrieval"]

        expected_retrieval = {
            "cache_size": 100,
            "max_workers": 2,
        }
        assert retrieval_config == expected_retrieval

    def test_get_memvid_config_retrieval_section_types(self):
        """Test the retrieval section has correct types."""
        config = get_memvid_config()
        retrieval_config = config["retrieval"]

        assert isinstance(retrieval_config["cache_size"], int)
        assert isinstance(retrieval_config["max_workers"], int)

    def test_get_memvid_config_complete_structure(self):
        """Test the complete structure of the config."""
        config = get_memvid_config()

        expected_config = {
            "qr": {
                "version": 10,
                "error_correction": 'M',
                "box_size": 5,
                "border": 3,
                "fill_color": "black",
                "back_color": "white",
            },
            "video": {
                "fps": 15,
                "frame_height": 256,
                "frame_width": 256,
            },
            "chunking": {
                "chunk_size": 512,
                "overlap": 32,
            },
            "retrieval": {
                "cache_size": 100,
                "max_workers": 2,
            }
        }
        assert config == expected_config

    def test_get_memvid_config_returns_new_dict_each_time(self):
        """Test that get_memvid_config returns a new dict each time."""
        config1 = get_memvid_config()
        config2 = get_memvid_config()

        # Should be equal but not the same object
        assert config1 == config2
        assert config1 is not config2

    def test_get_memvid_config_modifications_dont_affect_original(self):
        """Test that modifying returned config doesn't affect subsequent calls."""
        config1 = get_memvid_config()
        config2 = get_memvid_config()

        # Modify config1
        config1["qr"]["version"] = 999
        config1["video"]["fps"] = 999
        config1["new_key"] = "new_value"

        # config2 should be unaffected
        assert config2["qr"]["version"] == 10
        assert config2["video"]["fps"] == 15
        assert "new_key" not in config2

    def test_get_memvid_config_nested_dict_modification(self):
        """Test that modifying nested dicts doesn't affect subsequent calls."""
        config1 = get_memvid_config()
        config1["qr"]["new_qr_key"] = "new_value"
        config1["video"]["new_video_key"] = "new_value"

        config2 = get_memvid_config()
        assert "new_qr_key" not in config2["qr"]
        assert "new_video_key" not in config2["video"]

    def test_get_memvid_config_uses_constants(self):
        """Test that config values match the module constants."""
        config = get_memvid_config()

        # QR constants
        assert config["qr"]["version"] == QR_VERSION
        assert config["qr"]["error_correction"] == QR_ERROR_CORRECTION
        assert config["qr"]["box_size"] == QR_BOX_SIZE
        assert config["qr"]["border"] == QR_BORDER
        assert config["qr"]["fill_color"] == QR_FILL_COLOR
        assert config["qr"]["back_color"] == QR_BACK_COLOR

        # Chunking constants
        assert config["chunking"]["chunk_size"] == DEFAULT_CHUNK_SIZE
        assert config["chunking"]["overlap"] == DEFAULT_OVERLAP

        # Video constants
        assert config["video"]["fps"] == VIDEO_FPS
        assert config["video"]["frame_height"] == FRAME_HEIGHT
        assert config["video"]["frame_width"] == FRAME_WIDTH

    def test_get_memvid_config_all_values_are_serializable(self):
        """Test that all config values are JSON serializable."""
        import json
        config = get_memvid_config()

        # Should not raise any exceptions
        json_str = json.dumps(config)
        reconstructed = json.loads(json_str)
        assert reconstructed == config

    def test_get_memvid_config_no_none_values(self):
        """Test that config contains no None values."""
        config = get_memvid_config()

        def check_no_none_values(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    assert value is not None, f"None value found at {current_path}"
                    check_no_none_values(value, current_path)
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    current_path = f"{path}[{i}]"
                    assert value is not None, f"None value found at {current_path}"
                    check_no_none_values(value, current_path)

        check_no_none_values(config)

    def test_get_memvid_config_reasonable_values(self):
        """Test that config values are reasonable for their intended use."""
        config = get_memvid_config()

        # QR code values should be positive and reasonable
        assert config["qr"]["version"] > 0
        assert config["qr"]["box_size"] > 0
        assert config["qr"]["border"] >= 0
        assert len(config["qr"]["fill_color"]) > 0
        assert len(config["qr"]["back_color"]) > 0

        # Video values should be positive
        assert config["video"]["fps"] > 0
        assert config["video"]["frame_height"] > 0
        assert config["video"]["frame_width"] > 0

        # Chunking values should be reasonable
        assert config["chunking"]["chunk_size"] > 0
        assert config["chunking"]["overlap"] >= 0
        assert config["chunking"]["overlap"] < config["chunking"]["chunk_size"]

        # Retrieval values should be positive
        assert config["retrieval"]["cache_size"] > 0
        assert config["retrieval"]["max_workers"] > 0

    def test_get_memvid_config_deep_copy_behavior(self):
        """Test that the config behaves like a deep copy."""
        config = get_memvid_config()
        original_qr_version = config["qr"]["version"]

        # Create a deep copy for comparison


        # Modify the nested structure
        config["qr"]["version"] = 999

        # Get a fresh config
        fresh_config = get_memvid_config()

        # Fresh config should not be affected by the modification
        assert fresh_config["qr"]["version"] == original_qr_version
        assert fresh_config["qr"]["version"] != 999
