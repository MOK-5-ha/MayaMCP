"""Model configuration for MayaMCP."""

import os
from typing import Dict, Any, List


def get_model_config() -> Dict[str, Any]:
    """
    Get model configuration from environment variables.
    
    Returns:
        Dictionary containing model configuration.
    """
    return {
        "model_version": os.getenv("GEMINI_MODEL_VERSION", "gemini-2.5-flash-lite"),
        "temperature": float(os.getenv("TEMPERATURE", "0.7")),
        "max_output_tokens": int(os.getenv("MAX_OUTPUT_TOKENS", "2048")),
        "top_p": 0.95,
        "top_k": 1
    }

def get_generation_config() -> Dict[str, Any]:
    """
    Get generation configuration for LLM calls.
    
    Returns:
        Dictionary containing generation parameters.
    """
    config = get_model_config()
    return {
        "temperature": config["temperature"],
        "top_p": config["top_p"],
        "top_k": config["top_k"],
        "max_output_tokens": config["max_output_tokens"]
    }

def get_cartesia_config() -> Dict[str, Any]:
    """
    Get Cartesia TTS configuration.
    
    Returns:
        Dictionary containing Cartesia configuration.
    """
    return {
        "voice_id": "6f84f4b8-58a2-430c-8c79-688dad597532",
        "model_id": "sonic-2",
        "language": "en",
        "output_format": {
            "container": "wav",
            "sample_rate": 24000,
            "encoding": "pcm_f32le"
        }
    }

# Known valid Gemini model identifiers (non-exhaustive; update as needed)
KNOWN_GEMINI_MODELS: List[str] = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-exp",
]

def get_known_gemini_models() -> List[str]:
    """Return the known list of valid Gemini model identifiers."""
    return KNOWN_GEMINI_MODELS.copy()

def is_valid_gemini_model(model_name: str) -> bool:
    """Check if the provided model name is in the known valid list.

    Note: This is a permissive check used for warnings only; the app will continue even if false.
    """
    try:
        return str(model_name).strip() in KNOWN_GEMINI_MODELS
    except (AttributeError, TypeError):
        return False
