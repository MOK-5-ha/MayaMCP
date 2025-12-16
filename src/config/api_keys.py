"""API key management for MayaMCP."""

import os
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_api_keys() -> Dict[str, Optional[str]]:
    """
    Retrieve API keys from environment variables.
    
    Returns:
        Dictionary containing API keys or None if not found.
    """
    google_key = os.getenv("GEMINI_API_KEY")
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    return {
        "google_api_key": google_key.strip() if google_key is not None else None,
        "cartesia_api_key": cartesia_key.strip() if cartesia_key is not None else None
    }

def validate_api_keys(required_keys: Optional[list] = None) -> bool:
    """
    Validate that required API keys are present.
    
    Args:
        required_keys: List of required key names. Defaults to all keys.
        
    Returns:
        True if all required keys are present and non-empty.
    """
    if required_keys is None:
        required_keys = ["google_api_key", "cartesia_api_key"]
    
    api_keys = get_api_keys()
    
    for key in required_keys:
        if not api_keys.get(key):
            return False
    
    return True

def get_google_api_key() -> Optional[str]:
    """Get Google API key specifically."""
    return get_api_keys()["google_api_key"]

def get_cartesia_api_key() -> Optional[str]:
    """Get Cartesia API key specifically."""
    return get_api_keys()["cartesia_api_key"]