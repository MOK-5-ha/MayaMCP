"""Lightweight API key validation for BYOK authentication."""

from ..config.logging_config import get_logger

logger = get_logger(__name__)

# Reuse SDK error classes from client.py
try:
    from google import genai
except ImportError:
    genai = None

# Timeout in milliseconds for the validation request (10 seconds).
_VALIDATION_TIMEOUT_MS = 10_000


def validate_gemini_key(api_key: str) -> tuple[bool, str]:
    """Validate a Gemini API key with a lightweight API call.

    Makes a ``models.list()`` request (page_size=1) which consumes no
    tokens and fetches only the first model entry to minimise latency.

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
        client = genai.Client(
            api_key=api_key,
            http_options={"timeout": _VALIDATION_TIMEOUT_MS},
        )
        # Fetch only the first model entry — cheapest possible call,
        # no tokens consumed, proves the key is valid.
        next(iter(client.models.list(config={"page_size": 1})), None)
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
        return False, "Validation failed. Please try again or contact support."
