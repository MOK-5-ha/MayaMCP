"""
Simplified MemvidEncoder for Maya
Creates video memory from text chunks using QR codes
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from .utils import encode_to_qr, qr_to_frame, chunk_text, check_dependencies
from .config import get_memvid_config

logger = logging.getLogger(__name__)

class MemvidEncoder:
    """
    Simplified MemvidEncoder for Maya's personality documents
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_memvid_config()
        self.chunks = []
        self.chunk_metadata = []
        
        # Check dependencies on initialization
        try:
            check_dependencies()
            self.dependencies_available = True
        except ImportError as e:
            logger.error(f"Memvid dependencies not available: {e}")
            self.dependencies_available = False
    
    def add_chunks(self, chunks: List[str]):
        """Add text chunks to be encoded"""
        self.chunks.extend(chunks)
        logger.info(f"Added {len(chunks)} chunks. Total: {len(self.chunks)}")
    
    def add_text(self, text: str, chunk_size: Optional[int] = None, overlap: Optional[int] = None):
        """Add text and automatically chunk it"""
        chunk_size = chunk_size or self.config["chunking"]["chunk_size"]
        overlap = overlap or self.config["chunking"]["overlap"]
        
        chunks = chunk_text(text, chunk_size, overlap)
        self.add_chunks(chunks)
    
    def build_video_simple(self, output_path: str, index_path: str) -> bool:
        """
        Build video memory using simple image sequence (fallback method)
        """
        if not self.dependencies_available:
            logger.error("Cannot build video - missing dependencies")
            return False
            
        if not self.chunks:
            logger.error("No chunks to encode")
            return False
        
        try:
            import cv2
            
            # Video configuration
            video_config = self.config["video"]
            frame_size = (video_config["frame_width"], video_config["frame_height"])
            fps = video_config["fps"]
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, frame_size)
            
            if not out.isOpened():
                logger.error("Failed to create video writer")
                return False
            
            # Create index data
            index_data = {
                "chunks": [],
                "total_frames": 0,
                "fps": fps,
                "config": self.config
            }
            
            frame_count = 0
            
            # Process each chunk
            for i, chunk in enumerate(tqdm(self.chunks, desc="Encoding chunks")):
                # Create chunk data
                chunk_data = {
                    "id": i,
                    "text": chunk,
                    "frame": frame_count
                }
                
                # Encode to QR
                qr_image = encode_to_qr(json.dumps(chunk_data))
                if qr_image is None:
                    logger.warning(f"Failed to encode chunk {i}")
                    continue
                
                # Convert to video frame
                frame = qr_to_frame(qr_image, frame_size)
                if frame is None:
                    logger.warning(f"Failed to convert chunk {i} to frame")
                    continue
                
                # Write frame to video
                out.write(frame)
                
                # Add to index
                index_data["chunks"].append({
                    "id": i,
                    "frame": frame_count,
                    "text": chunk[:100] + "..." if len(chunk) > 100 else chunk,  # Preview text
                    "length": len(chunk)
                })
                
                frame_count += 1
            
            # Finalize video
            out.release()
            index_data["total_frames"] = frame_count
            
            # Save index
            with open(index_path, 'w') as f:
                json.dump(index_data, f, indent=2)
            
            logger.info(f"Successfully created video with {frame_count} frames: {output_path}")
            logger.info(f"Index saved: {index_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Video creation failed: {e}")
            return False
    
    def build_memory_files(self, base_path: str) -> bool:
        """
        Build video memory and index files for Maya
        """
        if not self.chunks:
            logger.error("No chunks to encode")
            return False
        
        # Create output paths
        video_path = f"{base_path}.mp4"
        index_path = f"{base_path}_index.json"
        
        # Ensure output directory exists
        Path(video_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Try to build video
        success = self.build_video_simple(video_path, index_path)
        
        if success:
            logger.info(f"Maya's video memory created: {video_path}")
        else:
            logger.error("Failed to create Maya's video memory")
        
        return success
    
    def get_stats(self) -> Dict[str, Any]:
        """Get encoder statistics"""
        return {
            "total_chunks": len(self.chunks),
            "dependencies_available": self.dependencies_available,
            "config": self.config
        }