"""API key modal UI components for BYOK authentication."""

from collections.abc import MutableMapping

import gradio as gr

from ..config.logging_config import get_logger
from ..llm.key_validator import validate_gemini_key
from ..utils.helpers import extract_session_id
from ..utils.state_manager import set_api_keys

logger = get_logger(__name__)

# Sentinel value returned by process_order when the LLM hits quota limits
QUOTA_ERROR_SENTINEL = "QUOTA_ERROR"


def create_quota_error_html() -> str:
    """Return styled HTML for the quota-exceeded popup overlay."""
    return """
    <div id="quota-error-popup" style="
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.6); z-index: 9999;
        display: flex; align-items: center; justify-content: center;
    ">
      <div style="
          background: #1a1a2e; border: 1px solid #e94560; border-radius: 12px;
          padding: 32px; max-width: 520px; width: 90%; color: #eee;
          font-family: sans-serif; box-shadow: 0 8px 32px rgba(233,69,96,0.3);
      ">
        <h2 style="margin-top:0; color:#e94560;">Vertex AI Quota Reached</h2>
        <p>Your GCP project has exceeded its Vertex AI usage quota.</p>
        <p><strong>To continue using Maya:</strong></p>
        <ol style="line-height:1.8;">
          <li>Check Vertex AI quotas and billing in Google Cloud Console.</li>
          <li>Confirm Application Default Credentials can access this project.</li>
          <li>Retry after the quota becomes available.</li>
        </ol>
        <button onclick="document.getElementById('quota-error-popup').style.display='none'"
                style="
                    margin-top: 12px; padding: 10px 28px;
                    background: #e94560; color: white; border: none;
                    border-radius: 6px; cursor: pointer; font-size: 1em;
                ">
          Dismiss
        </button>
      </div>
    </div>
    """


def create_help_instructions_md() -> str:
    """Return Markdown text with instructions on configuring GCP Vertex AI Mode."""
    return """
### GCP Vertex AI Mode Setup (Paid Tier)

MayaMCP runs in **100% GCP Vertex AI Mode** using Google Cloud billing credits and Application Default Credentials (ADC).

1. Authenticate with Application Default Credentials:
   ```bash
   gcloud auth application-default login
   ```
2. Enter a **GCP Project ID** that those credentials can access.
3. Ensure Vertex AI is enabled and the project has billing configured.

---

### Getting a Cartesia API Key (for voice)

1. Visit [Cartesia](https://play.cartesia.ai/)
2. Create a free account
3. Navigate to **API Keys** in your dashboard
4. Generate a new key and paste it above

> Cartesia is optional. If you skip it, Maya will respond with text only (no voice).
"""


def handle_key_submission(
    gcp_project: str,
    cartesia_key: str,
    request: gr.Request,
    app_state: MutableMapping | None = None,
) -> tuple[str, gr.Column, gr.Column, bool]:
    """Validate Vertex AI access, store session credentials, and show chat."""
    if app_state is None:
        app_state = {}

    session_id = extract_session_id(request)
    project = gcp_project.strip() if gcp_project else ""
    if not project:
        return (
            "**Error:** GCP Project ID is required.",
            gr.Column(visible=True),
            gr.Column(visible=False),
            False,
        )

    try:
        is_valid, error_msg = validate_gemini_key(gcp_project=project)
    except Exception:
        logger.exception("Exception during Vertex AI configuration validation")
        return (
            "**Error:** Unable to validate Vertex AI configuration. Please check your connection and try again.",
            gr.Column(visible=True),
            gr.Column(visible=False),
            False,
        )
    if not is_valid:
        return (
            f"**Error:** {error_msg}",
            gr.Column(visible=True),
            gr.Column(visible=False),
            False,
        )

    set_api_keys(
        session_id,
        app_state,
        gcp_project=project,
        cartesia_key=cartesia_key.strip() if cartesia_key else None,
    )

    logger.info("Vertex AI configuration validated and stored for session %s", session_id)

    return (
        "",
        gr.Column(visible=False),
        gr.Column(visible=True),
        True,
    )
