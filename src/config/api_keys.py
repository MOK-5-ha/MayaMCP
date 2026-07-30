"""API key management for MayaMCP."""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_gcp_project() -> str | None:
    """Retrieve GCP Project ID for Vertex AI mode."""
    project = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
    return project.strip() if project and project.strip() else None


def get_gcp_location() -> str:
    """Retrieve GCP Location for Vertex AI mode (defaults to 'global')."""
    location = os.getenv("GCP_LOCATION", "global")
    return location.strip() if location and location.strip() else "global"


def is_vertex_ai_mode() -> bool:
    """Check if GCP Vertex AI mode is enabled via environment variables."""
    return get_gcp_project() is not None


def get_api_keys() -> dict[str, str | None]:
    """
    Retrieve API keys and GCP project configuration from environment variables.

    Returns:
        Dictionary containing API keys or GCP project settings.
    """
    google_key = os.getenv("GEMINI_API_KEY")
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    gcp_project = get_gcp_project()
    gcp_location = get_gcp_location()
    return {
        "google_api_key": google_key.strip() if google_key is not None else None,
        "cartesia_api_key": cartesia_key.strip() if cartesia_key is not None else None,
        "gcp_project": gcp_project,
        "gcp_location": gcp_location,
        "is_vertex_ai": gcp_project is not None,
    }


def get_google_api_key() -> str | None:
    """Get Google API key specifically."""
    return get_api_keys()["google_api_key"]


