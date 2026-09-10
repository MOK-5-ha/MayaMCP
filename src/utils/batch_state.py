"""Batch state cache for optimizing remote dictionary operations.

This module implements a request-scoped cache that absorbs all state
reads/writes within a request lifecycle, flushing to modal.Dict
exactly once at the end. This addresses performance issue
identified in PERFORMANCE_ANALYSIS.md #2.
"""

import threading
from collections.abc import MutableMapping
from contextlib import contextmanager
from typing import Any

from ..config.logging_config import get_logger

logger = get_logger(__name__)


class BatchStateCache:
    """
    Request-scoped cache for state operations that would otherwise trigger
    immediate remote dictionary writes. Accumulates changes and flushes them
    once at the end of the request lifecycle.
    """

    def __init__(self, session_id: str, store: MutableMapping):
        """
        Initialize the batch cache for a specific session and store.

        Args:
            session_id: Unique identifier for the user session
            store: Mutable mapping (dict or modal.Dict) for persistent storage
        """
        self.session_id = session_id
        self.store = store
        self._cached_data: dict[str, Any] | None = None
        self._dirty = False  # Track if we have unsaved changes
        self._invalidated = False  # Set when session is reset to suppress stale flushes
        self._lock = threading.RLock()

    def invalidate(self) -> None:
        """
        Invalidate this cache so that any queued updates are discarded
        and flush() will be a no-op.
        """
        with self._lock:
            self._invalidated = True
            self._dirty = False
            self._cached_data = None
            logger.info(f"Invalidated batch state cache for session {self.session_id}")

    def _load_data(self) -> dict[str, Any]:
        """
        Load session data from store, using cache if available.

        Returns:
            Session data dictionary
        """
        if self._cached_data is None:
            from ..utils.state_manager import _get_session_data
            self._cached_data = _get_session_data(self.session_id, self.store)
            logger.debug(
                f"Loaded session data for {self.session_id} into batch cache"
            )
        return self._cached_data

    def get_session_data(self) -> dict[str, Any]:
        """
        Get cached session data, loading from store if necessary.

        Returns:
            Session data dictionary
        """
        with self._lock:
            return self._load_data().copy()

    def has_cached_data(self) -> bool:
        """
        Check if the cache has loaded data.

        Returns:
            True if cached data exists and cache is not invalidated, False otherwise
        """
        with self._lock:
            return self._cached_data is not None and not self._invalidated

    def get_cached_data(self) -> dict[str, Any] | None:
        """
        Get the currently cached data without loading from store.

        Returns:
            Cached data dictionary or None if not loaded or invalidated
        """
        with self._lock:
            return self._cached_data.copy() if (self._cached_data is not None and not self._invalidated) else None

    def set_cached_data(self, data: dict[str, Any], dirty: bool = True) -> None:
        """
        Set the cached data and optionally mark as dirty.

        Args:
            data: The session data to cache
            dirty: Whether to mark the cache as having unsaved changes
        """
        with self._lock:
            if self._invalidated:
                return
            self._cached_data = data.copy()
            self._dirty = dirty
            logger.debug(f"Set cached data for {self.session_id}, dirty={dirty}")

    def set_dirty(self, dirty: bool = True) -> None:
        """
        Mark the cache as having unsaved changes.

        Args:
            dirty: Whether the cache has unsaved changes
        """
        with self._lock:
            if self._invalidated:
                return
            self._dirty = dirty
            logger.debug(f"Marked cache for {self.session_id} as dirty={dirty}")

    def is_dirty(self) -> bool:
        """
        Check if the cache has unsaved changes.

        Returns:
            True if cache has unsaved changes and is not invalidated, False otherwise
        """
        with self._lock:
            return self._dirty and not self._invalidated


    def get_section(self, section_name: str) -> dict[str, Any]:
        """
        Get a specific section of session data.

        Args:
            section_name: Name of section (e.g., 'conversation',
                         'payment', 'history')

        Returns:
            Section data dictionary
        """
        with self._lock:
            data = self._load_data()
            if section_name not in data:
                raise KeyError(f"Section '{section_name}' not found in session data")
            if not isinstance(data[section_name], dict):
                raise TypeError(f"Section '{section_name}' is not a dictionary")
            return data[section_name].copy()

    def update_session_data(self, updates: dict[str, Any]) -> None:
        """
        Update session data with the provided changes.

        Args:
            updates: Dictionary of updates to apply to session data
        """
        with self._lock:
            data = self._load_data()
            data.update(updates)
            self._dirty = True
            logger.debug(
                f"Queued session data updates for {self.session_id}: "
                f"{list(updates.keys())}"
            )

    def update_section(self, section_name: str, updates: dict[str, Any]) -> None:
        """
        Update a specific section of session data.

        Args:
            section_name: Name of section to update
            updates: Dictionary of updates to apply to section
        """
        with self._lock:
            data = self._load_data()
            if section_name not in data:
                raise KeyError(f"Section '{section_name}' not found in session data")
            if not isinstance(data[section_name], dict):
                raise TypeError(f"Section '{section_name}' is not a dictionary")
            data[section_name].update(updates)
            self._dirty = True
            logger.debug(
                f"Queued {section_name} updates for {self.session_id}: "
                f"{list(updates.keys())}"
            )

    def flush(self) -> None:
        """
        Flush all cached changes to the persistent store.

        This is called once at end of request lifecycle to commit
        all accumulated changes in a single remote dictionary operation.
        """
        from ..utils.state_manager import get_session_lock

        lock = get_session_lock(self.session_id)
        with lock:
            with self._lock:
                if self._invalidated:
                    logger.info(
                        f"Skipping flush for invalidated batch cache for {self.session_id}"
                    )
                    return
                if self._dirty and self._cached_data is not None:
                    # Defensive merge: if persistent store was updated out-of-band with fresh chips,
                    # ensure we do not overwrite them with older/empty chip_state.
                    if self.session_id in self.store:
                        store_data = self.store[self.session_id]
                        if isinstance(store_data, dict) and "chip_state" in store_data:
                            store_chips = store_data.get("chip_state", {})
                            cached_chips = self._cached_data.get("chip_state", {})
                            store_has_chips = store_chips.get("current_chips") is not None
                            cached_has_chips = cached_chips.get("current_chips") is not None
                            if store_has_chips and not cached_has_chips:
                                self._cached_data["chip_state"] = store_chips
                            elif store_has_chips and cached_has_chips:
                                store_seq = store_chips.get("generation_seq", 0)
                                cached_seq = cached_chips.get("generation_seq", 0)
                                if store_seq >= cached_seq:
                                    self._cached_data["chip_state"] = store_chips

                    # Single write-back to remote store
                    self.store[self.session_id] = self._cached_data
                    self._dirty = False
                    logger.info(f"Flushed batch state changes for {self.session_id}")
                elif not self._dirty:
                    logger.debug(f"No changes to flush for {self.session_id}")


