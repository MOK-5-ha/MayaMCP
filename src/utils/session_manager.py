"""Session management with memory-aware admission control for MayaMCP on Modal."""

import os
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, Set

from ..config.logging_config import get_logger
from .memory_monitor import get_memory_monitor

logger = get_logger(__name__)


@dataclass
class SessionData:
    """Session metadata for tracking and management."""
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_access: float = field(default_factory=time.time)
    api_key_hash: str = ""
    memory_allocated_mb: float = 0.0
    
    def update_access(self):
        """Update last access time to current time."""
        self.last_access = time.time()
    
    def is_expired(self, expiry_seconds: int = 3600) -> bool:
        """Check if session has expired."""
        return time.time() - self.last_access > expiry_seconds


class MayaSessionManager:
    """Memory-aware session management with admission control."""
    
    def __init__(self):
        """Initialize session manager with configuration from environment."""
        # Session limits from environment
        self.max_sessions_per_container = int(
            os.getenv("MAYA_SESSIONS_PER_CONTAINER", "100")
        )
        self.session_expiry_seconds = int(
            os.getenv("MAYA_SESSION_EXPIRY_SECONDS", "3600")
        )
        self.default_session_memory_mb = float(
            os.getenv("MAYA_DEFAULT_SESSION_MEMORY_MB", "50.0")
        )
        
        # Session storage
        self._sessions: Dict[str, SessionData] = {}
        self._lock = threading.RLock()
        
        # Memory monitor for admission control
        self._memory_monitor = get_memory_monitor()
        
        # Statistics
        self._sessions_created = 0
        self._sessions_rejected = 0
        self._sessions_expired = 0
        
        logger.info(
            f"SessionManager initialized: max_sessions={self.max_sessions_per_container}, "
            f"expiry={self.session_expiry_seconds}s, "
            f"default_memory={self.default_session_memory_mb}MB"
        )
    
    def create_session(self, session_id: str, api_key_hash: str = "") -> bool:
        """
        Create a new session with memory-aware admission control.
        
        Args:
            session_id: Unique session identifier
            api_key_hash: Hash of the API key for tracking
            
        Returns:
            True if session created successfully, False if rejected
        """
        with self._lock:
            # Check if session already exists
            if session_id in self._sessions:
                self._sessions[session_id].update_access()
                logger.debug(f"Session {session_id[:8]} accessed (existing)")
                return True
            
            # Check session limit
            if len(self._sessions) >= self.max_sessions_per_container:
                logger.warning(
                    f"Session limit reached: {len(self._sessions)}/{self.max_sessions_per_container}"
                )
                self._sessions_rejected += 1
                return False
            
            # Check memory availability
            if not self._memory_monitor.is_memory_available(self.default_session_memory_mb):
                memory_metrics = self._memory_monitor.get_memory_metrics()
                logger.warning(
                    f"Insufficient memory for new session: "
                    f"{memory_metrics['available_mb']:.1f}MB available, "
                    f"{self.default_session_memory_mb}MB required"
                )
                self._sessions_rejected += 1
                return False
            
            # Create session
            session = SessionData(
                session_id=session_id,
                api_key_hash=api_key_hash,
                memory_allocated_mb=self.default_session_memory_mb
            )
            
            self._sessions[session_id] = session
            self._sessions_created += 1
            
            logger.info(
                f"Session created: {session_id[:8]} "
                f"(total: {len(self._sessions)}/{self.max_sessions_per_container})"
            )
            return True
    
    def access_session(self, session_id: str) -> bool:
        """
        Record session access and validate session exists.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session exists and was accessed, False otherwise
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.update_access()
                return True
            return False
    
    def remove_session(self, session_id: str) -> bool:
        """
        Remove a session from management.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was removed, False if not found
        """
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session:
                logger.info(
                    f"Session removed: {session_id[:8]} "
                    f"(remaining: {len(self._sessions)})"
                )
                return True
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions and return count of cleaned sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        expired_sessions = []
        
        with self._lock:
            for session_id, session in self._sessions.items():
                if session.is_expired(self.session_expiry_seconds):
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                self._sessions.pop(session_id, None)
                self._sessions_expired += 1
        
        if expired_sessions:
            logger.info(
                f"Cleaned up {len(expired_sessions)} expired sessions "
                f"(remaining: {len(self._sessions)})"
            )
        
        return len(expired_sessions)
    
    def get_session_count(self) -> int:
        """Get current number of active sessions."""
        with self._lock:
            return len(self._sessions)
    
    def get_session_info(self, session_id: str) -> Optional[SessionData]:
        """Get session information without updating access time."""
        with self._lock:
            return self._sessions.get(session_id)
    
    def get_all_session_ids(self) -> Set[str]:
        """Get all active session IDs."""
        with self._lock:
            return set(self._sessions.keys())
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get session manager statistics for monitoring.
        
        Returns:
            Dictionary with session statistics
        """
        with self._lock:
            current_sessions = len(self._sessions)
            
        return {
            "current_sessions": current_sessions,
            "max_sessions": self.max_sessions_per_container,
            "sessions_created": self._sessions_created,
            "sessions_rejected": self._sessions_rejected,
            "sessions_expired": self._sessions_expired,
            "utilization": current_sessions / self.max_sessions_per_container,
            "expiry_seconds": self.session_expiry_seconds,
            "default_memory_mb": self.default_session_memory_mb
        }
    
    def get_memory_status(self) -> Dict[str, any]:
        """
        Get memory status for admission decisions.
        
        Returns:
            Dictionary with memory status information
        """
        memory_metrics = self._memory_monitor.get_memory_metrics()
        stats = self.get_statistics()
        
        return {
            "memory_available": memory_metrics["available_mb"],
            "memory_utilization": memory_metrics["utilization"],
            "memory_pressure": memory_metrics["pressure"],
            "sessions_per_container": stats["current_sessions"],
            "max_sessions_per_container": stats["max_sessions"],
            "estimated_session_memory": stats["default_memory_mb"],
            "can_create_session": (
                memory_metrics["available_mb"] >= stats["default_memory_mb"]
                and stats["current_sessions"] < stats["max_sessions"]
                and not memory_metrics["pressure"]
            )
        }


# Global session manager instance
_session_manager: Optional[MayaSessionManager] = None


def get_session_manager() -> MayaSessionManager:
    """Get or create the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = MayaSessionManager()
        logger.info("Global session manager initialized")
    return _session_manager


def cleanup_expired_sessions_background(interval_seconds: int = 300) -> threading.Thread:
    """
    Start background thread for cleaning up expired sessions.
    
    Args:
        interval_seconds: Cleanup interval in seconds (default: 5 minutes)
        
    Returns:
        The cleanup thread
    """
    def cleanup_loop():
        manager = get_session_manager()
        logger.info(f"Session cleanup thread started (interval: {interval_seconds}s)")
        
        while True:
            try:
                cleaned = manager.cleanup_expired_sessions()
                if cleaned > 0:
                    logger.info(f"Background cleanup removed {cleaned} expired sessions")
                time.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Session cleanup error: {e}", exc_info=True)
                time.sleep(interval_seconds)
    
    cleanup_thread = threading.Thread(
        target=cleanup_loop,
        name="session-cleanup",
        daemon=True
    )
    cleanup_thread.start()
    return cleanup_thread
