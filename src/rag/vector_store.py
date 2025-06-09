"""Vector store operations using FAISS."""

import numpy as np
import faiss
from typing import List, Tuple, Optional
from .embeddings import get_embeddings_batch
from ..config.logging_config import get_logger

logger = get_logger(__name__)

# Default personality documents for Maya
DEFAULT_DOCUMENTS = [
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
]

def initialize_vector_store(documents: Optional[List[str]] = None) -> Tuple[faiss.Index, List[str]]:
    """
    Initialize FAISS vector store with documents.
    
    Args:
        documents: List of documents to index. Uses DEFAULT_DOCUMENTS if None.
        
    Returns:
        Tuple of (FAISS index, list of valid documents)
    """
    if documents is None:
        documents = DEFAULT_DOCUMENTS
    
    logger.info("Generating embeddings for documents...")
    
    # Get embeddings for all documents
    document_embeddings = get_embeddings_batch(documents, task_type="RETRIEVAL_DOCUMENT")
    
    # Filter out failed embeddings
    valid_embeddings = []
    valid_documents = []
    
    for i, (doc, embedding) in enumerate(zip(documents, document_embeddings)):
        if embedding is not None:
            valid_embeddings.append(embedding)
            valid_documents.append(doc)
        else:
            logger.warning(f"Could not generate embedding for document {i}")
    
    if not valid_embeddings:
        raise ValueError("No valid embeddings generated")
    
    # Convert to numpy array
    embeddings_array = np.array(valid_embeddings).astype('float32')
    
    # Initialize FAISS index
    dimension = len(embeddings_array[0])
    index = faiss.IndexFlatL2(dimension)
    
    # Add vectors to the index
    index.add(embeddings_array)
    
    logger.info(f"Created FAISS index with {index.ntotal} vectors of dimension {dimension}")
    
    return index, valid_documents

def search_similar_documents(
    index: faiss.Index,
    documents: List[str],
    query_text: str,
    n_results: int = 1
) -> List[str]:
    """
    Search for similar documents using FAISS.
    
    Args:
        index: FAISS index
        documents: List of documents corresponding to index
        query_text: Query text to search with
        n_results: Number of results to return
        
    Returns:
        List of retrieved documents
    """
    from .embeddings import get_embedding
    
    # Get embedding for the query
    query_embedding = get_embedding(query_text, task_type="RETRIEVAL_QUERY")
    
    if query_embedding is None:
        logger.warning("Could not generate embedding for query")
        return []
    
    # Convert to numpy array
    query_embedding_array = np.array([query_embedding]).astype('float32')
    
    # Search the index
    distances, indices = index.search(query_embedding_array, n_results)
    
    # Return the retrieved documents
    retrieved_documents = [documents[i] for i in indices[0] if i < len(documents)]
    
    return retrieved_documents