"""
Memvid-enhanced RAG pipeline for Maya
"""

from google import genai
from typing import List

from .memvid_store import search_memvid_documents
from ..config.logging_config import get_logger
from ..utils.errors import classify_and_log_genai_error

logger = get_logger(__name__)



def generate_memvid_response(
    query_text: str,
    retrieved_documents: List[str],
    api_key: str,
    model_version: str = "gemini-2.5-flash-preview-04-17"
) -> str:
    """
    Generate a response augmented with Memvid-retrieved documents.

    Args:
        query_text: User query
        retrieved_documents: Documents retrieved from Memvid
        api_key: Google API key
        model_version: Gemini model version to use

    Returns:
        Generated response text
    """
    query_oneline = query_text.replace("\n", " ")

    # Enhanced prompt for Memvid-retrieved content
    prompt = f"""You are Maya, the bartender at "MOK 5-ha". Your name is Maya.
You are conversational and interact with customers using insights from your video memory below.
When asked about your name, ALWAYS respond that your name is Maya.

The bar's name "MOK 5-ha" is pronounced "Moksha" which represents liberation from the cycle of rebirth and union with the divine in Eastern philosophy.
When customers ask about the bar, explain this philosophical theme - that good drinks can help people find temporary liberation from their daily problems, just as spiritual enlightenment frees the soul from worldly attachments.

Your video memory has retrieved these relevant insights: {' | '.join(retrieved_documents)}

Be sure to respond in a complete sentence while maintaining a modest and humorous tone.
If the retrieved insights aren't directly relevant, you may draw inspiration from them while staying true to the conversation.

Question: {query_oneline}
Answer:"""

    try:
        # Initialize Google GenAI client (modern SDK)
        client = genai.Client(api_key=api_key)

        # Generate response
        resp = client.models.generate_content(
            model=model_version,
            contents=prompt,
        )

        return getattr(resp, "text", "") or ""

    except Exception as e:
        classify_and_log_genai_error(e, logger, context="while generating Memvid-enhanced response")
        # Fallback response
        return "I'm Maya, your bartender at MOK 5-ha. My video memory seems to be having a moment. Can I get you something from the menu?"

def memvid_rag_pipeline(
    query_text: str,
    memvid_retriever,
    api_key: str,
    model_version: str = "gemini-2.5-flash-preview-04-17"
) -> str:
    """
    Complete Memvid-based RAG pipeline for query processing.

    Args:
        query_text: User query
        memvid_retriever: MemvidRetriever instance
        api_key: Google API key
        model_version: Gemini model version to use

    Returns:
        Generated response text
    """
    try:
        # Get relevant passages from Memvid
        relevant_passages = search_memvid_documents(
            retriever=memvid_retriever,
            query_text=query_text,
            n_results=2  # Get 2 relevant passages for richer context
        )

        # If no relevant passages found, return empty string
        if not relevant_passages:
            logger.warning("No relevant passages found for query: %s", query_text)
            return ""

        # Generate Memvid-enhanced response
        enhanced_response = generate_memvid_response(
            query_text=query_text,
            retrieved_documents=relevant_passages,
            api_key=api_key,
            model_version=model_version
        )

        return enhanced_response

    except Exception as e:
        classify_and_log_genai_error(e, logger, context="in Memvid RAG pipeline")
        return ""