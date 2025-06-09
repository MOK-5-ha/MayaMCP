"""Embedding generation for RAG system."""

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional, List
from ..config.logging_config import get_logger

logger = get_logger(__name__)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_embedding(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> Optional[List[float]]:
    """
    Get embedding for a single text using Google Generative AI.
    
    Args:
        text: Text to embed
        task_type: Type of embedding task (RETRIEVAL_DOCUMENT or RETRIEVAL_QUERY)
        
    Returns:
        Embedding vector as list of floats, or None if failed.
    """
    try:
        response = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type=task_type
        )
        
        # Parse the response to extract embedding
        if hasattr(response, 'embedding'):
            return response.embedding
        elif isinstance(response, dict) and 'embedding' in response:
            return response['embedding']
        else:
            logger.warning(f"Unexpected response structure: {type(response)}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting embedding: {e}")
        return None

def get_embeddings_batch(texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[Optional[List[float]]]:
    """
    Get embeddings for multiple texts.
    
    Args:
        texts: List of texts to embed
        task_type: Type of embedding task
        
    Returns:
        List of embedding vectors, with None for failed embeddings.
    """
    embeddings = []
    for text in texts:
        embedding = get_embedding(text, task_type)
        embeddings.append(embedding)
    
    return embeddings