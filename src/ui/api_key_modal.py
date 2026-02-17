"""API key modal UI components for BYOK authentication."""

import gradio as gr
from typing import Optional, Tuple, MutableMapping

from ..config.logging_config import get_logger
from ..llm.key_validator import validate_gemini_key
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
        <h2 style="margin-top:0; color:#e94560;">Rate Limit Reached</h2>
        <p>Your free-tier Gemini API key has exceeded its usage quota.</p>
        <p><strong>To continue using Maya, you can:</strong></p>
        <ol style="line-height:1.8;">
          <li>Wait for your quota to reset (free tier resets daily)</li>
          <li>Enable billing on your Google AI Studio account:
            <br><a href="https://aistudio.google.com/apikey"
                   target="_blank" rel="noopener"
                   style="color:#4fc3f7;">https://aistudio.google.com/apikey</a>
          </li>
          <li>Refresh this page and enter an upgraded API key</li>
        </ol>
        <p style="font-size:0.85em; color:#aaa;">
          Free tier limits: ~15 requests/minute, 1,500 requests/day.
        </p>
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
    """Return Markdown text with instructions on obtaining API keys."""
    return """
### Getting a Free Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Select or create a Google Cloud project when prompted
5. Copy your new API key and paste it above

> The free tier includes ~15 requests/minute and 1,500 requests/day.

---

### Getting a Cartesia API Key (for voice)

1. Visit [Cartesia](https://play.cartesia.ai/)
2. Create a free account
3. Navigate to **API Keys** in your dashboard
4. Generate a new key and paste it above

> Cartesia is optional. If you skip it, Maya will respond with text only (no voice).
"""


def handle_key_submission(
    gemini_key: str,
    cartesia_key: str,
    request: gr.Request,
    app_state: Optional[MutableMapping] = None,
) -> Tuple:
    """Validate keys, store them in session state, and toggle UI visibility.

    Returns:
        Tuple of (error_markdown, api_key_column_update, chat_column_update,
                  keys_validated_state)
    """
    if app_state is None:
        app_state = {}

    session_id = "default"
    if request:
        session_id = request.session_hash

    # --- Validate Gemini key (required) ---
    if not gemini_key or not gemini_key.strip():
        return (
            "**Error:** Please enter your Gemini API key.",
            gr.Column(visible=True),
            gr.Column(visible=False),
            False,
        )

    is_valid, error_msg = validate_gemini_key(gemini_key.strip())
    if not is_valid:
        return (
            f"**Error:** {error_msg}",
            gr.Column(visible=True),
            gr.Column(visible=False),
            False,
        )

    # --- Store keys in session state ---
    set_api_keys(
        session_id,
        app_state,
        gemini_key=gemini_key.strip(),
        cartesia_key=cartesia_key.strip() if cartesia_key else None,
    )

    logger.info(f"BYOK keys validated and stored for session {session_id}")

    # Success: hide form, show chat
    return (
        "",
        gr.Column(visible=False),
        gr.Column(visible=True),
        True,
    )
