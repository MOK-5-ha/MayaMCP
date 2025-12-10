"""Embedding generation for RAG system."""

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, RetryCallState
from typing import Optional, List
from ..config.logging_config import get_logger
from ..utils.errors import classify_and_log_genai_error
from ..config.api_keys import get_google_api_key

try:
    from google.api_core import exceptions as google_api_exceptions
except ImportError:
    google_api_exceptions = None

_NON_RETRYABLE_EXCEPTIONS = (ValueError, TypeError)
if google_api_exceptions is not None:
    _NON_RETRYABLE_EXCEPTIONS = _NON_RETRYABLE_EXCEPTIONS + (
        google_api_exceptions.InvalidArgument,
        google_api_exceptions.FailedPrecondition,
        google_api_exceptions.PermissionDenied,
        google_api_exceptions.Unauthenticated,
    )

DEFAULT_TASK_TYPE = "RETRIEVAL_DOCUMENT"
BATCH_SIZE = 64


def _retry_return_none(_retry_state: RetryCallState):
    return None


if not hasattr(genai, "batch_embed_contents"):
    genai.batch_embed_contents = None


logger = get_logger(__name__)

# Module-level cache for configured API key to avoid redundant configuration calls
_configured_api_key: Optional[str] = None


def _ensure_genai_configured() -> Optional[str]:
    """Ensure genai is configured with the current API key.
    
    Returns:
        The API key if successfully configured, None otherwise.
        
    Note:
        This function caches the configured API key and only reconfigures
        if the key has changed, improving performance while still supporting
        key rotation in environments where keys may change.
    """
    global _configured_api_key
    
    api_key = get_google_api_key()
    if not api_key:
        logger.error("GEMINI_API_KEY not set; cannot generate embeddings.")
        return None
    
    # Only reconfigure if the API key has changed
    if api_key != _configured_api_key:
        genai.configure(api_key=api_key)
        _configured_api_key = api_key
    
    return api_key



@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), retry_error_callback=_retry_return_none)
def get_embedding(text: str, task_type: str = DEFAULT_TASK_TYPE) -> Optional[List[float]]:
    """
        Embedding vector as list of floats, or None if failed.
    """
    try:
        # Configure and call Embeddings API (free Gemini API)
        if not _ensure_genai_configured():
            return None
        embed_kwargs = {
            "model": "text-embedding-004",
            "content": text,
        }
        if task_type != DEFAULT_TASK_TYPE:
            embed_kwargs["task_type"] = task_type
        response = genai.embed_content(**embed_kwargs)

        # Parse the response to extract embedding vector
        if hasattr(response, "embedding"):
            emb = response.embedding
            # New SDK usually returns .embedding.values (list[float])
            if hasattr(emb, "values"):
                values_attr = emb.values
                vec_source = values_attr() if callable(values_attr) else values_attr
                return list(vec_source)
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

    except _NON_RETRYABLE_EXCEPTIONS as e:
        classify_and_log_genai_error(e, logger, context="while generating embedding")
        return None
    except Exception as e:
        classify_and_log_genai_error(e, logger, context="while generating embedding")
        raise


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def _call_batch_embed(batch_embed_fn, batch: List[str], task_type: str):
    """Call batch embedding API with retry logic.
    
    Args:
        batch_embed_fn: The batch embedding function from genai
        batch: List of texts to embed in this batch
        task_type: Type of embedding task
        
    Returns:
        Response from batch embedding API
        
    Raises:
        Exception: Re-raises exceptions for tenacity to handle
    """
    try:
        # Use the Google AI Studio batch embeddings endpoint
        resp = batch_embed_fn(
            model="text-embedding-004",
            requests=[
                {"content": t, "task_type": task_type}
                if task_type != DEFAULT_TASK_TYPE
                else {"content": t}
                for t in batch
            ],
        )
        return resp
    except Exception as e:
        # Log and re-raise for tenacity to handle backoff/retry
        logger.warning(f"Batch embed error (size={len(batch)}): {e}")
        raise


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
    if not _ensure_genai_configured():
        return [None] * len(texts)
    batch_embed_fn = getattr(genai, "batch_embed_contents", None)
    if not callable(batch_embed_fn):
        logger.info("batch_embed_contents not available; falling back to sequential embed_content calls.")
        return [get_embedding(t, task_type=task_type) for t in texts]


    results: List[Optional[List[float]]] = []

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
                if isinstance(item, dict) and "values" in item:
                    vec = list(item["values"])
                elif hasattr(item, "values"):
                    values_attr = item.values
                    vec_source = values_attr() if callable(values_attr) else values_attr
                    vec = list(vec_source)
                elif isinstance(item, list):
                    vec = item
                out.append(vec)
        else:
            out = [None] * expected_len
        return out

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        try:
            resp = _call_batch_embed(batch_embed_fn, batch, task_type)
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