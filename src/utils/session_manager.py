"""Session management with memory-aware admission control for MayaMCP on Modal."""

import os
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Any

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
    
    def _can_admit_session(self, memory_metrics: Dict[str, Any], stats: Dict[str, Any]) -> bool:
        """
        Helper function to determine if a new session can be admitted.
        
        Args:
            memory_metrics: Memory monitoring metrics
            stats: Session statistics
            
        Returns:
            True if session can be admitted, False otherwise
        """
        return (
            memory_metrics["available_mb"] >= stats["default_memory_mb"]
            and stats["current_sessions"] < stats["max_sessions"]
            and not memory_metrics["pressure"]
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
            
            # Get admission status using helper
            memory_metrics = self._memory_monitor.get_memory_metrics()
            stats = self.get_statistics()
            
            if not self._can_admit_session(memory_metrics, stats):
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
            
            # Capture remaining count while still inside lock
            remaining_count = len(self._sessions)
            
            for session_id in expired_sessions:
                self._sessions.pop(session_id, None)
                self._sessions_expired += 1
        
        if expired_sessions:
            logger.info(
                f"Cleaned up {len(expired_sessions)} expired sessions "
                f"(remaining: {remaining_count})"
            )
        
        return len(expired_sessions)
    
    def get_session_count(self) -> int:
        """Get current number of active sessions."""
        with self._lock:
            return len(self._sessions)
    
    def get_session_info(self, session_id: str) -> Optional[SessionData]:
        """Get session information without updating access time."""
        with self._lock:
            session_data = self._sessions.get(session_id)
            if session_data is None:
                return None
            
            # Return a shallow copy to prevent external mutation
            return SessionData(
                session_id=session_data.session_id,
                created_at=session_data.created_at,
                last_access=session_data.last_access,
                memory_mb=session_data.memory_mb,
                api_key_hash=session_data.api_key_hash
            )
    
    def get_all_session_ids(self) -> Set[str]:
        """Get all active session IDs."""
        with self._lock:
            return set(self._sessions.keys())
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get session manager statistics for monitoring.
        
        Returns:
            Dictionary with session statistics
        """
        with self._lock:
            current_sessions = len(self._sessions)
            sessions_created = self._sessions_created
            sessions_rejected = self._sessions_rejected
            sessions_expired = self._sessions_expired
            max_sessions_per_container = self.max_sessions_per_container
            session_expiry_seconds = self.session_expiry_seconds
            default_session_memory_mb = self.default_session_memory_mb
            
            # Compute utilization safely
            if max_sessions_per_container > 0:
                utilization = current_sessions / max_sessions_per_container
            else:
                utilization = 0.0
            
            return {
                "current_sessions": current_sessions,
                "max_sessions": max_sessions_per_container,
                "sessions_created": sessions_created,
                "sessions_rejected": sessions_rejected,
                "sessions_expired": sessions_expired,
                "utilization": utilization,
                "expiry_seconds": session_expiry_seconds,
                "default_session_memory_mb": default_session_memory_mb
            }
    
    def get_memory_status(self) -> Dict[str, Any]:
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
            "can_create_session": self._can_admit_session(memory_metrics, stats)
        }


# Global session manager instance
_session_manager: Optional[MayaSessionManager] = None
_session_manager_lock = threading.Lock()

# Cleanup thread management
_cleanup_thread: Optional[threading.Thread] = None
_cleanup_thread_lock = threading.Lock()

def get_session_manager() -> MayaSessionManager:
    """Get or create the global session manager instance."""
    global _session_manager
    with _session_manager_lock:
        if _session_manager is None:
            _session_manager = MayaSessionManager()
            logger.info("Global session manager initialized")
        logger.info("Global session manager initialized")
    return _session_manager


def cleanup_expired_sessions_background(
        interval_seconds: int = 300, stop_event: threading.Event, session_manager: Optional[MayaSessionManager] = None
    ) -> threading.Thread:
    """
    Start background thread for cleaning up expired sessions.
    
    Args:
        interval_seconds: Cleanup interval in seconds (default: 5 minutes)
        stop_event: Threading event to signal graceful shutdown
        session_manager: Session manager instance for cleanup operations
        
    Returns:
        The cleanup thread
    """
    global _cleanup_thread, _cleanup_thread_lock
    
    with _cleanup_thread_lock:
        # Check if cleanup thread already exists and is alive
        if _cleanup_thread is not None and _cleanup_thread.is_alive():
            return _cleanup_thread
        
        # Create new cleanup thread
        def cleanup_loop():
            manager = session_manager
            logger.info(f"Session cleanup thread started (interval: {interval_seconds}s)")
            
            while not stop_event.is_set():
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
        _cleanup_thread = cleanup_thread
        return cleanup_thread

# Mount Gradio app with FastAPI for Modal
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from gradio.routes import mount_gradio_app

web_app = FastAPI()

# Track process start time for uptime metric
START_TIME = time.time()

# Store cleanup thread reference for shutdown
cleanup_thread_ref = [None]

# Shutdown hook for graceful cleanup
def shutdown_cleanup_thread():
    """Gracefully stop the cleanup thread."""
    if cleanup_thread_ref[0]:
        stop_event.set()  # Signal thread to stop
        cleanup_thread_ref[0].join(timeout=5.0)  # Wait for graceful shutdown
        cleanup_thread_ref[0] = None

# Register shutdown hook
web_app.add_event_handler("shutdown", shutdown_cleanup_thread)
