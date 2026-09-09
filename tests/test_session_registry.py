import importlib
import os
import time
from unittest.mock import patch

import src.llm.session_registry as session_registry
from src.llm.session_registry import _key_hash


def test_key_hash_basic_properties():
    """Verify _key_hash generates deterministic 16-hex-character fingerprints."""
    h1 = _key_hash("test-project:global")
    h2 = _key_hash("test-project:global")
    h3 = _key_hash("other-project:global")

    assert len(h1) == 16
    assert h1 == h2
    assert h1 != h3
    # Valid hexadecimal
    int(h1, 16)


def test_key_hash_fallback_secret_not_hardcoded_default():
    """Verify that when MAYA_KEY_HASH_SECRET is unset, the fallback is not a public hardcoded string."""
    assert session_registry._KEY_HASH_SECRET != b"maya-dev-key-hash-secret"
    assert len(session_registry._KEY_HASH_SECRET) >= 32


def test_key_hash_latency_non_blocking():
    """Verify _key_hash is fast (HMAC) and does not perform expensive PBKDF2 iterations."""
    t0 = time.perf_counter()
    for _ in range(50):
        _key_hash("test-project:global")
    elapsed = time.perf_counter() - t0

    # 50 iterations of PBKDF2 (310k) would take > 10 seconds.
    # 50 iterations of HMAC takes < 5 milliseconds.
    assert elapsed < 0.1, f"Hash derivation was too slow ({elapsed:.3f}s for 50 iterations)"


def test_key_hash_custom_secret_env():
    """Verify MAYA_KEY_HASH_SECRET environment variable is respected when set."""
    with patch.dict(os.environ, {"MAYA_KEY_HASH_SECRET": "custom-secret-key-12345"}):
        importlib.reload(session_registry)
        try:
            assert session_registry._KEY_HASH_SECRET == b"custom-secret-key-12345"
            h = session_registry._key_hash("test-project:global")
            assert len(h) == 16
        finally:
            # Reload module without custom secret to restore clean state
            os.environ.pop("MAYA_KEY_HASH_SECRET", None)
            importlib.reload(session_registry)
