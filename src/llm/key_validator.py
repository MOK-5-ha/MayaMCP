"""Validation for GCP Vertex AI Mode configuration."""

import os
from typing import Optional, Tuple

from ..config.logging_config import get_logger

logger = get_logger(__name__)

try:
    from google import genai
except ImportError:
    genai = None

_VALIDATION_TIMEOUT_S = 10


def validate_gemini_key(
    api_key: Optional[str] = None,
    gcp_project: Optional[str] = None,
    gcp_location: Optional[str] = None,
) -> Tuple[bool, str]:
    """Validate GCP Vertex AI configuration with Application Default Credentials.

    Google AI Studio Key Mode has been permanently removed; this function validates
    the GCP Project ID and Vertex AI connectivity.

    Args:
        api_key: Optional deprecated parameter.
        gcp_project: Optional explicit GCP Project ID.
        gcp_location: Optional GCP Location.

    Returns:
        ``(True, "")`` on success, or ``(False, error_message)`` on failure.
    """
    project = (
        gcp_project or os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT") or ""
    ).strip()
    if not project:
        return (
            False,
            "GCP_PROJECT or GOOGLE_CLOUD_PROJECT is not configured. "
            "Google AI Studio Key Mode has been permanently removed; this project "
            "exclusively uses GCP Vertex AI Mode (Paid Tier). Please set GCP_PROJECT in your .env file.",
        )

    location = (
        gcp_location or os.getenv("GCP_LOCATION") or "global"
    ).strip() or "global"

    if genai is None:
        logger.error("google-genai SDK not installed; cannot validate GCP Vertex AI mode")
        return False, "Server configuration error. Please try again later."

    try:
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
        os.environ["GEMINI_TIER"] = "paid"
        client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
            http_options={"timeout": _VALIDATION_TIMEOUT_S},
        )
        next(iter(client.models.list(config={"page_size": 1})), None)
        logger.info("GCP Vertex AI Mode validated successfully for project %s", project)
        return True, ""
    except Exception as e:
        msg = str(e).lower()
        code = getattr(e, "status_code", None)
        error_code = getattr(e, "error_code", None)

        if code == 429 or error_code == 429 or "429" in msg or "quota" in msg:
            logger.warning(f"GCP Vertex AI key validation hit rate limit: {e}")
            return (
                False,
                "GCP Vertex AI quota limit encountered. Please verify quota limits in GCP Console.",
            )

        if (
            code in (401, 403)
            or error_code in (401, 403)
            or "permission" in msg
            or "unauthenticated" in msg
            or "credentials" in msg
        ):
            logger.warning(f"GCP Vertex AI validation auth failure: {e}")
            return (
                False,
                "Application Default Credentials (ADC) or GCP permissions invalid for project "
                f"'{project}'. Run 'gcloud auth application-default login' or verify project access.",
            )

        if "timeout" in msg or "connect" in msg or "network" in msg:
            logger.warning(f"GCP Vertex AI validation network error: {e}")
            return False, "Connection error. Please check your internet and try again."

        logger.error(f"GCP Vertex AI validation unexpected error: {e}")
        return False, f"Vertex AI validation failed for project '{project}': {e}"
