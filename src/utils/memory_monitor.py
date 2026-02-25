"""Memory monitoring utility for MayaMCP on Modal Labs."""

import os
import threading
import time
from typing import Any, Dict, Optional, Tuple

from ..config.logging_config import get_logger

logger = get_logger(__name__)


class MemoryMonitor:
    """Container memory monitoring with pressure detection."""

    def __init__(self, memory_threshold: float = 0.8):
        """
        Initialize memory monitor.

        Args:
            memory_threshold: Alert threshold (0.0-1.0), default 0.8 (80%)
        """
        self.memory_threshold = memory_threshold
        self._lock = threading.Lock()
        self._last_alert_time = 0
        self._alert_cooldown = 300  # 5 minutes between alerts

    def read_cgroup_memory(self) -> Tuple[Optional[int], Optional[int]]:
        """
        Read container memory usage and limit from cgroups.

        Returns:
            Tuple of (current_bytes, limit_bytes) or (None, None) if unavailable
        """
        try:
            # Current usage
            current = None
            limit = None
            
            for p in ("/sys/fs/cgroup/memory.current", "/sys/fs/cgroup/memory.usage_in_bytes"):
                if os.path.exists(p):
                    with open(p) as f:
                        raw = f.read().strip()
                        if p == "/sys/fs/cgroup/memory.current":
                            current = int(raw)
                        elif p == "/sys/fs/cgroup/memory.usage_in_bytes":
                            current = int(raw)
                        elif raw.lower() == "max":
                            # Treat "max" as unlimited
                            limit = None
                        elif raw.lower() == "unknown":
                            # Treat unknown as unbounded
                            limit = None
                        else:
                            # Parse numeric limit
                            try:
                                limit = int(raw)
                            except ValueError:
                                logger.warning(f"Invalid cgroup limit value: {raw}")
                                limit = None
                            break
            
            # Memory limit
            for p in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory.limit_in_bytes"):
                if os.path.exists(p):
                    with open(p) as f:
                        raw = f.read().strip()
                        if raw.lower() == "max":
                            # "max" means unlimited - treat as None
                            limit = None
                        elif raw.lower() == "unknown":
                            # "unknown" means unbounded - treat as None
                            limit = None
                        else:
                            # Parse numeric limit
                            try:
                                limit = int(raw)
                            except ValueError:
                                logger.warning(f"Invalid cgroup limit value: {raw}")
                                limit = None
                            break
            
            return current, limit
        except Exception:
            logger.debug("Failed to read cgroup memory", exc_info=True)
            return None, None

    def get_memory_usage_mb(self) -> Optional[float]:
        """
        Get current memory usage in MB.

        Returns:
            Memory usage in MB or None if unavailable
        """
        current_bytes, _ = self.read_cgroup_memory()
        if current_bytes is not None:
            return current_bytes / (1024 * 1024)
        return None

    def get_memory_utilization(self) -> Optional[float]:
        """
        Get memory utilization as ratio (0.0-1.0).
        """
        current_bytes, limit_bytes = self.read_cgroup_memory()
        if current_bytes is not None and limit_bytes is not None and limit_bytes > 0:
            return current_bytes / limit_bytes
        else:
            return None
    
    def is_memory_available(self, required_mb: float = 100) -> bool:
        """
        Check if sufficient memory is available for new session.
        """
        current_bytes, limit_bytes = self.read_cgroup_memory()
        if current_bytes is not None and limit_bytes is not None:
            current_mb = current_bytes / (1024 * 1024)
            limit_mb = limit_bytes / (1024 * 1024)
            return current_mb >= required_mb
        else:
            return False
    
    def check_memory_pressure(self) -> Dict[str, Any]:
        """
        Check for memory pressure and return status.
        """
        current_bytes, limit_bytes = self.read_cgroup_memory()
        if current_bytes is not None and limit_bytes is not None:
            current_mb = current_bytes / (1024 * 1024)
            limit_mb = limit_bytes / (1024 * 1024)
            utilization = current_mb / limit_mb
            pressure = utilization >= self.memory_threshold
            
            # Check cooldown period to avoid alert spam
            current_time = time.time()
            if pressure and (current_time - self._last_alert_time) > self._alert_cooldown:
                with self._lock:
                    if (current_time - self._last_alert_time) > self._alert_cooldown:
                        logger.debug(f"Memory check: {current_mb:.1f}MB/{limit_mb:.1f}MB "
                                   f"({utilization:.1%}), available: {limit_mb - current_mb:.1f}MB")
                        self._last_alert_time = current_time
            
            available_mb = limit_mb - current_mb
            return {
                "pressure": pressure,
                "utilization": utilization,
                "available_mb": available_mb,
                "current_mb": current_mb,
                "limit_mb": limit_mb,
                "message": f"Memory utilization: {utilization:.1%}%, available: {available_mb:.1f}MB"
            }
        else:
            return {
                "pressure": False,
                "utilization": None,
                "available_mb": None,
                "current_mb": None,
                "limit_mb": None,
                "message": "Memory monitoring unavailable"
            }
    
        return {
            "pressure": pressure,
            "utilization": utilization,
            "current_mb": current_mb,
            "limit_mb": limit_mb,
            "message": f"Memory utilization: {utilization:.1%}" if pressure else "Memory usage normal"
        }

    def get_memory_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive memory metrics for monitoring.
        
        Returns:
            Dictionary with memory metrics
        """
        current_bytes, limit_bytes = self.read_cgroup_memory()
        if current_bytes is None or limit_bytes is None:
            return {
                "current_bytes": None,
                "limit_bytes": None,
                "current_mb": None,
                "limit_mb": None,
                "utilization": None,
                "available_mb": None,
                "pressure": None,
                "monitoring_available": False
            }
        
        current_mb = current_bytes / (1024 * 1024)
        limit_mb = limit_bytes / (1024 * 1024)
        
        # Prevent division by zero
        if limit_mb <= 0:
            return {
                "current_bytes": current_bytes,
                "limit_bytes": limit_bytes,
                "current_mb": current_mb,
                "limit_mb": limit_mb,
                "utilization": 0.0,
                "available_mb": 0.0,
                "pressure": True,
                "monitoring_available": False
            }
        
        utilization = current_mb / limit_mb
        available_mb = limit_mb - current_mb
        pressure = utilization >= self.memory_threshold
        
        return {
            "current_bytes": current_bytes,
            "limit_bytes": limit_bytes,
            "current_mb": current_mb,
            "limit_mb": limit_mb,
            "utilization": utilization,
            "available_mb": available_mb,
            "pressure": pressure,
            "monitoring_available": True
        }


# Global memory monitor instance
_memory_monitor: Optional[MemoryMonitor] = None


def get_memory_monitor() -> MemoryMonitor:
    """Get or create the global memory monitor instance."""
    global _memory_monitor
    if _memory_monitor is None:
        # Read threshold from environment
        try:
            threshold = float(os.getenv("MAYA_CONTAINER_MEMORY_THRESHOLD", "0.8"))
        except ValueError:
            logger.warning(
                "Invalid MAYA_CONTAINER_MEMORY_THRESHOLD value; defaulting to 0.8"
            )
            threshold = 0.8
        threshold = max(0.1, min(0.95, threshold))
        _memory_monitor = MemoryMonitor(memory_threshold=threshold)
        logger.info(f"Memory monitor initialized with threshold: {threshold:.1%}")
    return _memory_monitor


def check_memory_health() -> bool:
    """
    Quick health check for memory status.

    Returns:
        True if memory is healthy, False otherwise
    """
    monitor = get_memory_monitor()
    pressure_status = monitor.check_memory_pressure()
    return not pressure_status["pressure"]
