"""Logging configuration for MayaMCP."""

import logging
import os
from typing import Optional

def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up logging configuration for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR). 
               Defaults to INFO, or DEBUG if DEBUG env var is True.
        format_string: Custom format string for log messages.
        
    Returns:
        Configured logger instance.
    """
    # Determine log level
    if level is None:
        debug_mode = os.getenv("DEBUG", "False").lower() == "true"
        level = "DEBUG" if debug_mode else "INFO"
    
    # Default format string
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure logging
    # Configure logging
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingFormatter(format_string))
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=[handler],
        force=True  # Override any existing configuration
    )
    
    # Return logger for the main module
    return logging.getLogger("mayamcp")

class RedactingFormatter(logging.Formatter):
    """Formatter that redacts sensitive information from log records."""
    
    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt, datefmt, style)
        import re
        self._patterns = [
            # Google API Keys (AIza...)
            (re.compile(r'(AIza[0-9A-Za-z-_]{35})'), r'REDACTED_API_KEY'),
            # Generic Bearer tokens
            (re.compile(r'Bearer\s+[a-zA-Z0-9\-\._~\+\/]{20,}'), r'Bearer REDACTED_TOKEN'),
            # Stripe Secret Keys (sk_live_..., sk_test_...)
            (re.compile(r'(sk_(live|test)_[0-9a-zA-Z]{24,})'), r'REDACTED_STRIPE_KEY'),
        ]

    def format(self, record):
        original_msg = super().format(record)
        redacted_msg = original_msg
        for pattern, replacement in self._patterns:
            redacted_msg = pattern.sub(replacement, redacted_msg)
        return redacted_msg

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance.
    """
    return logging.getLogger(name)