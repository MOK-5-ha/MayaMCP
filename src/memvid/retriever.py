"""
Simplified MemvidRetriever for Maya
Retrieves text from video memory using QR code decoding
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import time

from .utils import extract_frame, decode_qr, check_dependencies
from .config import get_memvid_config

logger = logging.getLogger(__name__)

class MemvidRetriever:
    """
    Simplified retriever for Maya's video memory
    """
    
    def __init__(self, video_file: str, index_file: str, config: Optional[Dict[str, Any]] = None):
        self.video_file = str(Path(video_file).absolute())
        self.index_file = str(Path(index_file).absolute())
        self.config = config or get_memvid_config()
        
        # Check dependencies
        try:
            check_dependencies()
            self.dependencies_available = True
        except ImportError as e:
            logger.error(f"Memvid dependencies not available: {e}")
            self.dependencies_available = False
            
        # Load index
        self.index_data = self._load_index()
        self._frame_cache = {}
        
        # Verify index is a dict
        if not isinstance(self.index_data, dict):
            logger.warning(f"Memvid index must be a JSON object: {self.index_file}. Using empty index.")
            self.index_data = {"chunks": [], "total_frames": 0}
        
        # Verify index has data
        if not self.index_data.get("chunks"):
            logger.warning(f"Memvid index invalid or empty: {self.index_file}")
            # Do not raise, allow empty index
            if "chunks" not in self.index_data:
                self.index_data["chunks"] = []
            
        # Verify video
        self._verify_video()
        
        logger.info(f"Initialized retriever with {len(self.index_data['chunks'])} chunks")
    
    def _load_index(self) -> Dict[str, Any]:
        """Load index file"""
        try:
            with open(self.index_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load Memvid index {self.index_file}: {e}. Using empty index.")
            return {"chunks": [], "total_frames": 0}
    
    def _verify_video(self):
        """Verify video file exists and is accessible"""
        if not self.dependencies_available:
            return
            
        try:
            import cv2
            cap = cv2.VideoCapture(self.video_file)
            if not cap.isOpened():
                logger.error(f"Cannot open video file: {self.video_file}")
                return
            
            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            
            logger.info(f"Video verified: {self.total_frames} frames at {self.fps} fps")
        except Exception as e:
            logger.error(f"Video verification failed: {e}")
    
    def search_simple(self, query: str, top_k: int = 5) -> List[str]:
        """
        Simple text-based search (optimized for performance)
        """
        # Preprocess query words once for efficiency
        query_words = [word.lower() for word in query.split() if word.strip()]
        if not query_words:
            return []
        
        results = []
        
        # Score chunks based on keyword overlap with optimized matching
        scored_chunks = []
        for chunk_info in self.index_data["chunks"]:
            chunk_text = chunk_info.get("text", "").lower()
            # Optimized keyword matching score
            matching_words = sum(1 for word in query_words if word in chunk_text)
            if matching_words > 0:
                # Normalize score by query length for better ranking
                normalized_score = matching_words / len(query_words)
                scored_chunks.append((normalized_score, chunk_info))
        
        # Sort by score and return top results
        scored_chunks.sort(reverse=True, key=lambda x: x[0])
        
        for score, chunk_info in scored_chunks[:top_k]:
            # Try to get full text from video
            full_text = self._get_chunk_from_video(chunk_info["frame"])
            if full_text:
                results.append(full_text)
            else:
                # Fallback to index preview
                results.append(chunk_info["text"])
        
        return results
    
    def _get_chunk_from_video(self, frame_number: int) -> Optional[str]:
        """Get chunk text from video frame"""
        if not self.dependencies_available:
            return None
        
        # Check cache
        if frame_number in self._frame_cache:
            return self._frame_cache[frame_number]
        
        try:
            # Extract and decode frame
            frame = extract_frame(self.video_file, frame_number)
            if frame is None:
                return None
            
            decoded_data = decode_qr(frame)
            if decoded_data is None:
                return None
            
            # Parse chunk data
            chunk_data = json.loads(decoded_data)
            text = chunk_data.get("text", "")
            
            # Cache result
            if len(self._frame_cache) < 50:  # Simple cache limit
                self._frame_cache[frame_number] = text
            
            return text
            
        except Exception as e:
            logger.warning(f"Failed to extract chunk from frame {frame_number}: {e}")
            return None
    
    def get_all_chunks(self) -> List[str]:
        """Get all chunks from video memory"""
        results = []
        
        for chunk_info in self.index_data["chunks"]:
            # Try to get full text from video
            full_text = self._get_chunk_from_video(chunk_info["frame"])
            if full_text:
                results.append(full_text)
            else:
                # Fallback to index preview
                results.append(chunk_info["text"])
        
        return results
    
    def get_chunk_by_id(self, chunk_id: int) -> Optional[str]:
        """Get specific chunk by ID"""
        for chunk_info in self.index_data["chunks"]:
            if chunk_info["id"] == chunk_id:
                return self._get_chunk_from_video(chunk_info["frame"])
        return None
    
    def search(self, query: str, top_k: int = 5) -> List[str]:
        """
        Main search interface - uses simple search for now
        """
        start_time = time.time()
        
        results = self.search_simple(query, top_k)
        
        elapsed = time.time() - start_time
        logger.info(f"Search completed in {elapsed:.3f}s for query: '{query[:50]}'")
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics"""
        return {
            "video_file": self.video_file,
            "total_chunks": len(self.index_data["chunks"]),
            "total_frames": self.index_data.get("total_frames", 0),
            "cache_size": len(self._frame_cache),
            "dependencies_available": self.dependencies_available
        }