"""Embedding generation for RAG system."""

from typing import List, Optional

from google.genai import types
from tenacity import RetryCallState, retry, stop_after_attempt, wait_exponential

from ..config.api_keys import get_google_api_key
from ..config.logging_config import get_logger
from ..llm.client import get_genai_client
from ..utils.errors import classify_and_log_genai_error

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

EMBEDDING_MODEL = "gemini-embedding-001"
DEFAULT_TASK_TYPE = "RETRIEVAL_DOCUMENT"
BATCH_SIZE = 64


def _retry_return_none(_retry_state: RetryCallState):
    return None


logger = get_logger(__name__)


def _get_embed_client():
    """Return a genai Client for embedding calls, or None if no API key."""
    api_key = get_google_api_key()
    if not api_key:
        logger.error("GEMINI_API_KEY not set; cannot generate embeddings.")
        return None
    return get_genai_client(api_key)


def _parse_embedding_values(emb) -> Optional[List[float]]:
    """Extract a float list from a single embedding object."""
    if hasattr(emb, "values"):
        values_attr = emb.values
        # Some protobuf repeated-field accessors or wrapper objects expose
        # emb.values as a callable method rather than a plain list; invoke
        # it to retrieve the actual sequence in that case.
        vec_source = values_attr() if callable(values_attr) else values_attr
        return list(vec_source)
    if isinstance(emb, list):
        return emb
    return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), retry_error_callback=_retry_return_none)
def get_embedding(text: str, task_type: str = DEFAULT_TASK_TYPE) -> Optional[List[float]]:
    """
        Embedding vector as list of floats, or None if failed.
    """
    try:
        client = _get_embed_client()
        if client is None:
            return None

        config = types.EmbedContentConfig(task_type=task_type)
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=config,
        )

        # Parse the response to extract embedding vector
        if hasattr(response, "embeddings") and response.embeddings:
            return _parse_embedding_values(response.embeddings[0])

        logger.warning(f"Unexpected embedding response structure: {type(response)}")
        return None

    except _NON_RETRYABLE_EXCEPTIONS as e:
        classify_and_log_genai_error(e, logger, context="while generating embedding")
        return None
    except Exception as e:
        classify_and_log_genai_error(e, logger, context="while generating embedding")
        raise


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def _call_batch_embed(client, batch: List[str], task_type: str):
    """Call batch embedding API with retry logic."""
    try:
        config = types.EmbedContentConfig(task_type=task_type)
        resp = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=batch,
            config=config,
        )
        return resp
    except Exception as e:
        logger.warning(f"Batch embed error (size={len(batch)}): {e}")
        raise


def get_embeddings_batch(texts: List[str], task_type: str = DEFAULT_TASK_TYPE) -> List[Optional[List[float]]]:
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

    client = _get_embed_client()
    if client is None:
        return [None] * len(texts)

    results: List[Optional[List[float]]] = []

    def _parse_resp(resp, expected_len: int) -> List[Optional[List[float]]]:
        out: List[Optional[List[float]]] = []
        if hasattr(resp, "embeddings") and isinstance(resp.embeddings, list):
            for item in resp.embeddings:
                out.append(_parse_embedding_values(item))
        else:
            out = [None] * expected_len
        return out

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        try:
            resp = _call_batch_embed(client, batch, task_type)
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
        except Exception:
            logger.exception(f"Batch failed after retries (size={len(batch)})")
            batch_vecs = [None] * len(batch)
        results.extend(batch_vecs)

    return results
