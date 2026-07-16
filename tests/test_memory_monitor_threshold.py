import os
import pytest
from unittest.mock import patch
import src.utils.memory_monitor
from src.utils.memory_monitor import get_memory_monitor

def test_get_memory_monitor_clamping_warning(caplog):
    """Test that get_memory_monitor logs a warning when clamping the threshold."""
    # Isolate module-level singleton
    with patch.object(src.utils.memory_monitor, '_memory_monitor', None):
        with patch.dict(os.environ, {"MAYA_CONTAINER_MEMORY_THRESHOLD": "1.5"}):
            monitor = get_memory_monitor()
            
            # Verify threshold was clamped to 0.95
            assert monitor.memory_threshold == 0.95
            
            # Verify warning was logged
            assert any(
                "MAYA_CONTAINER_MEMORY_THRESHOLD 1.5 is outside [0.1, 0.95] range; clamping to 0.95"
                in record.message
                for record in caplog.records
                if record.levelname == "WARNING"
            )

def test_get_memory_monitor_no_clamping_no_warning(caplog):
    """Test that get_memory_monitor does not log a warning when threshold is in range."""
    # Isolate module-level singleton
    with patch.object(src.utils.memory_monitor, '_memory_monitor', None):
        with patch.dict(os.environ, {"MAYA_CONTAINER_MEMORY_THRESHOLD": "0.7"}):
            monitor = get_memory_monitor()
            
            # Verify threshold was not clamped
            assert monitor.memory_threshold == 0.7
            
            # Verify no warning was logged for clamping
            assert not any(
                "is outside [0.1, 0.95] range"
                in record.message
                for record in caplog.records
                if record.levelname == "WARNING"
            )

if __name__ == "__main__":
    pytest.main([__file__])
