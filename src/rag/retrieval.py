"""Document retrieval functions for RAG."""

from typing import List
from .vector_store import search_similar_documents
from ..config.logging_config import get_logger

logger = get_logger(__name__)

def retrieve_relevant_passages(
    index,
    documents: List[str], 
    query_text: str,
    n_results: int = 1
) -> List[str]:
    """
    Retrieve relevant passages from FAISS based on the query.
    
    Args:
        index: FAISS index
        documents: List of documents corresponding to index
        query_text: Query text to search with
        n_results: Number of results to return
        
    Returns:
        List of retrieved documents
    """
    try:
        retrieved_docs = search_similar_documents(
            index=index,
            documents=documents,
            query_text=query_text,
            n_results=n_results
        )
        
        logger.debug(f"Retrieved {len(retrieved_docs)} documents for query: {query_text[:50]}...")
        return retrieved_docs
        
    except Exception as e:
        logger.error(f"Error in document retrieval: {e}")
        return []