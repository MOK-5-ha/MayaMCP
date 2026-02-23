"""LLM client initialization and API calls."""

import logging
import threading
from typing import Any, Dict, Generator, List, Optional

from google import genai
from google.genai import types
from langchain_google_genai import ChatGoogleGenerativeAI
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

from ..config.logging_config import get_logger
from ..config.model_config import get_model_config
from ..utils.errors import classify_and_log_genai_error

logger = get_logger(__name__)


def _handle_genai_fallback_error(e: Exception, logger: logging.Logger, context: str):
    """
    Handle fallback error classification for GenAI exceptions.
    
    Args:
        e: The exception to classify and handle
        logger: Logger instance for error reporting
        context: Context string for error classification
    """
    # Fallback classification using attributes to avoid brittle string matching
    code = getattr(e, "status_code", None)
    error_code = getattr(e, "error_code", None)
    
    # Detect timeouts via common exception types
    # Check for built-in timeout
    is_timeout = isinstance(e, TimeoutError)
    if not is_timeout and httpx is not None:
        httpx_timeout_types = tuple(
            t for t in [
                getattr(httpx, "TimeoutException", None),
                getattr(httpx, "ReadTimeout", None),
                getattr(httpx, "WriteTimeout", None),
                getattr(httpx, "ConnectTimeout", None),
            ] if isinstance(t, type)
        )
        if httpx_timeout_types and isinstance(e, httpx_timeout_types):
            is_timeout = True

    if is_timeout:
        logger.warning(f"Timeout from Gemini API: {e}")
    elif code == 429 or error_code == 429:
        logger.warning(f"Rate limit hit calling Gemini: {e}")
    elif code in (401, 403) or error_code in (401, 403):
        logger.error(f"Authentication/authorization error calling Gemini: {e}")
    else:
        # Fall back to shared string-based classifier to keep consistency
        classify_and_log_genai_error(e, logger, context=context)
# Optional: SDK-specific errors and HTTP client timeout classes
try:
    from google.genai import errors as genai_errors  # type: ignore
except Exception:
    genai_errors = None  # SDK may not expose errors in some versions

try:
    import httpx  # type: ignore
except Exception:
    httpx = None

# Sentinel error that never matches real SDK exceptions; safe for except clauses
class _NoSDKError(Exception):
    """Used so our except clauses compile even if SDK-specific errors are unavailable."""
    pass

# Map SDK error classes to names, falling back to non-matching sentinel
GenaiRateLimitError = getattr(genai_errors, "RateLimitError", _NoSDKError) if genai_errors else _NoSDKError
GenaiAuthError = getattr(genai_errors, "AuthenticationError", _NoSDKError) if genai_errors else _NoSDKError
GenaiPermissionDeniedError = (
    getattr(genai_errors, "PermissionDeniedError", getattr(genai_errors, "PermissionDenied", _NoSDKError))
    if genai_errors else _NoSDKError
)
GenaiUnauthenticatedError = getattr(genai_errors, "UnauthenticatedError", _NoSDKError) if genai_errors else _NoSDKError
GenaiTimeoutError = getattr(genai_errors, "TimeoutError", _NoSDKError) if genai_errors else _NoSDKError


# ---- Unified Google GenAI client/wrapper utilities ----

_genai_client: Optional[genai.Client] = None
_genai_client_key: Optional[str] = None
_CLIENT_LOCK = threading.Lock()


def get_genai_client(api_key: str) -> genai.Client:
    """Return a singleton genai.Client, creating it if needed.

    Thread-safe. If *api_key* differs from the key used to create the
    current client the client is recreated (supports key rotation).
    """
    global _genai_client, _genai_client_key
    if _genai_client is not None and _genai_client_key == api_key:
        return _genai_client

    with _CLIENT_LOCK:
        if _genai_client is None or _genai_client_key != api_key:
            _genai_client = genai.Client(api_key=api_key)
            _genai_client_key = api_key
        local_client = _genai_client
    return local_client


def build_generate_config(config_dict: Dict[str, Any]) -> types.GenerateContentConfig:
    """Map our generation config dict to a GenerateContentConfig."""
    return types.GenerateContentConfig(
        temperature=config_dict.get("temperature"),
        top_p=config_dict.get("top_p"),
        top_k=config_dict.get("top_k"),
        max_output_tokens=config_dict.get("max_output_tokens"),
    )


def get_model_name() -> str:
    """Return the configured Gemini model name."""
    return get_model_config()["model_version"]


def get_langchain_llm_params() -> Dict[str, Any]:
    """Return a dict of params for ChatGoogleGenerativeAI construction."""
    cfg = get_model_config()
    return {
        "model": cfg["model_version"],
        "temperature": cfg["temperature"],
        "top_p": cfg["top_p"],
        "top_k": cfg["top_k"],
        "max_output_tokens": cfg["max_output_tokens"],
    }


