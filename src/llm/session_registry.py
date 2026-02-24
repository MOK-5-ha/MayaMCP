"""Thread-safe per-session cache for LLM and TTS client instances."""

import hashlib
import os
import threading
from typing import Any, Dict, List, Optional

from ..config.logging_config import get_logger

logger = get_logger(__name__)

# Registry: session_id -> {"llm": instance, "tts": instance, "gemini_hash": str, "cartesia_hash": str}
_session_clients: Dict[str, Dict[str, Any]] = {}
_registry_lock = threading.Lock()

# Import new session manager for memory-aware admission control
try:
    from ..utils.session_manager import get_session_manager
    _session_manager_available = True
except ImportError:
    logger.warning("Session manager not available, using legacy session limits")
    _session_manager_available = False

# Resource limits
def _get_env_int(env_var: str, default: int) -> int:
    """Safely parse integer from environment variable with fallback."""
    try:
        value = os.getenv(env_var)
        if value is not None:
            return int(value)
    except ValueError:
        logger.error(
            "Invalid %s value '%s', using default %s",
            env_var, value, default
        )
    return default

# Legacy fallback if session manager unavailable
MAX_CONCURRENT_SESSIONS = _get_env_int("MAYA_MAX_SESSIONS", 1000)


class SessionLimitExceededError(RuntimeError):
    """Raised when maximum concurrent session limit is exceeded."""
    pass


def _key_hash(api_key: str) -> str:
    """Return a short SHA-256 hash of an API key for comparison (never log raw keys)."""
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]


def get_session_llm(session_id: str, api_key: str, tools: Optional[List] = None):
    """Return a cached or newly created LLM instance for session.

    If API key has changed since last call, LLM is recreated.

    Args:
        session_id: Gradio session hash.
        api_key: User-provided Gemini API key.
        tools: Tool definitions to bind to LLM.

    Returns:
        Initialized ``ChatGoogleGenerativeAI`` instance with tools bound.
    """
    key_hash = _key_hash(api_key)

    # Check for existing session first (fast path)
    with _registry_lock:
        entry = _session_clients.get(session_id)
        if entry and entry.get("llm") and entry.get("gemini_hash") == key_hash:
            return entry["llm"]

    # Memory-aware session admission control
    if _session_manager_available:
        session_manager = get_session_manager()
        if not session_manager.create_session(session_id, key_hash):
            logger.warning(
                f"Session {session_id[:8]} rejected by memory-aware admission control"
            )
            raise SessionLimitExceededError(
                "Session rejected: insufficient memory or session limit reached"
            )
    else:
        # Legacy fallback: check session limit and reserve slot atomically
        with _registry_lock:
            if session_id not in _session_clients:
                if len(_session_clients) >= MAX_CONCURRENT_SESSIONS:
                    logger.warning(
                        f"Maximum concurrent sessions "
                        f"({MAX_CONCURRENT_SESSIONS}) reached"
                    )
                    raise SessionLimitExceededError(
                        f"Too many concurrent sessions: {MAX_CONCURRENT_SESSIONS}"
                    )

                # Reserve session slot
                _session_clients[session_id] = {}

    # Create outside lock to avoid blocking other sessions
    from .client import initialize_llm

    llm = initialize_llm(api_key=api_key, tools=tools)
    logger.info("Created new LLM instance for session %s...", session_id[:8])

    with _registry_lock:
        entry = _session_clients[session_id]
        # Another thread may have stored an LLM while we were creating ours
        existing = entry.get("llm")
        if existing and entry.get("gemini_hash") == key_hash:
            # Discard the redundant instance we just built
            # (ChatGoogleGenerativeAI is stateless — no close needed)
            return existing
        entry["llm"] = llm
        entry["gemini_hash"] = key_hash

    return llm


