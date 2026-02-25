"""Application-level rate limiting for DoS protection and quota management."""

import os
import time
import threading
from collections import defaultdict, deque
from typing import Dict, Optional, Tuple

from ..config.logging_config import get_logger

logger = get_logger(__name__)


class TokenBucket:
    """Token bucket implementation for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens the bucket can hold
            refill_rate: Number of tokens to add per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        # Validate input
        if not isinstance(tokens, int) or tokens <= 0:
            raise ValueError(f"Tokens must be a positive integer, got {tokens}")
        
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def peek(self) -> int:
        """
        Get current token count without consuming.
        
        Returns:
            Current number of tokens in bucket
        """
        with self._lock:
            self._refill()
            return self.tokens
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def stats(self) -> Dict[str, int]:
        """
        Get consistent snapshot of bucket statistics.
        
        Returns:
            Dictionary with tokens, capacity, and refill_rate per minute
        """
        with self._lock:
            self._refill()
            return {
                "tokens": int(self.tokens),
                "capacity": self.capacity,
                "refill_rate": int(self.refill_rate * 60)  # per minute
            }


class RateLimiter:
    """Multi-level rate limiting for session and application-wide protection."""
    
    # Default rate limits (configurable via environment)
    DEFAULT_SESSION_LIMIT = 10  # requests per minute per session
    DEFAULT_APP_LIMIT = 100    # requests per minute globally
    DEFAULT_BURST_LIMIT = 5     # burst requests allowed
    
    def __init__(self):
        """Initialize rate limiter with default limits."""
        # Get limits from environment or use defaults
        self.session_limit = self._get_env_limit(
            "MAYA_SESSION_RATE_LIMIT", 
            self.DEFAULT_SESSION_LIMIT
        )
        self.app_limit = self._get_env_limit(
            "MAYA_APP_RATE_LIMIT", 
            self.DEFAULT_APP_LIMIT
        )
        self.burst_limit = self._get_env_limit(
            "MAYA_BURST_LIMIT", 
            self.DEFAULT_BURST_LIMIT
        )
        
        # Session-specific buckets (session_id -> TokenBucket)
        self._session_buckets: Dict[str, TokenBucket] = {}
        self._session_lock = threading.Lock()
        
        # Global application bucket
        self._app_bucket = TokenBucket(
            capacity=self.app_limit,
            refill_rate=self.app_limit / 60.0  # per second
        )
        
        # Request tracking for burst detection
        self._request_history: Dict[str, deque] = defaultdict(deque)
        self._history_lock = threading.Lock()
        
        logger.info(
            f"Rate limiter initialized: session={self.session_limit}/min, "
            f"app={self.app_limit}/min, burst={self.burst_limit}"
        )
    
    def _get_env_limit(self, env_var: str, default: int) -> int:
        """Get rate limit from environment variable."""
        try:
            value = os.getenv(env_var)
            if value:
                parsed_value = int(value)
                if parsed_value > 0:
                    return parsed_value
                else:
                    logger.warning(
                        f"Invalid rate limit in {env_var}: {value} (must be > 0), "
                        f"using default {default}"
                    )
        except (ValueError, TypeError):
            logger.warning(f"Invalid rate limit in {env_var}, using default {default}")
        return default
    
    def check_session_limit(self, session_id: str, consume: bool = True) -> Tuple[bool, str]:
        """
        Check if session can make a request.
        
        Args:
            session_id: Unique session identifier
            consume: Whether to consume a token (True) or just check (False)
            
        Returns:
            Tuple of (allowed, reason) where reason is empty if allowed
        """
        # Check burst limit (records attempt even if subsequent limits fail, 
        # providing intentional DoS protection against rapid retries)
        if not self._check_burst_limit(session_id):
            return False, "Too many requests in quick succession"
        
        # Get or create session bucket
        with self._session_lock:
            if session_id not in self._session_buckets:
                self._session_buckets[session_id] = TokenBucket(
                    capacity=self.session_limit,
                    refill_rate=self.session_limit / 60.0  # per second
                )
            bucket = self._session_buckets[session_id]
        
        # Check session rate limit
        if consume:
            if not bucket.consume():
                return False, f"Session rate limit exceeded ({self.session_limit}/min)"
        else:
            # Check-only mode: verify we have enough tokens using peek()
            if bucket.peek() < 1:
                return False, f"Session rate limit exceeded ({self.session_limit}/min)"
        
        return True, ""
    
    def check_app_limit(self, consume: bool = True) -> Tuple[bool, str]:
        """
        Check if application can handle a request.
        
        Args:
            consume: Whether to consume a token (True) or just check (False)
            
        Returns:
            Tuple of (allowed, reason) where reason is empty if allowed
        """
        if consume:
            if not self._app_bucket.consume():
                return False, f"Application rate limit exceeded ({self.app_limit}/min)"
        else:
            # Check-only mode: verify we have enough tokens using peek()
            if self._app_bucket.peek() < 1:
                return False, f"Application rate limit exceeded ({self.app_limit}/min)"
        
        return True, ""
    
    def check_limits(self, session_id: str) -> Tuple[bool, str]:
        """
        Check both application and session rate limits with consistent lock ordering.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Tuple of (allowed, reason) where reason is empty if allowed
        """
        # Check burst limit (records attempt even if subsequent limits fail, 
        # providing intentional DoS protection against rapid retries)
        if not self._check_burst_limit(session_id):
            return False, "Too many requests in quick succession"
        
        # Take locks in consistent order: history_lock first, then session_lock
        with self._history_lock:
            with self._session_lock:
                # Check app limit by reading tokens directly without calling consume()
                if self._app_bucket.tokens < 1:
                    return False, f"Application rate limit exceeded ({self.app_limit}/min)"
                
                # Get or create session bucket
                if session_id not in self._session_buckets:
                    self._session_buckets[session_id] = TokenBucket(
                        capacity=self.session_limit,
                        refill_rate=self.session_limit / 60.0  # per second
                    )
                
                bucket = self._session_buckets[session_id]
                
                # Check session limit by reading tokens directly
                if bucket.tokens < 1:
                    return False, f"Session rate limit exceeded ({self.session_limit}/min)"
                
                # All checks passed, consume tokens atomically
                self._app_bucket.tokens -= 1
                bucket.tokens -= 1
                
                return True, ""
    
    def _check_burst_limit(self, session_id: str) -> bool:
        """
        Check burst limit to prevent rapid-fire requests.
        
        Note: This method appends to the history immediately if the check passes.
        This means denied attempts (due to subsequent app or session limits) 
        are still recorded, providing a natural penalty for rapid retries 
        during rate-limit or capacity conditions (DoS protection).

        Args:
            session_id: Unique session identifier
            
        Returns:
            True if within burst limit, False otherwise
        """
        now = time.time()
        window_start = now - 10  # 10-second window
        
        with self._history_lock:
            history = self._request_history[session_id]
            
            # Remove old requests outside window
            while history and history[0] < window_start:
                history.popleft()
            
            # Check if adding this request would exceed burst limit
            if len(history) >= self.burst_limit:
                return False
            
            # Add current request
            history.append(now)
            return True
    
    def cleanup_expired_sessions(self, max_age_seconds: int = 3600) -> None:
        """
        Clean up session data for expired sessions.
        
        Args:
            max_age_seconds: Maximum age of session data before cleanup
        """
        now = time.time()
        cutoff_time = now - max_age_seconds
        
        # Track cleanup counts separately
        session_expired_count = 0
        history_expired_count = 0
        
        with self._session_lock:
            expired_sessions = []
            for session_id, bucket in self._session_buckets.items():
                if bucket.last_refill < cutoff_time:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self._session_buckets[session_id]
            
            session_expired_count = len(expired_sessions)
        
        with self._history_lock:
            expired_sessions = []
            for session_id, history in self._request_history.items():
                if history and history[-1] < cutoff_time:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self._request_history[session_id]
            
            history_expired_count = len(expired_sessions)
        
        # Log combined cleanup results
        total_cleaned = session_expired_count + history_expired_count
        if total_cleaned > 0:
            logger.info(
                f"Cleaned up rate limiter data: "
                f"{session_expired_count} session buckets, "
                f"{history_expired_count} request histories "
                f"(total: {total_cleaned})"
            )
    
    def get_session_stats(self, session_id: str) -> Dict[str, int]:
        """
        Get rate limiting statistics for a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Dictionary with rate limiting statistics
        """
        with self._session_lock:
            bucket = self._session_buckets.get(session_id)
            if not bucket:
                return {"tokens": 0, "capacity": self.session_limit}
            
            return bucket.stats()
    
    def get_app_stats(self) -> Dict[str, int]:
        """
        Get application-wide rate limiting statistics.
        
        Returns:
            Dictionary with application rate limiting statistics
        """
        return self._app_bucket.stats()


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None
_limiter_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    """
    Get the global rate limiter instance.
    
    Returns:
        RateLimiter singleton instance
    """
    global _rate_limiter
    
    if _rate_limiter is None:
        with _limiter_lock:
            if _rate_limiter is None:
                _rate_limiter = RateLimiter()
                logger.info("Global rate limiter initialized")
    
    return _rate_limiter


def check_rate_limits(session_id: str) -> Tuple[bool, str]:
    """
    Convenience function to check rate limits for a session.
    
    Args:
        session_id: Unique session identifier
        
    Returns:
        Tuple of (allowed, reason) where reason is empty if allowed
    """
    limiter = get_rate_limiter()
    return limiter.check_limits(session_id)
