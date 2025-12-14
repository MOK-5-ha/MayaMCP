"""Stripe MCP client for payment operations.

This module provides integration with the Stripe MCP server for payment
link generation and status checking. It includes retry logic, availability
checking with caching, and fallback to mock payments when Stripe is unavailable.

Requirements:
- 3.1: Create Stripe payment link using test mode
- 3.2: Return payment link to user
- 3.3: Mark bill as paid and reset tab on success
- 3.4: Fall back to mock payment if Stripe unavailable
- 4.1: Use Stripe test API keys exclusively
- 4.2: Use Stripe's test mode sandbox environment
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Any, Tuple

from ..config.logging_config import get_logger

logger = get_logger(__name__)


# =============================================================================
# Configuration Constants
# =============================================================================

# Retry configuration for create_payment_link
MAX_RETRIES = 3  # Total up to 4 requests (initial + 3 retries)
DEFAULT_TIMEOUT = 15.0  # Overall timeout in seconds
RETRY_DELAYS = [1.0, 2.0, 4.0]  # Exponential backoff: 1s, 2s, 4s

# Availability check configuration
AVAILABILITY_CACHE_TTL = 30.0  # Cache availability result for 30 seconds
AVAILABILITY_TIMEOUT = 5.0  # Probe must respond within 5 seconds

# Payment status polling configuration
POLL_INTERVAL = 2.0  # 2 seconds between attempts
POLL_TIMEOUT = 5.0  # Per-poll timeout (each poll must complete within 5s)
POLL_DEADLINE = 30.0  # Total wall-clock deadline for polling
MAX_POLL_ATTEMPTS = 15  # Maximum polling attempts


class StripeMCPError(Exception):
    """Base exception for Stripe MCP operations."""
    pass


class StripeUnavailableError(StripeMCPError):
    """Raised when Stripe MCP server is unavailable."""
    pass


class PaymentLinkCreationError(StripeMCPError):
    """Raised when payment link creation fails after retries."""
    pass


class PaymentStatusTimeoutError(StripeMCPError):
    """Raised when payment status polling exceeds deadline."""
    pass


class StripeMCPClient:
    """
    Client for Stripe MCP server operations.
    
    This client provides methods for:
    - Creating payment links with retry logic
    - Checking payment status with timeout
    - Availability checking with caching
    
    All operations use Stripe's test mode by default.
    
    Attributes:
        test_mode: Whether to use Stripe test mode (default: True)
        max_retries: Maximum retry attempts for payment link creation
        timeout: Overall timeout for operations
    """
    
    def __init__(
        self,
        test_mode: bool = True,
        max_retries: int = MAX_RETRIES,
        timeout: float = DEFAULT_TIMEOUT
    ):
        """
        Initialize Stripe MCP client.
        
        Args:
            test_mode: Use Stripe test mode (default: True, required for sandbox)
            max_retries: Maximum retry attempts (default: 3)
            timeout: Overall timeout in seconds (default: 15.0)
        """
        self.test_mode = test_mode
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Availability cache
        self._availability_cache: Optional[Tuple[bool, float]] = None
        
        logger.info(
            f"StripeMCPClient initialized: test_mode={test_mode}, "
            f"max_retries={max_retries}, timeout={timeout}"
        )
    
    def generate_idempotency_key(self, session_id: str) -> str:
        """
        Generate idempotency key for Stripe requests.
        
        Format: {session_id}_{unix_timestamp}
        
        This ensures that retried requests don't create duplicate payment links.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Idempotency key string in format {session_id}_{unix_timestamp}
        
        Requirements: 3.1
        """
        unix_timestamp = int(time.time())
        idempotency_key = f"{session_id}_{unix_timestamp}"
        logger.debug(f"Generated idempotency key: {idempotency_key}")
        return idempotency_key
    
    def is_available(self) -> bool:
        """
        Check if Stripe MCP server is available.
        
        Uses a lightweight probe to check server availability. Results are
        cached for AVAILABILITY_CACHE_TTL seconds to reduce probe overhead.
        
        Availability check implementation:
        - Attempt to list Stripe MCP server tools via kiroPowers activate
        - Success criteria: server responds within 5 seconds with valid tool list
        - Unavailability indicators: connection refused, timeout, 5xx errors, empty tool list
        
        Returns:
            True if Stripe MCP server is available, False otherwise
            
        Requirements: 3.4
        """
        current_time = time.time()
        
        # Check cache
        if self._availability_cache is not None:
            cached_result, cache_time = self._availability_cache
            if current_time - cache_time < AVAILABILITY_CACHE_TTL:
                logger.debug(f"Using cached availability result: {cached_result}")
                return cached_result
        
        # Perform availability check
        try:
            is_available = self._probe_stripe_server()
            self._availability_cache = (is_available, current_time)
            logger.info(f"Stripe MCP availability check: {is_available}")
            return is_available
        except Exception as e:
            logger.warning(f"Stripe MCP availability check failed: {e}")
            self._availability_cache = (False, current_time)
            return False
    
    def _probe_stripe_server(self) -> bool:
        """
        Perform lightweight probe of Stripe MCP server.
        
        This is a synchronous probe that attempts to activate the Stripe
        power and verify it returns a valid tool list.
        
        Returns:
            True if server responds with valid tools, False otherwise
        """
        # TODO: Implement actual MCP server probe via kiroPowers
        # For now, return True to allow development to proceed
        # This will be replaced with actual MCP integration
        logger.debug("Stripe MCP probe: returning True (stub implementation)")
        return True
    
    async def create_payment_link(
        self,
        amount: float,
        description: str,
        idempotency_key: str,
        max_retries: Optional[int] = None
    ) -> Dict[str, str]:
        """
        Create Stripe payment link with async retry logic.
        
        Uses non-blocking async retries with asyncio.sleep() to avoid blocking
        request threads. Implements exponential backoff: 1s, 2s, 4s.
        
        Args:
            amount: Payment amount in dollars
            description: Payment description (e.g., "Bar tab at MOK 5-ha")
            idempotency_key: Key for request deduplication
            max_retries: Override default max retries (optional)
            
        Returns:
            Dict with keys:
            - url: Stripe payment link URL
            - payment_id: Stripe payment link ID (plink_xxx)
            - is_simulated: Whether this is a mock payment (fallback)
            
        Raises:
            PaymentLinkCreationError: If all retries exhausted and fallback fails
            
        Requirements: 3.1, 3.2, 4.2
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        # Check availability first to avoid unnecessary retries
        if not self.is_available():
            logger.warning(
                f"Stripe MCP unavailable, falling back to mock payment. "
                f"session_key={idempotency_key}"
            )
            return self._create_mock_payment(amount, description)
        
        start_time = time.time()
        last_error: Optional[Exception] = None
        
        for attempt in range(max_retries + 1):  # Initial + retries
            # Check overall timeout
            elapsed = time.time() - start_time
            if elapsed >= self.timeout:
                logger.warning(
                    f"Payment link creation timed out after {elapsed:.1f}s. "
                    f"attempts={attempt}, idempotency_key={idempotency_key}"
                )
                break
            
            try:
                result = await self._call_stripe_create_link(
                    amount, description, idempotency_key
                )
                logger.info(
                    f"Payment link created successfully: "
                    f"payment_id={result.get('payment_id')}, attempt={attempt + 1}"
                )
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Payment link creation attempt {attempt + 1} failed: {e}"
                )
                
                # Wait before retry (if not last attempt)
                if attempt < max_retries:
                    delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                    remaining_time = self.timeout - (time.time() - start_time)
                    
                    if remaining_time > delay:
                        logger.debug(f"Waiting {delay}s before retry {attempt + 2}")
                        await asyncio.sleep(delay)
                    else:
                        logger.debug("Not enough time for retry, breaking")
                        break
        
        # All retries exhausted - fall back to mock payment
        logger.warning(
            f"Payment link creation failed after {max_retries + 1} attempts. "
            f"idempotency_key={idempotency_key}, last_error={last_error}. "
            f"Falling back to mock payment."
        )
        
        return self._create_mock_payment(amount, description)
    
    async def _call_stripe_create_link(
        self,
        amount: float,
        description: str,
        idempotency_key: str
    ) -> Dict[str, str]:
        """
        Call Stripe MCP server to create payment link.
        
        This method will be implemented to use kiroPowers tool to communicate
        with the Stripe MCP server.
        
        Args:
            amount: Payment amount in dollars
            description: Payment description
            idempotency_key: Idempotency key for deduplication
            
        Returns:
            Dict with url, payment_id, is_simulated=False
            
        Raises:
            Exception: If Stripe API call fails
        """
        # TODO: Implement actual MCP server call via kiroPowers
        # For now, simulate a successful response for development
        # This will be replaced with actual MCP integration
        
        # Convert amount to cents for Stripe
        amount_cents = int(round(amount * 100))
        
        # Simulate Stripe payment link response
        mock_payment_id = f"plink_test_{idempotency_key[-8:]}"
        mock_url = f"https://checkout.stripe.com/c/pay/{mock_payment_id}"
        
        logger.debug(
            f"Stripe MCP call (stub): amount={amount_cents}, "
            f"description={description}, idempotency_key={idempotency_key}"
        )
        
        return {
            "url": mock_url,
            "payment_id": mock_payment_id,
            "is_simulated": False
        }
    
    def _create_mock_payment(
        self,
        amount: float,
        description: str
    ) -> Dict[str, str]:
        """
        Create mock payment link as fallback.
        
        Used when Stripe MCP server is unavailable or all retries exhausted.
        
        Args:
            amount: Payment amount in dollars
            description: Payment description
            
        Returns:
            Dict with mock url, payment_id, is_simulated=True
        """
        mock_id = f"mock_{int(time.time())}"
        
        logger.info(
            f"Created mock payment: id={mock_id}, amount=${amount:.2f}"
        )
        
        return {
            "url": f"https://example.com/mock-payment/{mock_id}",
            "payment_id": mock_id,
            "is_simulated": True
        }
    
    async def check_payment_status(
        self,
        payment_id: str,
        poll_interval: float = POLL_INTERVAL,
        poll_timeout: float = POLL_TIMEOUT,
        deadline: float = POLL_DEADLINE
    ) -> str:
        """
        Check status of Stripe payment with timeout.
        
        Polls the payment status at regular intervals until the payment
        completes, fails, or the deadline is exceeded.
        
        Polling configuration:
        - Poll interval: 2 seconds between attempts
        - Per-poll timeout: 5 seconds (each poll must complete within 5s)
        - Total deadline: 30 seconds for entire polling operation
        - Maximum attempts: 15 (2s interval × 15 = 30s total)
        
        Args:
            payment_id: Stripe payment ID to check
            poll_interval: Seconds between poll attempts (default: 2.0)
            poll_timeout: Timeout for each poll (default: 5.0)
            deadline: Total wall-clock deadline (default: 30.0)
            
        Returns:
            Payment status: "pending", "succeeded", "failed", or "timeout"
            
        Requirements: 3.3
        """
        start_time = time.time()
        attempt = 0
        
        while True:
            elapsed = time.time() - start_time
            
            # Check wall-clock deadline
            if elapsed >= deadline:
                logger.warning(
                    f"Payment status check timed out: "
                    f"payment_id={payment_id}, elapsed={elapsed:.1f}s"
                )
                return "timeout"
            
            # Check max attempts
            if attempt >= MAX_POLL_ATTEMPTS:
                logger.warning(
                    f"Payment status check exceeded max attempts: "
                    f"payment_id={payment_id}, attempts={attempt}"
                )
                return "timeout"
            
            try:
                status = await asyncio.wait_for(
                    self._poll_payment_status(payment_id),
                    timeout=poll_timeout
                )
                
                logger.debug(
                    f"Payment status poll: payment_id={payment_id}, "
                    f"status={status}, attempt={attempt + 1}"
                )
                
                # Return if terminal status
                if status in ("succeeded", "failed"):
                    logger.info(
                        f"Payment status resolved: payment_id={payment_id}, "
                        f"status={status}, attempts={attempt + 1}"
                    )
                    return status
                
            except asyncio.TimeoutError:
                logger.warning(
                    f"Payment status poll timed out: "
                    f"payment_id={payment_id}, attempt={attempt + 1}"
                )
            except Exception as e:
                logger.warning(
                    f"Payment status poll failed: "
                    f"payment_id={payment_id}, attempt={attempt + 1}, error={e}"
                )
            
            attempt += 1
            
            # Wait before next poll (if time permits)
            remaining = deadline - (time.time() - start_time)
            if remaining > poll_interval:
                await asyncio.sleep(poll_interval)
            elif remaining > 0:
                await asyncio.sleep(remaining)
            else:
                break
        
        return "timeout"
    
    async def _poll_payment_status(self, payment_id: str) -> str:
        """
        Poll Stripe MCP server for payment status.
        
        This method will be implemented to use kiroPowers tool to communicate
        with the Stripe MCP server.
        
        Args:
            payment_id: Stripe payment ID to check
            
        Returns:
            Payment status: "pending", "succeeded", or "failed"
        """
        # TODO: Implement actual MCP server call via kiroPowers
        # For now, simulate a pending response for development
        # This will be replaced with actual MCP integration
        
        logger.debug(f"Stripe MCP status poll (stub): payment_id={payment_id}")
        
        # Simulate: return pending for now
        # In real implementation, this would query Stripe
        return "pending"
    
    def invalidate_availability_cache(self) -> None:
        """
        Invalidate the availability cache.
        
        Call this when you want to force a fresh availability check,
        for example after a connection error.
        """
        self._availability_cache = None
        logger.debug("Availability cache invalidated")
