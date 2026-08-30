"""GCP Vertex AI configuration and environment management for MayaMCP."""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_gcp_project() -> str:
    """Retrieve and validate the GCP project ID.

    GCP_PROJECT takes precedence over GOOGLE_CLOUD_PROJECT.

    Returns:
        The configured GCP Project ID.

    Raises:
        ValueError: If neither GCP_PROJECT nor GOOGLE_CLOUD_PROJECT is set.
    """
    project = (os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT") or "").strip()
    if not project:
        raise ValueError(
            "GCP_PROJECT or GOOGLE_CLOUD_PROJECT is not configured. "
            "Google AI Studio Key Mode has been permanently removed; this project "
            "exclusively uses GCP Vertex AI Mode (Paid Tier). Please set GCP_PROJECT in your .env file."
        )
    return project


def get_gcp_location() -> str:
    """Retrieve the GCP location/region for Vertex AI.

    Returns:
        The configured GCP location (defaults to "global").
    """
    return (os.getenv("GCP_LOCATION") or "global").strip() or "global"


def is_vertex_ai_mode() -> bool:
    """Check if GCP Vertex AI mode is enabled via environment variables."""
    return True


def configure_provider_env() -> dict[str, str | None]:
    """Synchronize environment variables strictly for 100% GCP Vertex AI Mode (Paid Tier).

    Purges stale Google AI Studio API key environment variables,
    enforces GOOGLE_GENAI_USE_VERTEXAI="true", sets GEMINI_TIER="paid",
    and validates that GCP_PROJECT is set.

    Returns:
        Dictionary containing resolved provider configuration settings.

    Raises:
        ValueError: If GCP_PROJECT or GOOGLE_CLOUD_PROJECT is not configured.
    """
    # Purge stale Google AI Studio API keys to prevent accidental fallback
    for stale_key in ("GEMINI" + "_API_KEY", "LLM" + "_API_KEY", "BACKUP_LLM" + "_API_KEY"):
        os.environ.pop(stale_key, None)

    # Force Vertex AI mode & paid tier quota
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
    os.environ["GEMINI_TIER"] = "paid"

    # Validate GCP Project ID
    gcp_project = get_gcp_project()
    gcp_location = get_gcp_location()

    cartesia_key = os.getenv("CARTESIA_API_KEY")
    cartesia_clean = cartesia_key.strip() if cartesia_key is not None else None

    return {
        "gcp_project": gcp_project,
        "gcp_location": gcp_location,
        "gemini_tier": "paid",
        "cartesia_api_key": cartesia_clean,
    }


def get_api_keys() -> dict[str, str | None]:
    """Legacy helper maintained for compatibility.

    Returns provider configuration dictionary including GCP project details.
    """
    try:
        cfg = configure_provider_env()
        return {
            "google_api_key": None,
            "gcp_project": cfg["gcp_project"],
            "gcp_location": cfg["gcp_location"],
            "cartesia_api_key": cfg["cartesia_api_key"],
        }
    except ValueError:
        cartesia_key = os.getenv("CARTESIA_API_KEY")
        return {
            "google_api_key": None,
            "gcp_project": None,
            "gcp_location": get_gcp_location(),
            "cartesia_api_key": cartesia_key.strip() if cartesia_key else None,
        }


def get_google_api_key() -> str | None:
    """Get Google API key (None in 100% GCP Vertex AI mode)."""
    return None
