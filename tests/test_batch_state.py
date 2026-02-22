"""Tests for batch state commits functionality."""

import pytest
from unittest.mock import Mock, patch

from src.utils.batch_state import BatchStateCache, batch_state_commits, get_current_batch_cache, is_in_batch_context


class TestBatchStateCache:
    """Test cases for BatchStateCache class."""

    def test_init(self):
        """Test BatchStateCache initialization."""
        store = Mock()
        cache = BatchStateCache("test_session", store)
        
        assert cache.session_id == "test_session"
        assert cache.store == store
        assert cache._cached_data is None
        assert cache._dirty is False

    def test_load_data_initializes_from_store(self):
        """Test that _load_data initializes from store when cache is empty."""
        store = Mock()
        
        with patch('src.utils.batch_state._get_session_data') as mock_get_data:
            mock_get_data.return_value = {"test": "data"}
            
            cache = BatchStateCache("test_session", store)
            data = cache._load_data()
            
            mock_get_data.assert_called_once_with("test_session", store)
            assert data == {"test": "data"}
            assert cache._cached_data == {"test": "data"}

    def test_load_data_uses_cache(self):
        """Test that _load_data uses cached data when available."""
        store = Mock()
        cached_data = {"cached": "data"}
        
        cache = BatchStateCache("test_session", store)
        cache._cached_data = cached_data
        
        data = cache._load_data()
        assert data == cached_data

    def test_get_session_data_returns_copy(self):
        """Test that get_session_data returns a copy of cached data."""
        store = Mock()
        cached_data = {"test": "data"}
        
        cache = BatchStateCache("test_session", store)
        cache._cached_data = cached_data
        
        data = cache.get_session_data()
        assert data == cached_data
        assert data is not cached_data  # Should be a copy

    def test_update_session_data(self):
        """Test updating session data."""
        store = Mock()
        cache = BatchStateCache("test_session", store)
        cache._cached_data = {"existing": "data"}
        
        updates = {"new": "value"}
        cache.update_session_data(updates)
        
        assert cache._cached_data == {"existing": "data", "new": "value"}
        assert cache._dirty is True

    def test_get_section(self):
        """Test getting a specific section of data."""
        store = Mock()
        cached_data = {"conversation": {"turn": 1}, "payment": {"balance": 100}}
        
        cache = BatchStateCache("test_session", store)
        cache._cached_data = cached_data
        
        conversation = cache.get_section("conversation")
        assert conversation == {"turn": 1}
        assert conversation is not cached_data["conversation"]

    def test_get_section_missing_key(self):
        """Test getting a section that doesn't exist raises KeyError."""
        store = Mock()
        cached_data = {"conversation": {"turn": 1}}
        
        cache = BatchStateCache("test_session", store)
        cache._cached_data = cached_data
        
        with pytest.raises(KeyError, match="Section 'payment' not found"):
            cache.get_section("payment")

    def test_update_section(self):
        """Test updating a specific section of data."""
        store = Mock()
        cached_data = {"conversation": {"turn": 1}, "payment": {"balance": 100}}
        
        cache = BatchStateCache("test_session", store)
        cache._cached_data = cached_data
        
        cache.update_section("payment", {"balance": 200})
        
        assert cache._cached_data["payment"] == {"balance": 200}
        assert cache._dirty is True

    def test_flush_writes_to_store_when_dirty(self):
        """Test that flush writes to store when data is dirty."""
        store = Mock()
        cached_data = {"test": "data"}
        
        cache = BatchStateCache("test_session", store)
        cache._cached_data = cached_data
        cache._dirty = True
        
        cache.flush()
        
        store.__setitem__.assert_called_once_with("test_session", cached_data)
        assert cache._dirty is False

    def test_flush_skips_write_when_clean(self):
        """Test that flush skips write when data is clean."""
        store = Mock()
        cached_data = {"test": "data"}
        
        cache = BatchStateCache("test_session", store)
        cache._cached_data = cached_data
        cache._dirty = False
        
        cache.flush()
        
        store.__setitem__.assert_not_called()


class TestBatchStateCommits:
    """Test cases for batch_state_commits context manager."""

    def test_context_manager_sets_and_clears_cache(self):
        """Test that context manager sets and clears batch cache."""
        store = Mock()
        
        with batch_state_commits("test_session", store) as cache:
            assert is_in_batch_context() is True
            assert get_current_batch_cache() is cache
            assert isinstance(cache, BatchStateCache)
            assert cache.session_id == "test_session"
            assert cache.store == store
        
        # Context should be cleared after exiting
        assert is_in_batch_context() is False
        assert get_current_batch_cache() is None

    def test_context_manager_flushes_on_exit(self):
        """Test that context manager flushes cache on exit."""
        store = Mock()
        cached_data = {"test": "data"}
        
        with patch('src.utils.batch_state._get_session_data') as mock_get_data:
            mock_get_data.return_value = cached_data
            
            with batch_state_commits("test_session", store) as cache:
                cache.update_session_data({"updated": True})
            
            # Should have been flushed
            store.__setitem__.assert_called_once_with("test_session", {"test": "data", "updated": True})

    def test_nested_context_uses_innermost(self):
        """Test that nested contexts use the innermost one."""
        store = Mock()
        
        with batch_state_commits("outer", store) as outer_cache:
            assert get_current_batch_cache() is outer_cache
            
            with batch_state_commits("inner", store) as inner_cache:
                assert get_current_batch_cache() is inner_cache
            
            # Should revert to outer after inner exits
            assert get_current_batch_cache() is outer_cache
        
        # Should be cleared after outer exits
        assert get_current_batch_cache() is None

    def test_context_manager_clears_on_exception(self):
        """Test that context manager clears cache and propagates exceptions."""
        store = Mock()
        
        with pytest.raises(ValueError):
            with batch_state_commits("test_session", store) as cache:
                # Should be in context inside the block
                assert is_in_batch_context() is True
                assert get_current_batch_cache() is cache
                
                # Raise an exception to test cleanup
                raise ValueError("Test exception")
        
        # Context should be cleared after exception
        assert is_in_batch_context() is False
        assert get_current_batch_cache() is None


if __name__ == "__main__":
    pytest.main([__file__])
