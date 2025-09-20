"""Embedding generation for RAG system."""

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional, List
from ..config.logging_config import get_logger
from ..utils.errors import classify_and_log_genai_error
from ..config.api_keys import get_google_api_key



logger = get_logger(__name__)





@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_embedding(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> Optional[List[float]]:
    """
        Embedding vector as list of floats, or None if failed.
    """
    try:
        # Configure and call Embeddings API (free Gemini API)
        api_key = get_google_api_key()
        if not api_key:
            logger.error("GEMINI_API_KEY not set; cannot generate embeddings.")
            return None
        genai.configure(api_key=api_key)
        response = genai.embed_content(
            model="text-embedding-004",
            content=text,
        )

        # Parse the response to extract embedding vector
        if hasattr(response, "embedding"):
            emb = response.embedding
            # New SDK usually returns .embedding.values (list[float])
            if hasattr(emb, "values"):
                return list(emb.values)
            # Fallback if already a list-like
            if isinstance(emb, list):
                return emb
        elif isinstance(response, dict):
            emb = response.get("embedding")
            if isinstance(emb, dict) and "values" in emb:
                return list(emb["values"])
            if isinstance(emb, list):
                return emb

        logger.warning(f"Unexpected embedding response structure: {type(response)}")
        return None

    except Exception as e:
        classify_and_log_genai_error(e, logger, context="while generating embedding")
        return None

def get_embeddings_batch(texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[Optional[List[float]]]:
    """
    Get embeddings for multiple texts via a single batch API call with chunking and retry.

    Args:
        texts: List of texts to embed
        task_type: Type of embedding task (forwarded when supported)

    Returns:
        List of embedding vectors (floats) aligned to input order; None for failures.
    """
    if not texts:
        return []

    # Configure API
    api_key = get_google_api_key()
    if not api_key:
        logger.error("GEMINI_API_KEY not set; cannot generate batch embeddings.")
        return [None] * len(texts)
    genai.configure(api_key=api_key)
    # If batch API isn't available in the installed SDK, fall back to per-item calls
    if not hasattr(genai, "batch_embed_contents"):
        logger.info("batch_embed_contents not available; falling back to sequential embed_content calls.")
        return [get_embedding(t, task_type=task_type) for t in texts]


    BATCH_SIZE = 64  # conservative default; adjust if higher limits are guaranteed
    results: List[Optional[List[float]]] = []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def _call_batch(batch: List[str]):
        try:
            # Use the Google AI Studio batch embeddings endpoint
            resp = genai.batch_embed_contents(
                model="text-embedding-004",
                requests=[{"content": t} for t in batch],
            )
            return resp
        except Exception as e:
            # Log and re-raise for tenacity to handle backoff/retry
            logger.warning(f"Batch embed error (size={len(batch)}): {e}")
            raise

    def _parse_resp(resp, expected_len: int) -> List[Optional[List[float]]]:
        out: List[Optional[List[float]]] = []
        seq = None
        if hasattr(resp, "embeddings"):
            seq = getattr(resp, "embeddings")
        elif isinstance(resp, dict):
            seq = resp.get("embeddings") or resp.get("results") or resp.get("data")
        elif isinstance(resp, list):
            seq = resp
        if isinstance(seq, list):
            for item in seq:
                vec = None
                if hasattr(item, "values"):
                    vec = list(item.values)
                elif isinstance(item, dict) and "values" in item:
                    vec = list(item["values"])
                elif isinstance(item, list):
                    vec = item
                out.append(vec)
        else:
            out = [None] * expected_len
        return out

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        try:
            resp = _call_batch(batch)
            batch_vecs = _parse_resp(resp, len(batch))
            # Ensure 1:1 alignment with input batch
            if len(batch_vecs) != len(batch):
                logger.warning(
                    f"Batch response length mismatch: expected {len(batch)}, got {len(batch_vecs)}"
                )
                if len(batch_vecs) < len(batch):
                    batch_vecs.extend([None] * (len(batch) - len(batch_vecs)))
                else:
                    batch_vecs = batch_vecs[: len(batch)]
        except Exception as e:
            logger.error(f"Batch failed after retries (size={len(batch)}): {e}")
            batch_vecs = [None] * len(batch)
        results.extend(batch_vecs)

    return results