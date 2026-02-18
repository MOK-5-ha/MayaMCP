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

def get_google_api_key() -> Optional[str]:
    """Get Google API key specifically."""
    return get_api_keys()["google_api_key"]