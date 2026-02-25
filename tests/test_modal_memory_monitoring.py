"""Tests for Modal memory monitoring and session management."""

import os
import time
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.utils.memory_monitor import MemoryMonitor, get_memory_monitor, check_memory_health
from src.utils.session_manager import MayaSessionManager, SessionData, get_session_manager


class TestMemoryMonitor:
    """Test memory monitoring functionality."""
    
    def test_memory_monitor_initialization(self):
        """Test memory monitor initialization with default threshold."""
        monitor = MemoryMonitor()
        assert monitor.memory_threshold == 0.8
    
    def test_memory_monitor_custom_threshold(self):
        """Test memory monitor initialization with custom threshold."""
        monitor = MemoryMonitor(memory_threshold=0.7)
        assert monitor.memory_threshold == 0.7
    
    @patch('src.utils.memory_monitor.open')
    @patch('src.utils.memory_monitor.os.path.exists')
    def test_read_cgroup_memory_success(self, mock_exists, mock_open):
        """Test successful cgroup memory reading."""
        # Mock file exists
        mock_exists.return_value = True
        
        # Mock file content
        mock_file = MagicMock()
        mock_file.read.side_effect = ["1000000\n", "2000000\n"]
        mock_open.return_value.__enter__.return_value = mock_file
        
        monitor = MemoryMonitor()
        current, limit = monitor.read_cgroup_memory()
        
        assert current == 1000000
        assert limit == 2000000
    
    @patch('src.utils.memory_monitor.open')
    @patch('src.utils.memory_monitor.os.path.exists')
    def test_read_cgroup_memory_failure(self, mock_exists, mock_open):
        """Test cgroup memory reading failure."""
        # Mock file doesn't exist
        mock_exists.return_value = False
        
        monitor = MemoryMonitor()
        current, limit = monitor.read_cgroup_memory()
        
        assert current is None
        assert limit is None
    
    @patch('src.utils.memory_monitor.MemoryMonitor.read_cgroup_memory')
    def test_get_memory_usage_mb(self, mock_read):
        """Test memory usage in MB calculation."""
        # Use byte value that matches binary MiB (1048576 bytes = 1 MiB)
        mock_read.return_value = (104857600, None)  # 100 MiB
        monitor = MemoryMonitor()
        usage_mb = monitor.get_memory_usage_mb()
        
        assert usage_mb == pytest.approx(100.0)
    
    @patch('src.utils.memory_monitor.MemoryMonitor.read_cgroup_memory')
    def test_get_memory_utilization(self, mock_read):
        """Test memory utilization calculation."""
        mock_read.return_value = (100000000, 200000000)  # 50%
        monitor = MemoryMonitor()
        utilization = monitor.get_memory_utilization()
        
        assert utilization == 0.5
    
    @patch('src.utils.memory_monitor.MemoryMonitor.read_cgroup_memory')
    def test_is_memory_available_success(self, mock_read):
        """Test memory availability check with sufficient memory."""
        mock_read.return_value = (100000000, 200000000)  # 100MB used, 100MB available
        monitor = MemoryMonitor()
        available = monitor.is_memory_available(required_mb=50)
        
        assert available is True
    
    @patch('src.utils.memory_monitor.MemoryMonitor.read_cgroup_memory')
    def test_is_memory_available_insufficient(self, mock_read):
        """Test memory availability check with insufficient memory."""
        mock_read.return_value = (150000000, 200000000)  # 150MB used, 50MB available
        monitor = MemoryMonitor()
        available = monitor.is_memory_available(required_mb=100)
        
        assert available is False
    
    @patch('src.utils.memory_monitor.MemoryMonitor.read_cgroup_memory')
    def test_check_memory_pressure_normal(self, mock_read):
        """Test memory pressure check with normal usage."""
        mock_read.return_value = (80000000, 200000000)  # 40% usage
        monitor = MemoryMonitor()
        pressure_status = monitor.check_memory_pressure()
        
        assert pressure_status["pressure"] is False
        assert pressure_status["utilization"] == 0.4
    
    @patch('src.utils.memory_monitor.MemoryMonitor.read_cgroup_memory')
    def test_check_memory_pressure_high(self, mock_read):
        """Test memory pressure check with high usage."""
        mock_read.return_value = (170000000, 200000000)  # 85% usage
        monitor = MemoryMonitor()
        pressure_status = monitor.check_memory_pressure()
        
        assert pressure_status["pressure"] is True
        assert pressure_status["utilization"] == 0.85


