"""Model configuration for MayaMCP."""

import os
from typing import Dict, Any, List
from .logging_config import get_logger


logger = get_logger(__name__)

def _parse_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except (ValueError, TypeError):
        logger.warning(f"Invalid {name} value '{raw}', falling back to {default}")
        return default

def _parse_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except (ValueError, TypeError):
        logger.warning(f"Invalid {name} value '{raw}', falling back to {default}")
        return default


def _get_default_temperature(model_version: str) -> float:
    """Get the recommended default temperature for a given model.

    Google strongly recommends temperature=1.0 for Gemini 3 models as their
    reasoning capabilities are optimized for this setting. Lower values may
    cause unexpected behavior (looping, degraded performance) in complex
    tasks.

    For older models (Gemini 2.x and earlier), 0.7 remains a reasonable
    default.
    """
    if model_version.startswith("gemini-3"):
        return 1.0
    return 0.7


def get_model_config() -> Dict[str, Any]:
    """
    Get model configuration from environment variables.

    Returns:
        Dictionary containing model configuration.
    """
    model_version = os.getenv(
        "GEMINI_MODEL_VERSION", "gemini-3-flash-preview"
    )
    default_temp = _get_default_temperature(model_version)
    return {
        "model_version": model_version,
        "temperature": _parse_float_env("TEMPERATURE", default_temp),
        "max_output_tokens": _parse_int_env("MAX_OUTPUT_TOKENS", 2048),
        "top_p": 0.95,
        "top_k": 1
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
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
    "gemini-3-pro-image-preview",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-exp",
]

def is_valid_gemini_model(model_name: str) -> bool:
    """Check if the provided model name is in the known valid list.

    Note: This is a permissive check used for warnings only; the app
    will continue even if false.
    """
    try:
        return str(model_name).strip() in KNOWN_GEMINI_MODELS
    except (AttributeError, TypeError):
        return False