def get_session_tts(session_id: str, api_key: Optional[str] = None):
    """Return a cached or newly created Cartesia TTS client for the session.

    If ``api_key`` is ``None`` or empty, returns ``None`` (TTS disabled).

    Args:
        session_id: Gradio session hash.
        api_key: User-provided Cartesia API key (optional).

    Returns:
        Initialized Cartesia client, or ``None`` if unavailable.
    """
    if not api_key or not api_key.strip():
        return None

    api_key = api_key.strip()
    key_hash = _key_hash(api_key)

    with _registry_lock:
        entry = _session_clients.get(session_id)
        if entry and entry.get("tts") and entry.get("cartesia_hash") == key_hash:
            return entry["tts"]

    # Create outside lock
    try:
        from ..voice.tts import initialize_cartesia_client

        tts = initialize_cartesia_client(api_key)
        logger.info("Created new TTS client for session %s...", session_id[:8])
    except Exception as e:
        logger.warning("Failed to create TTS client for session %s...: %s", session_id[:8], e)
        return None

    with _registry_lock:
        if session_id not in _session_clients:
            _session_clients[session_id] = {}
        entry = _session_clients[session_id]
        # Another thread may have stored a TTS client while we were creating ours
        existing = entry.get("tts")
        if existing and entry.get("cartesia_hash") == key_hash:
            # Close the redundant Cartesia client we just built
            close_fn = getattr(tts, "close", None)
            if callable(close_fn):
                try:
                    close_fn()
                except Exception:
                    logger.exception(
                        "Failed to close redundant TTS client for session %s",
                        session_id[:8],
                    )
            return existing
        if existing and entry.get("cartesia_hash") != key_hash:
            # API key changed: close the old client to avoid leaking httpx pool
            close_fn = getattr(existing, "close", None)
            if callable(close_fn):
                try:
                    close_fn()
                except Exception:
                    logger.exception(
                        "Failed to close old TTS client for session %s upon key rotation",
                        session_id[:8],
                    )
        entry["tts"] = tts
        entry["cartesia_hash"] = key_hash

    return tts


def cleanup_sessions(session_ids: List[str]) -> None:
    """Remove cached LLM and TTS clients for multiple sessions.
    
    Attempts to close TTS clients for each session before discarding entries.
    Used by background cleanup processes to free resources.
    
    Args:
        session_ids: List of session IDs to clean up.
    """
    # Collect entries under lock, then do I/O cleanup outside it.
    evicted: List[tuple] = []
    with _registry_lock:
        for session_id in session_ids:
            entry = _session_clients.pop(session_id, None)
            if entry is not None:
                evicted.append((session_id, entry))

    for session_id, entry in evicted:
        tts = entry.get("tts")
        if tts is not None:
            close_fn = getattr(tts, "close", None)
            if callable(close_fn):
                try:
                    close_fn()
                except Exception:
                    logger.exception(
                        "Failed to close TTS client for session %s",
                        session_id[:8],
                    )
    logger.info("Cleaned up LLM/TTS clients for session %s...", session_id[:8])

    # Also remove from session manager if available
    if _session_manager_available:
        try:
            session_manager = get_session_manager()
            for session_id in session_ids:
                session_manager.remove_session(session_id)
        except Exception as e:
            logger.warning(f"Failed to remove session from manager: {e}")


def clear_session_clients(session_id: str) -> None:
    """Remove cached LLM and TTS clients for a session.

    Attempts to close the Cartesia TTS client (which owns an httpx
    connection pool) before discarding the entry.  ChatGoogleGenerativeAI
    is stateless and has no close method, so it is simply dereferenced.

    Called on session reset to free resources.
    """
    with _registry_lock:
        entry = _session_clients.pop(session_id, None)

    if entry is None:
        return

    # Close the TTS client if it exposes a close() method (Cartesia does)
    tts = entry.get("tts")
    if tts is not None:
        close_fn = getattr(tts, "close", None)
        if callable(close_fn):
            try:
                close_fn()
            except Exception:
                logger.exception(
                    "Failed to close TTS client for session %s",
                    session_id[:8],
                )

    logger.info("Cleared cached clients for session %s...", session_id[:8])
