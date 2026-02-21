"""Batch state cache for optimizing remote dictionary operations.

This module implements a request-scoped cache that absorbs all state
reads/writes within a request lifecycle, flushing to modal.Dict
exactly once at the end. This addresses performance issue
identified in PERFORMANCE_ANALYSIS.md #2.
"""

import threading
from contextlib import contextmanager
from typing import Any, Dict, MutableMapping, Optional

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
        self._cached_data: Optional[Dict[str, Any]] = None
        self._dirty = False  # Track if we have unsaved changes
        self._lock = threading.Lock()

    def _load_data(self) -> Dict[str, Any]:
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

    def get_session_data(self) -> Dict[str, Any]:
        """
        Get cached session data, loading from store if necessary.

        Returns:
            Session data dictionary
        """
        with self._lock:
            return self._load_data().copy()

    def get_section(self, section_name: str) -> Dict[str, Any]:
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
            return data[section_name].copy()

    def update_session_data(self, updates: Dict[str, Any]) -> None:
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

    def update_section(self, section_name: str, updates: Dict[str, Any]) -> None:
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
        with self._lock:
            if self._dirty and self._cached_data is not None:
                # Single write-back to remote store
                self.store[self.session_id] = self._cached_data
                self._dirty = False
                logger.info(f"Flushed batch state changes for {self.session_id}")
            elif not self._dirty:
                logger.debug(f"No changes to flush for {self.session_id}")


# Thread-local storage for current batch cache
_batch_context = threading.local()


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
        logger.warning(
            "Nested batch_state_commits context detected - "
            "using innermost context"
        )

    cache = BatchStateCache(session_id, store)
    _batch_context.cache = cache

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
            # Clean up thread-local storage
            if hasattr(_batch_context, 'cache'):
                delattr(_batch_context, 'cache')
            logger.debug(f"Ended batch state commits context for {session_id}")


def get_current_batch_cache() -> Optional[BatchStateCache]:
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