# Thread-local storage for current batch cache
_batch_context = threading.local()

# Active batch caches keyed by session_id across threads
_active_session_caches: dict[str, list[BatchStateCache]] = {}
_active_caches_lock = threading.Lock()


def get_batch_cache_for_session(session_id: str) -> BatchStateCache | None:
    """
    Get the active batch cache for a session across any thread.

    Args:
        session_id: Unique identifier for the user session.

    Returns:
        The active BatchStateCache for this session if one exists, else None.
    """
    with _active_caches_lock:
        caches = _active_session_caches.get(session_id)
        return caches[-1] if caches else None


def clear_batch_cache_for_session(session_id: str) -> None:
    """
    Remove and invalidate all registered batch caches for a session (e.g. on reset or cleanup).

    Args:
        session_id: Unique identifier for the user session.
    """
    with _active_caches_lock:
        caches = _active_session_caches.pop(session_id, [])
    for cache in caches:
        cache.invalidate()


@contextmanager
def batch_state_commits(session_id: str, store: MutableMapping):
    """
    Context manager for request-scoped batch state commits.

    This context manager creates a BatchStateCache for the duration of the
    request, making it available to state_manager functions. All state
    operations within this context will be cached and flushed once at the end.

    Args:
        session_id: Unique identifier for the user session
        store: Mutable mapping (dict or modal.Dict) for persistent storage

    Yields:
        BatchStateCache instance for the request
    """
    if hasattr(_batch_context, 'cache'):
        raise RuntimeError(
            "Nested batch_state_commits context detected - "
            "nesting is not supported"
        )

    cache = BatchStateCache(session_id, store)
    _batch_context.cache = cache
    with _active_caches_lock:
        _active_session_caches.setdefault(session_id, []).append(cache)

    try:
        logger.debug(f"Starting batch state commits context for {session_id}")
        yield cache
    finally:
        try:
            cache.flush()
        except Exception as e:
            logger.error(f"Failed to flush batch state changes for {session_id}: {e}")
            raise
        finally:
            with _active_caches_lock:
                if session_id in _active_session_caches:
                    try:
                        _active_session_caches[session_id].remove(cache)
                    except ValueError:
                        pass
                    if not _active_session_caches[session_id]:
                        _active_session_caches.pop(session_id, None)
            # Clean up thread-local storage
            if hasattr(_batch_context, 'cache'):
                delattr(_batch_context, 'cache')
            logger.debug(f"Ended batch state commits context for {session_id}")



def get_current_batch_cache() -> BatchStateCache | None:
    """
    Get the current batch cache if within a batch_state_commits context.

    Returns:
        Current BatchStateCache instance or None if not in context
    """
    return getattr(_batch_context, 'cache', None)


def is_in_batch_context() -> bool:
    """
    Check if currently executing within a batch_state_commits context.

    Returns:
        True if in batch context, False otherwise
    """
    return hasattr(_batch_context, 'cache')
