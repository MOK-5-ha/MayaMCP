"""LLM client initialization and API calls."""

import google.generativeai as genai
import threading
from langchain_google_genai import ChatGoogleGenerativeAI
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log
import logging
from typing import Dict, List, Any, Optional
from ..config.logging_config import get_logger
from ..config.model_config import get_model_config, get_generation_config
from ..utils.errors import classify_and_log_genai_error


logger = get_logger(__name__)
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

_GENAI_CONFIGURED = False
_CONFIG_LOCK = threading.Lock()

def configure_genai(api_key: str) -> None:
    """Configure the Google Generative AI client for API key auth."""
    global _GENAI_CONFIGURED
    if _GENAI_CONFIGURED:
        return

    with _CONFIG_LOCK:
        if not _GENAI_CONFIGURED:
            genai.configure(api_key=api_key)
            _GENAI_CONFIGURED = True


def get_generative_model(model_name: str) -> genai.GenerativeModel:
    """Return a GenerativeModel for the given model name."""
    return genai.GenerativeModel(model_name)


def build_generate_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Map our generation config dict for google-generativeai (dict-based)."""
    return {
        "temperature": config_dict.get("temperature"),
        "top_p": config_dict.get("top_p"),
        "top_k": config_dict.get("top_k"),
        "max_output_tokens": config_dict.get("max_output_tokens"),
    }


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
            logger.info(f"Successfully initialized LangChain ChatGoogleGenerativeAI model without tools.")

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
) -> genai.types.GenerateContentResponse:
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

    # Configure Google Generative AI (free Gemini API)
    configure_genai(api_key)

    # Get model name from shared config
    model_name = get_model_name()

    # Map our config dict to generation_config (dict)
    gen_config = build_generate_config(config)

    # Call the API via GenerativeModel
    try:
        model = get_generative_model(model_name)
        response = model.generate_content(
            contents=prompt_content,
            generation_config=gen_config,
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
            classify_and_log_genai_error(e, logger, context="calling Gemini API")
        raise

    logger.debug("Gemini API call successful.")
    return response