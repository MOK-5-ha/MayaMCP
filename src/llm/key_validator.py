"""Lightweight API key validation for BYOK authentication."""

import threading

from ..config.logging_config import get_logger

logger = get_logger(__name__)

# Reuse SDK error classes from client.py
try:
    from google import genai
    from google.genai import errors as genai_errors
except ImportError:
    genai = None
    genai_errors = None

_VALIDATE_LOCK = threading.Lock()


def validate_gemini_key(api_key: str) -> tuple:
    """Validate a Gemini API key with a lightweight API call.

    Makes a ``models.list()`` request which consumes no tokens.

    Args:
        api_key: The Gemini API key to validate.

    Returns:
        ``(True, "")`` on success, or ``(False, error_message)`` on failure.
    """
    if not api_key or not api_key.strip():
        return False, "Please enter a Gemini API key."

    api_key = api_key.strip()

    if genai is None:
        logger.error("google-genai SDK not installed; cannot validate key")
        return False, "Server configuration error. Please try again later."

    try:
        with _VALIDATE_LOCK:
            client = genai.Client(api_key=api_key)
            # models.list() is the cheapest possible call - no tokens consumed
            _models = list(client.models.list())
        logger.info("Gemini API key validated successfully")
        return True, ""
    except Exception as e:
        msg = str(e).lower()
        code = getattr(e, "status_code", None)
        error_code = getattr(e, "error_code", None)

        # Rate limit / quota exceeded
        if code == 429 or error_code == 429 or "429" in msg or "rate" in msg or "quota" in msg:
            logger.warning(f"Gemini key validation hit rate limit: {e}")
            return (
                False,
                "This API key has exceeded its rate limit. "
                "Please wait a moment and try again, or enable billing in Google AI Studio.",
            )

        # Authentication / permission errors
        if (
            code in (401, 403)
            or error_code in (401, 403)
            or "401" in msg
            or "403" in msg
            or "invalid" in msg
            or "auth" in msg
            or "permission" in msg
            or "unauthenticated" in msg
        ):
            logger.warning(f"Gemini key validation auth failure: {e}")
            return (
                False,
                "Invalid API key. Please verify your key from Google AI Studio "
                "(https://aistudio.google.com/app/apikey).",
            )

        # Network / timeout errors
        if "timeout" in msg or "connect" in msg or "network" in msg:
            logger.warning(f"Gemini key validation network error: {e}")
            return False, "Connection error. Please check your internet and try again."

        # Unknown error
        logger.error(f"Gemini key validation unexpected error: {e}")
        return False, f"Validation failed: {e}"
