"""Thread-safe per-session cache for LLM and TTS client instances."""

import hashlib
import threading
from typing import Any, Dict, List, Optional

from ..config.logging_config import get_logger

logger = get_logger(__name__)

# Registry: session_id -> {"llm": instance, "tts": instance, "gemini_hash": str, "cartesia_hash": str}
_session_clients: Dict[str, Dict[str, Any]] = {}
_registry_lock = threading.Lock()


def _key_hash(api_key: str) -> str:
    """Return a short SHA-256 hash of an API key for comparison (never log raw keys)."""
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]


def get_session_llm(session_id: str, api_key: str, tools: Optional[List] = None):
    """Return a cached or newly created LLM instance for the session.

    If the API key has changed since the last call, the LLM is recreated.

    Args:
        session_id: Gradio session hash.
        api_key: User-provided Gemini API key.
        tools: Tool definitions to bind to the LLM.

    Returns:
        Initialized ``ChatGoogleGenerativeAI`` instance with tools bound.
    """
    key_hash = _key_hash(api_key)

    with _registry_lock:
        entry = _session_clients.get(session_id)
        if entry and entry.get("llm") and entry.get("gemini_hash") == key_hash:
            return entry["llm"]

    # Create outside lock to avoid blocking other sessions
    from .client import initialize_llm

    llm = initialize_llm(api_key=api_key, tools=tools)
    logger.info(f"Created new LLM instance for session {session_id[:8]}...")

    with _registry_lock:
        if session_id not in _session_clients:
            _session_clients[session_id] = {}
        _session_clients[session_id]["llm"] = llm
        _session_clients[session_id]["gemini_hash"] = key_hash

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
        logger.info(f"Created new TTS client for session {session_id[:8]}...")
    except Exception as e:
        logger.warning(f"Failed to create TTS client for session {session_id[:8]}...: {e}")
        return None

    with _registry_lock:
        if session_id not in _session_clients:
            _session_clients[session_id] = {}
        _session_clients[session_id]["tts"] = tts
        _session_clients[session_id]["cartesia_hash"] = key_hash

    return tts


def clear_session_clients(session_id: str) -> None:
    """Remove cached LLM and TTS clients for a session.

    Called on session reset to free resources.
    """
    with _registry_lock:
        if session_id in _session_clients:
            del _session_clients[session_id]
            logger.info(f"Cleared cached clients for session {session_id[:8]}...")