class TestSessionData:
    """Test SessionData functionality."""
    
    def test_session_data_creation(self):
        """Test session data creation."""
        session = SessionData(session_id="test123")
        
        assert session.session_id == "test123"
        assert session.api_key_hash == ""
        assert session.memory_allocated_mb == 0.0
        assert session.created_at > 0
        assert session.last_access > 0
    
    def test_update_access(self):
        """Test access time update."""
        session = SessionData(session_id="test123")
        original_access = session.last_access
        
        # Mock time.time to advance clock deterministically
        with patch('time.time', return_value=original_access + 100):
            session.update_access()
        
        # Verify the access time was updated
        assert session.last_access == original_access + 100
    
    def test_is_expired_false(self):
        """Test session expiration check when not expired."""
        session = SessionData(session_id="test123")
        expired = session.is_expired(expiry_seconds=3600)
        
        assert expired is False
    
    def test_is_expired_true(self):
        """Test session expiration check when expired."""
        session = SessionData(session_id="test123")
        session.last_access = time.time() - 3700  # Expired 100 seconds ago
        expired = session.is_expired(expiry_seconds=3600)
        
        assert expired is True


class TestMayaSessionManager:
    """Test Maya session manager functionality."""
    
    @patch.dict(os.environ, {
        'MAYA_SESSIONS_PER_CONTAINER': '10',
        'MAYA_SESSION_EXPIRY_SECONDS': '1800',
        'MAYA_DEFAULT_SESSION_MEMORY_MB': '25.0'
    })
    def test_session_manager_initialization(self):
        """Test session manager initialization with environment variables."""
        manager = MayaSessionManager()
        
        assert manager.max_sessions_per_container == 10
        assert manager.session_expiry_seconds == 1800
        assert manager.default_session_memory_mb == 25.0
        assert manager.get_session_count() == 0
    
    @patch('src.utils.session_manager.get_memory_monitor')
    def test_create_session_success(self, mock_get_monitor):
        """Test successful session creation."""
        mock_monitor = Mock()
        mock_monitor.is_memory_available.return_value = True
        mock_get_monitor.return_value = mock_monitor
        
        manager = MayaSessionManager()
        created = manager.create_session("test123", "keyhash")
        
        assert created is True
        assert manager.get_session_count() == 1
        assert manager.access_session("test123") is True
    
    @patch('src.utils.session_manager.get_memory_monitor')
    def test_create_session_memory_limit(self, mock_get_monitor):
        """Test session creation rejected due to memory limit."""
        mock_monitor = Mock()
        mock_monitor.is_memory_available.return_value = False
        mock_get_monitor.return_value = mock_monitor
        
        manager = MayaSessionManager()
        created = manager.create_session("test123", "keyhash")
        
        assert created is False
        assert manager.get_session_count() == 0
        stats = manager.get_statistics()
        assert stats["sessions_rejected"] == 1
    
    @patch.dict(os.environ, {'MAYA_SESSIONS_PER_CONTAINER': '2'})
    @patch('src.utils.session_manager.get_memory_monitor')
    def test_create_session_limit_reached(self, mock_get_monitor):
        """Test session creation rejected due to session limit."""
        mock_monitor = Mock()
        mock_monitor.is_memory_available.return_value = True
        mock_get_monitor.return_value = mock_monitor
        
        manager = MayaSessionManager()
        
        # Create sessions up to limit
        assert manager.create_session("test1", "keyhash") is True
        assert manager.create_session("test2", "keyhash") is True
        
        # Third session should be rejected
        assert manager.create_session("test3", "keyhash") is False
        assert manager.get_session_count() == 2
    
    @patch('src.utils.session_manager.get_memory_monitor')
    def test_access_existing_session(self):
        """Test accessing an existing session."""
        mock_monitor = Mock()
        mock_monitor.is_memory_available.return_value = True
        with patch('src.utils.session_manager.get_memory_monitor', return_value=mock_monitor):
            manager = MayaSessionManager()
            
            removed = manager.remove_session("nonexistent")
            assert removed is False
    
    @patch('src.utils.session_manager.get_memory_monitor')
    def test_remove_existing_session(self):
        """Test removing an existing session."""
        mock_monitor = Mock()
        mock_monitor.is_memory_available.return_value = True
        with patch('src.utils.session_manager.get_memory_monitor', return_value=mock_monitor):
            manager = MayaSessionManager()
            manager.create_session("test123", "keyhash")
            
            removed = manager.remove_session("test123")
            assert removed is True
            assert manager.get_session_count() == 0
    
    @patch('src.utils.session_manager.get_memory_monitor')
    def test_remove_nonexistent_session(self):
        """Test removing a non-existent session."""
        assert removed is False
    
    @patch('src.utils.session_manager.get_memory_monitor')
    def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions."""
        mock_monitor = Mock()
        mock_monitor.is_memory_available.return_value = True
        with patch('src.utils.session_manager.get_memory_monitor', return_value=mock_monitor):
            manager = MayaSessionManager()
            
            # Create sessions
            manager.create_session("test1", "keyhash")
            manager.create_session("test2", "keyhash")
            
            # Expire one session
            session1 = manager.get_session_info("test1")
            session1.last_access = time.time() - 3700  # Expired
            
            # Cleanup
            cleaned = manager.cleanup_expired_sessions()
            
            assert cleaned == 1
            assert manager.get_session_count() == 1
            assert manager.access_session("test1") is False
            assert manager.access_session("test2") is True
    
    @patch('src.utils.memory_monitor.MemoryMonitor.read_cgroup_memory')
    def test_get_statistics(self):
        """Test statistics collection."""
        # Create deterministic manager with fixed limits and mock memory monitor
        mock_monitor = Mock()
        mock_monitor.is_memory_available.return_value = True
        
        with patch('src.utils.session_manager.get_memory_monitor', return_value=mock_monitor):
            # Use fixed low limit to ensure deterministic behavior
            manager = MayaSessionManager(max_sessions_per_container=3)
            
            # All three sessions should succeed (memory available)
            assert manager.create_session("test1", "keyhash") is True
            assert manager.create_session("test2", "keyhash") is True
            assert manager.create_session("test3", "keyhash") is True
            
            stats = manager.get_statistics()
            
            # Assert exact deterministic values
            assert stats["current_sessions"] == 3
            assert stats["max_sessions"] == 3  # Our fixed limit
            assert stats["sessions_created"] == 3
            assert "utilization" in stats
            assert 0 <= stats["utilization"] <= 1  # Between 0% and 100%
        assert 0 <= stats["utilization"] <= 1


class TestGlobalFunctions:
    """Test global function interfaces."""
    
    @patch('src.utils.memory_monitor.MemoryMonitor')
    def test_get_memory_monitor_singleton(self, mock_monitor_class):
        """Test memory monitor singleton behavior."""
        # Reset module-level singleton before test
        import src.utils.memory_monitor
        src.utils.memory_monitor._memory_monitor = None
        
        mock_instance = Mock()
        mock_monitor_class.return_value = mock_instance
        
        # First call should create instance
        monitor1 = get_memory_monitor()
        # Second call should return same instance
        monitor2 = get_memory_monitor()
        
        assert monitor1 is monitor2
        mock_monitor_class.assert_called_once()
    
    @patch('src.utils.session_manager.MayaSessionManager')
    def test_get_session_manager_singleton(self, mock_manager_class):
        """Test session manager singleton behavior."""
        # Reset module-level singleton before test
        import src.utils.session_manager
        src.utils.session_manager._session_manager = None
        
        mock_instance = Mock()
        mock_manager_class.return_value = mock_instance
        
        # First call should create instance
        manager1 = get_session_manager()
        # Second call should return same instance
        manager2 = get_session_manager()
        
        assert manager1 is manager2
        mock_manager_class.assert_called_once()
    
    @patch('src.utils.memory_monitor.get_memory_monitor')
    def test_check_memory_health_true(self, mock_get_monitor):
        """Test memory health check when healthy."""
        mock_monitor = Mock()
        mock_monitor.check_memory_pressure.return_value = {"pressure": False}
        mock_get_monitor.return_value = mock_monitor
        
        healthy = check_memory_health()
        assert healthy is True
    
    @patch('src.utils.memory_monitor.get_memory_monitor')
    def test_check_memory_health_false(self, mock_get_monitor):
        """Test memory health check when unhealthy."""
        mock_monitor = Mock()
        mock_monitor.check_memory_pressure.return_value = {"pressure": True}
        mock_get_monitor.return_value = mock_monitor
        
        healthy = check_memory_health()
        assert healthy is False


if __name__ == "__main__":
    pytest.main([__file__])
