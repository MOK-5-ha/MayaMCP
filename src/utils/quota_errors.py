"""Quota-exceeded popup HTML shared by the chat router."""

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
