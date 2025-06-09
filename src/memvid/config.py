"""
Configuration for Memvid integration
Simplified from original memvid config
"""

from typing import Dict, Any

# QR Code settings (simplified)
QR_VERSION = 10  # Smaller version for simpler setup
QR_ERROR_CORRECTION = 'M'
QR_BOX_SIZE = 5
QR_BORDER = 3
QR_FILL_COLOR = "black"
QR_BACK_COLOR = "white"

# Chunking settings
DEFAULT_CHUNK_SIZE = 512  # Smaller chunks for Maya's personality docs
DEFAULT_OVERLAP = 32

# Video settings (simplified)
VIDEO_FPS = 15
FRAME_HEIGHT = 256
FRAME_WIDTH = 256

def get_memvid_config() -> Dict[str, Any]:
    """Get Memvid configuration for Maya"""
    return {
        "qr": {
            "version": QR_VERSION,
            "error_correction": QR_ERROR_CORRECTION,
            "box_size": QR_BOX_SIZE,
            "border": QR_BORDER,
            "fill_color": QR_FILL_COLOR,
            "back_color": QR_BACK_COLOR,
        },
        "video": {
            "fps": VIDEO_FPS,
            "frame_height": FRAME_HEIGHT,
            "frame_width": FRAME_WIDTH,
        },
        "chunking": {
            "chunk_size": DEFAULT_CHUNK_SIZE,
            "overlap": DEFAULT_OVERLAP,
        },
        "retrieval": {
            "cache_size": 100,
            "max_workers": 2,  # Conservative for hackathon
        }
    }