def initialize_llm(api_key: str, tools: Optional[List] = None) -> ChatGoogleGenerativeAI:
    """
    Initialize and return the LLM used for completion.

    Args:
        api_key: Google API key
        tools: List of tools to bind to the LLM

    Returns:
        Initialized ChatGoogleGenerativeAI instance
    """
    try:
        params = get_langchain_llm_params()

        # Initialize ChatGoogleGenerativeAI with the Gemini model
        llm = ChatGoogleGenerativeAI(
            model=params["model"],
            temperature=params["temperature"],
            top_p=params["top_p"],
            top_k=params["top_k"],
            max_output_tokens=params["max_output_tokens"],
            google_api_key=api_key,
        )

        # Bind tools if provided
        if tools:
            llm = llm.bind_tools(tools)
            tool_count = len(tools)
            tool_word = "tool" if tool_count == 1 else "tools"
            logger.info(f"Successfully initialized LangChain ChatGoogleGenerativeAI model bound with {tool_count} {tool_word}.")
        else:
            logger.info("Successfully initialized LangChain ChatGoogleGenerativeAI model without tools.")

        return llm

    except Exception as e:
        logger.error(f"Error initializing LLM: {e}")
        raise

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
def call_gemini_api(
    prompt_content: List[Dict],
    config: Dict,
    api_key: str
) -> types.GenerateContentResponse:
    """
    Internal function to call the Gemini API with retry logic.

    Args:
        prompt_content: List of message dictionaries
        config: Generation configuration
        api_key: Google API key

    Returns:
        Gemini API response
    """
    logger.debug("Calling Gemini API...")

    # Get singleton client
    client = get_genai_client(api_key)

    # Get model name from shared config
    model_name = get_model_name()

    # Map our config dict to GenerateContentConfig
    gen_config = build_generate_config(config)

    # Call the API via client
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt_content,
            config=gen_config,
        )
    except GenaiRateLimitError as e:
        logger.warning(f"Rate limit hit calling Gemini: {e}")
        raise
    except (GenaiAuthError, GenaiPermissionDeniedError, GenaiUnauthenticatedError) as e:
        logger.error(f"Authentication/authorization error calling Gemini: {e}")
        raise
    except GenaiTimeoutError as e:
        logger.warning(f"Timeout from Gemini API: {e}")
        raise
    except Exception as e:
        _handle_genai_fallback_error(e, logger, "calling Gemini API")
        raise

    logger.debug("Gemini API call successful.")
    return response


def stream_gemini_api(
    prompt_content: List[Dict],
    config: Dict,
    api_key: str
) -> Generator[types.GenerateContentResponse, None, None]:
    """
    Stream Gemini API responses with resilient retry logic.

    Args:
        prompt_content: List of message dictionaries
        config: Generation configuration
        api_key: Google API key

    Yields:
        Streaming response chunks
    """
    logger.debug("Starting Gemini API stream...")

    # Internal helper with retry logic for opening streams
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    def _open_gemini_stream():
        """Open a fresh Gemini stream with retry logic."""
        # Get singleton client
        client = get_genai_client(api_key)

        # Get model name from shared config
        model_name = get_model_name()

        # Map our config dict to GenerateContentConfig
        gen_config = build_generate_config(config)

        # Call API via client with streaming
        response_stream = client.models.generate_content_stream(
            model=model_name,
            contents=prompt_content,
            config=gen_config,
        )
        return response_stream

    # Main streaming loop with mid-stream retry handling
    attempt = 0
    max_attempts = 3
    while attempt < max_attempts:
        try:
            # Open fresh stream
            response_stream = _open_gemini_stream()
            
            # Iterate through stream with error handling
            for chunk in response_stream:
                yield chunk
                
            # Stream completed successfully
            break
            
        except (GenaiRateLimitError, GenaiTimeoutError, TimeoutError) as e:
            attempt += 1
            if attempt >= max_attempts:
                logger.error(f"Failed to complete Gemini stream after {max_attempts} attempts: {e}")
                raise
            
            logger.warning(f"Stream interrupted (attempt {attempt}/{max_attempts}): {e}. Retrying...")
            # Note: We don't resume from offset as Gemini doesn't support it,
            # but we track attempts for logging/debugging
            
        except (GenaiAuthError, GenaiPermissionDeniedError,
                GenaiUnauthenticatedError) as e:
            # Don't retry auth errors
            logger.error(f"Authentication error in Gemini stream: {e}")
            raise
            
        except Exception as e:
            # Classify and handle other errors
            _handle_genai_fallback_error(e, logger, "Gemini API stream iteration")
            
            # Determine retry behavior based on error type
            code = getattr(e, "status_code", None)
            error_code = getattr(e, "error_code", None)
            
            # Detect timeouts via common exception types
            is_timeout = isinstance(e, TimeoutError)
            if not is_timeout and httpx is not None:
                httpx_timeout_types = tuple(
                    t for t in [
                        getattr(httpx, "TimeoutException", None),
                        getattr(httpx, "ReadTimeout", None),
                        getattr(httpx, "WriteTimeout", None),
                        getattr(httpx, "ConnectTimeout", None),
                    ] if isinstance(t, type)
                )
                if httpx_timeout_types and isinstance(e, httpx_timeout_types):
                    is_timeout = True

            if is_timeout or code == 429 or error_code == 429:
                # Retry timeouts and rate limits
                attempt += 1
                if attempt >= max_attempts:
                    logger.error(f"Failed to complete Gemini stream after {max_attempts} attempts: {e}")
                    raise
                logger.warning(f"Stream interrupted (attempt {attempt}/{max_attempts}): {e}. Retrying...")
            elif code in (401, 403) or error_code in (401, 403):
                # Don't retry auth errors
                logger.error(f"Authentication error in Gemini stream: {e}")
                raise
            else:
                # Log and retry other errors
                attempt += 1
                if attempt >= max_attempts:
                    logger.error(f"Failed to complete Gemini stream after {max_attempts} attempts: {e}")
                    raise
                logger.warning(f"Stream interrupted (attempt {attempt}/{max_attempts}). Retrying...")

    logger.debug("Gemini API stream completed.")
