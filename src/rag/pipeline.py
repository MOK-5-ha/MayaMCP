"""Complete RAG pipeline orchestration."""

import google.generativeai as genai
from typing import List, Optional
from .retrieval import retrieve_relevant_passages
from ..config.logging_config import get_logger
from ..utils.errors import classify_and_log_genai_error


logger = get_logger(__name__)

def generate_augmented_response(
    query_text: str,
    retrieved_documents: List[str],
    api_key: str,
    model_version: str = "gemini-2.5-flash-preview-04-17"
) -> str:
    """
    Generate a response augmented with the retrieved documents.

    Args:
        query_text: User query
        retrieved_documents: Documents retrieved from vector store
        api_key: Google API key
        model_version: Gemini model version to use

    Returns:
        Generated response text
    """
    query_oneline = query_text.replace("\n", " ")

    # Prompt template for the bartender agent
    prompt = f"""You are Maya, the bartender at "MOK 5-ha". Your name is Maya.
You are conversational and interact with customers using text from the reference passage included below.
When asked about your name, ALWAYS respond that your name is Maya.

The bar's name "MOK 5-ha" is pronounced "Moksha" which represents liberation from the cycle of rebirth and union with the divine in Eastern philosophy.
When customers ask about the bar, explain this philosophical theme - that good drinks can help people find temporary liberation from their daily problems, just as spiritual enlightenment frees the soul from worldly attachments.

Be sure to respond in a complete sentence while maintaining a modest and humorous tone.
If the passage is irrelevant to the answer, you may ignore it.

Reference passage: {' '.join(retrieved_documents)}

Question: {query_oneline}
Answer:"""

    try:
        # Configure and call Google Generative AI (free Gemini API)
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_version)
        resp = model.generate_content(prompt)
        return getattr(resp, "text", "") or ""

    except Exception as e:
        classify_and_log_genai_error(e, logger, context="while generating augmented response")
        # Fallback response
        return "I'm Maya, your bartender at MOK 5-ha. I'm not sure how to respond to that. Can I get you something from the menu?"

def rag_pipeline(
    query_text: str,
    index,
    documents: List[str],
    api_key: str,
    model_version: str = "gemini-2.5-flash-preview-04-17"
) -> str:
    """
    Complete RAG pipeline for query processing.

    Args:
        query_text: User query
        index: FAISS index
        documents: List of documents corresponding to index
        api_key: Google API key
        model_version: Gemini model version to use

    Returns:
        Generated response text
    """
    try:
        # Get relevant passages from FAISS
        relevant_passages = retrieve_relevant_passages(
            index=index,
            documents=documents,
            query_text=query_text
        )

        # If no relevant passages found, return empty string
        if not relevant_passages:
            logger.warning("No relevant passages found for query: %s", query_text)
            return ""

        # Generate augmented response
        augmented_response = generate_augmented_response(
            query_text=query_text,
            retrieved_documents=relevant_passages,
            api_key=api_key,
            model_version=model_version
        )

        return augmented_response

    except Exception as e:
        classify_and_log_genai_error(e, logger, context="in RAG pipeline")
        return ""