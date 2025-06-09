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
        Build video memory using simple image sequence (refactored for reduced complexity)
        """
        if not self._validate_build_prerequisites():
            return False
        
        try:
            video_writer = self._create_video_writer(output_path)
            if video_writer is None:
                return False
            
            index_data = self._initialize_index_data()
            frame_count = self._process_all_chunks(video_writer, index_data)
            
            self._finalize_video_build(video_writer, index_data, frame_count, index_path, output_path)
            return True
            
        except Exception as e:
            logger.error(f"Video creation failed: {e}")
            return False
    
    def _validate_build_prerequisites(self) -> bool:
        """Validate that video building can proceed"""
        if not self.dependencies_available:
            logger.error("Cannot build video - missing dependencies")
            return False
            
        if not self.chunks:
            logger.error("No chunks to encode")
            return False
        
        return True
    
    def _create_video_writer(self, output_path: str):
        """Create and validate video writer"""
        import cv2
        
        video_config = self.config["video"]
        frame_size = (video_config["frame_width"], video_config["frame_height"])
        fps = video_config["fps"]
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(output_path, fourcc, fps, frame_size)
        
        if not video_writer.isOpened():
            logger.error("Failed to create video writer")
            return None
        
        return video_writer
    
    def _initialize_index_data(self) -> Dict[str, Any]:
        """Initialize index data structure"""
        return {
            "chunks": [],
            "total_frames": 0,
            "fps": self.config["video"]["fps"],
            "config": self.config
        }
    
    def _process_all_chunks(self, video_writer, index_data: Dict[str, Any]) -> int:
        """Process all chunks and write to video"""
        frame_count = 0
        frame_size = (self.config["video"]["frame_width"], self.config["video"]["frame_height"])
        
        for i, chunk in enumerate(tqdm(self.chunks, desc="Encoding chunks")):
            if self._process_single_chunk(chunk, i, frame_count, frame_size, video_writer, index_data):
                frame_count += 1
        
        return frame_count
    
    def _process_single_chunk(self, chunk: str, chunk_id: int, frame_count: int, 
                            frame_size: tuple, video_writer, index_data: Dict[str, Any]) -> bool:
        """Process a single chunk and add to video"""
        chunk_data = {
            "id": chunk_id,
            "text": chunk,
            "frame": frame_count
        }
        
        # Encode to QR
        qr_image = encode_to_qr(json.dumps(chunk_data))
        if qr_image is None:
            logger.warning(f"Failed to encode chunk {chunk_id}")
            return False
        
        # Convert to video frame
        frame = qr_to_frame(qr_image, frame_size)
        if frame is None:
            logger.warning(f"Failed to convert chunk {chunk_id} to frame")
            return False
        
        # Write frame to video
        video_writer.write(frame)
        
        # Add to index
        self._add_chunk_to_index(chunk, chunk_id, frame_count, index_data)
        return True
    
    def _add_chunk_to_index(self, chunk: str, chunk_id: int, frame_count: int, index_data: Dict[str, Any]):
        """Add chunk metadata to index"""
        preview_text = chunk[:100] + "..." if len(chunk) > 100 else chunk
        index_data["chunks"].append({
            "id": chunk_id,
            "frame": frame_count,
            "text": preview_text,
            "length": len(chunk)
        })
    
    def _finalize_video_build(self, video_writer, index_data: Dict[str, Any], 
                            frame_count: int, index_path: str, output_path: str):
        """Finalize video creation and save index"""
        video_writer.release()
        index_data["total_frames"] = frame_count
        
        with open(index_path, 'w') as f:
            json.dump(index_data, f, indent=2)
        
        logger.info(f"Successfully created video with {frame_count} frames: {output_path}")
        logger.info(f"Index saved: {index_path}")
    
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