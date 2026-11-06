#!/usr/bin/env python3
"""
MayaMCP - AI Bartending Agent

Main application entry point for Maya, the philosophical bartender.
Serves the FastAPI application (Phaser 4 SPA at / and REST/SSE API at /api/v1).
"""

import os
import sys
from pathlib import Path

# App code imports through the `src.*` package namespace; console-script
# entry points don't put the repo root on sys.path, so bootstrap it here.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import uvicorn

from src.config.api_keys import configure_provider_env
from src.config.logging_config import setup_logging
from src.config.model_config import get_model_config, is_valid_gemini_model
from src.utils import initialize_state
from src.utils.rate_limiter import get_rate_limiter
from src.utils.state_manager import start_session_cleanup, stop_session_cleanup


def main():
    """Serve the FastAPI application via uvicorn."""
    logger = setup_logging()
    logger.info("Starting MayaMCP - AI Bartending Agent (GCP Vertex AI Mode - Paid Tier)")

    # Configure and validate GCP Vertex AI Mode environment
    provider_cfg = configure_provider_env()
    logger.info(
        "Initialized GCP Vertex AI Mode: project=%s, location=%s, tier=paid",
        provider_cfg["gcp_project"],
        provider_cfg["gcp_location"],
    )

    # Proactive model validation (warning-only)
    model_cfg = get_model_config()
    model_name = model_cfg.get("model_version")
    if model_name and not is_valid_gemini_model(model_name):
        logger.warning(
            f"Configured GEMINI_MODEL_VERSION '{model_name}' not in known list. "
            "Maya will continue to start, but you may want to verify the model "
            "identifier against Google AI docs: https://ai.google.dev/gemini-api/docs/models"
        )

    # Initialize application state and security services
    initialize_state()
    start_session_cleanup()
    get_rate_limiter()  # Initialize singleton
    logger.info("Application state and security services initialized")

    frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
    if not os.path.isdir(frontend_dist):
        logger.warning(
            "frontend/dist not found - API-only mode. "
            "Build the Phaser SPA: cd frontend && npm install && npm run build"
        )

    try:
        uvicorn.run(
            "src.fast_api_app:app",
            host=os.getenv("HOST", "0.0.0.0"),  # nosec B104 - overridable via HOST env var; intentional for containerised deployment
            port=int(os.getenv("PORT", "8000")),
            reload=os.getenv("DEBUG", "False").lower() == "true",
        )
    finally:
        stop_session_cleanup()
        logger.info("Security services stopped")


if __name__ == "__main__":
    main()
