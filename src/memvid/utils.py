"""
Utility functions for Memvid integration
Cherry-picked and simplified from original memvid
"""

import json
import logging
from typing import List, Optional, Tuple, Any, Union
import base64
import gzip

# Import only what we need
try:
    import qrcode
    import cv2
    import numpy as np
    from PIL import Image
    QR_AVAILABLE = True
    ImageType = Image.Image
    ArrayType = np.ndarray
except ImportError as e:
    logging.warning(f"QR/OpenCV dependencies not available: {e}")
    QR_AVAILABLE = False
    # Use Any for type hints when imports fail
    ImageType = Any
    ArrayType = Any

from .config import get_memvid_config

logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if required dependencies are available"""
    if not QR_AVAILABLE:
        raise ImportError("Missing dependencies. Need: pip install qrcode[pil] opencv-python")
    return True

def encode_to_qr(data: str) -> Optional[ImageType]:
    """
    Encode data to QR code image (simplified version)
    """
    if not QR_AVAILABLE:
        logger.error("QR dependencies not available")
        return None
        
    try:
        config = get_memvid_config()["qr"]
        
        # Compress data if it's large
        if len(data) > 100:
            compressed = gzip.compress(data.encode())
            data = base64.b64encode(compressed).decode()
            data = "GZ:" + data
        
        qr = qrcode.QRCode(
            version=config["version"],
            error_correction=getattr(qrcode.constants, f"ERROR_CORRECT_{config['error_correction']}"),
            box_size=config["box_size"],
            border=config["border"],
        )
        
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color=config["fill_color"], back_color=config["back_color"])
        return img
        
    except Exception as e:
        logger.error(f"QR encoding failed: {e}")
        return None

def decode_qr(image: ArrayType) -> Optional[str]:
    """
    Decode QR code from image (simplified version)
    """
    if not QR_AVAILABLE:
        return None
        
    try:
        detector = cv2.QRCodeDetector()
        data, bbox, straight_qrcode = detector.detectAndDecode(image)
        
        if data:
            # Check if data was compressed
            if data.startswith("GZ:"):
                compressed_data = base64.b64decode(data[3:])
                data = gzip.decompress(compressed_data).decode()
            return data
    except Exception as e:
        logger.warning(f"QR decode failed: {e}")
    return None

def qr_to_frame(qr_image: ImageType, frame_size: Tuple[int, int]) -> Optional[ArrayType]:
    """
    Convert QR PIL image to video frame
    """
    if not QR_AVAILABLE:
        return None
        
    try:
        # Resize to fit frame
        qr_image = qr_image.resize(frame_size, Image.Resampling.LANCZOS)
        
        # Convert to RGB
        if qr_image.mode != 'RGB':
            qr_image = qr_image.convert('RGB')
        
        # Convert to numpy array
        img_array = np.array(qr_image, dtype=np.uint8)
        
        # Convert to OpenCV format
        frame = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        return frame
    except Exception as e:
        logger.error(f"Frame conversion failed: {e}")
        return None

def extract_frame(video_path: str, frame_number: int) -> Optional[ArrayType]:
    """
    Extract single frame from video
    """
    if not QR_AVAILABLE:
        return None
        
    try:
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            return frame
    except Exception as e:
        logger.error(f"Frame extraction failed: {e}")
    return None

def chunk_text(text: str, chunk_size: int = 512, overlap: int = 32) -> List[str]:
    """
    Split text into overlapping chunks (simplified)
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            if last_period > chunk_size * 0.8:
                end = start + last_period + 1
                chunk = text[start:end]
        
        chunks.append(chunk.strip())
        start = end - overlap
    
    return chunks