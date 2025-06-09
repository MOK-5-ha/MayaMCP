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
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        force=True  # Override any existing configuration
    )
    
    # Return logger for the main module
    return logging.getLogger("mayamcp")

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance.
    """
    return logging.getLogger(name)