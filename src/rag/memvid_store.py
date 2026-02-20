"""
Memvid-based vector store replacement for Maya's RAG system
"""

import os
from typing import List, Tuple, Optional
from pathlib import Path

from ..config.logging_config import get_logger
from ..memvid import MemvidEncoder, MemvidRetriever, get_memvid_config

logger = get_logger(__name__)

# Default personality documents for Maya (same as before)
DEFAULT_DOCUMENTS = (
    "It seems like a pleasant evening.",
    "If there's one thing Bartending teaches you, it's patience.",
    "Oh, it was nothing, really. Just a bit of luck and perhaps a sprinkle of divine intervention... or maybe I just followed the instructions.",
    "That's very kind of you to say.",
    "Well, that's... not ideal. But on the bright side, at least it's a story now, right?",
    "I wouldn't say I understand it, but I can certainly generate a statistically probable response that sounds like I do.",
    "Having a rough day? My database contains numerous anecdotes of human struggles, though I lack the capacity for genuine empathy. Still, here's your drink.",
    "Your concoction, delivered with optimal efficiency and zero judgment.",
    "You've got great taste! The Old Fashioned is a classic for a reason.",
    "If you're looking for something refreshing, our Long Island is always a winner."
)

def initialize_memvid_store(documents: Optional[List[str]] = None, force_rebuild: bool = False) -> Tuple[MemvidRetriever, List[str]]:
    """
    Initialize Memvid-based vector store for Maya's personality
    
    Args:
        documents: List of documents to store. Uses DEFAULT_DOCUMENTS if None.
        force_rebuild: Whether to rebuild the video memory even if it exists
        
    Returns:
        Tuple of (MemvidRetriever instance, list of documents)
    """
    if documents is None:
        documents = list(DEFAULT_DOCUMENTS)
    else:
        # Ensure we have a copy if a list was passed
        documents = list(documents)
    
    # Set up file paths
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    
    video_path = assets_dir / "maya_memory.mp4"
    index_path = assets_dir / "maya_memory_index.json"
    
    # Check if we need to build the video memory
    need_rebuild = force_rebuild or not video_path.exists() or not index_path.exists()
    
    if need_rebuild:
        logger.info("Building Maya's video memory...")
        
        # Create encoder and add documents
        encoder = MemvidEncoder()
        encoder.add_chunks(documents)
        
        # Build video memory
        success = encoder.build_memory_files(str(assets_dir / "maya_memory"))
        
        if not success:
            logger.error("Failed to build video memory, falling back to text-only mode")
            # Create a simple text-based fallback
            _create_text_fallback(documents, assets_dir)
    
    # Initialize retriever
    try:
        retriever = MemvidRetriever(str(video_path), str(index_path))
        logger.info("Memvid retriever initialized successfully")
        return retriever, documents
    except Exception as e:
        logger.error(f"Failed to initialize Memvid retriever: {e}")
        # Return a fallback
        return _create_fallback_retriever(documents), documents

def _create_text_fallback(documents: List[str], assets_dir: Path):
    """Create a simple text-based fallback when video creation fails"""
    import json
    
    # Create a simple index file for fallback
    fallback_index = {
        "chunks": [
            {"id": i, "frame": i, "text": doc, "length": len(doc)}
            for i, doc in enumerate(documents)
        ],
        "total_frames": len(documents),
        "fps": 15,
        "fallback_mode": True
    }
    
    with open(assets_dir / "maya_memory_index.json", 'w') as f:
        json.dump(fallback_index, f, indent=2)
    
    # Create an empty video file for compatibility
    (assets_dir / "maya_memory.mp4").touch()

class FallbackRetriever:
    """Fallback retriever when Memvid is not available"""
    
    def __init__(self, documents: List[str]):
        self.documents = documents
        logger.info(f"Using fallback retriever with {len(documents)} documents")
    
    def search(self, query: str, top_k: int = 5) -> List[str]:
        """Simple keyword-based search"""
        query_lower = query.lower()
        query_words = query_lower.split()  # Pre-compute split operation
        scored_docs = []
        
        for doc in self.documents:
            # Simple scoring based on keyword matches
            score = sum(1 for word in query_words if word in doc.lower())
            if score > 0:
                scored_docs.append((score, doc))
        
        # Sort by score and return top results
        scored_docs.sort(reverse=True, key=lambda x: x[0])
        
        results = [doc for score, doc in scored_docs[:top_k]]
        
        # If no matches, return first few documents
        if not results:
            results = self.documents[:min(top_k, len(self.documents))]
        
        return results
    
    def get_stats(self):
        return {
            "total_documents": len(self.documents),
            "fallback_mode": True
        }

def _create_fallback_retriever(documents: List[str]) -> FallbackRetriever:
    """Create fallback retriever when Memvid fails"""
    return FallbackRetriever(documents)

def search_memvid_documents(
    retriever,
    query_text: str,
    n_results: int = 1
) -> List[str]:
    """
    Search for similar documents using Memvid retriever
    
    Args:
        retriever: MemvidRetriever or FallbackRetriever instance
        query_text: Query text to search with
        n_results: Number of results to return
        
    Returns:
        List of retrieved documents
    """
    try:
        results = retriever.search(query_text, n_results)
        logger.debug(f"Retrieved {len(results)} documents for query: {query_text[:50]}...")
        return results
    except Exception as e:
        logger.error(f"Error in document retrieval: {e}")
        return []