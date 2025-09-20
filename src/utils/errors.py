"""Shared error classification and logging helpers."""
from typing import Protocol
import re

# We accept any logger-like object that supports .warning and .error
class _LoggerLike(Protocol):
    def warning(self, msg: str) -> None: ...
    def error(self, msg: str) -> None: ...


def classify_and_log_genai_error(e: Exception, logger: _LoggerLike, context: str) -> None:
    """Classify common GenAI errors by message and log with consistent format.
    Replicates existing checks across the codebase for compatibility.

    Args:
        e: The exception to classify
        logger: Logger instance to write messages to
        context: Short phrase to complete the log message, e.g.,
                 "in RAG pipeline" or "while generating Memvid-enhanced response"
    """
    msg = str(e)
    try:
        if ("429" in msg) or re.search(r"\brate\s*limit\b", msg, re.IGNORECASE):
            logger.warning(f"Rate limit {context}: {e}")
        elif ("401" in msg) or ("403" in msg) or re.search(r"\b(auth|authentication|authorization)\b", msg, re.IGNORECASE):
            logger.error(f"Authentication error {context}: {e}")
        elif "timeout" in msg.lower():
            logger.warning(f"Timeout {context}: {e}")
        else:
            logger.error(f"Error {context}: {e}")
    except Exception:
        # Fallback to generic log in case of unexpected logging issues
        try:
            logger.error(f"Error {context}: {e}")
        except Exception:
            # Last resort: ignore logging failure
            pass

