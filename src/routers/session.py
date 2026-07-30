"""Session management endpoints."""

from typing import Optional
from fastapi import APIRouter, Header, HTTPException

from ..schemas.session import KeySubmissionRequest, SessionStatusResponse
from ..utils.state_manager import has_valid_keys, reset_session_state, set_api_keys

router = APIRouter(prefix="/session", tags=["Session"])

# Global or module app_state store dict fallback
_SESSION_STORE = {}


def _resolve_session_id(x_session_id: Optional[str]) -> str:
    return x_session_id.strip() if x_session_id and x_session_id.strip() else "default"


@router.get("/status", response_model=SessionStatusResponse)
def get_session_status(x_session_id: Optional[str] = Header(None)) -> SessionStatusResponse:
    session_id = _resolve_session_id(x_session_id)
    valid = has_valid_keys(session_id, _SESSION_STORE)
    return SessionStatusResponse(
        session_id=session_id,
        has_valid_keys=valid,
        is_active=True,
    )


@router.post("/keys")
def submit_session_keys(
    request: KeySubmissionRequest,
    x_session_id: Optional[str] = Header(None)
) -> dict:
    session_id = _resolve_session_id(x_session_id)
    if not request.gemini_key or not request.gemini_key.strip():
        raise HTTPException(status_code=400, detail="Gemini API key is required.")
    
    set_api_keys(
        session_id=session_id,
        store=_SESSION_STORE,
        gemini_key=request.gemini_key.strip(),
        cartesia_key=request.cartesia_key.strip() if request.cartesia_key else None
    )
    valid = has_valid_keys(session_id, _SESSION_STORE)
    return {
        "status": "success",
        "session_id": session_id,
        "has_valid_keys": valid
    }


@router.post("/reset")
def reset_session(x_session_id: Optional[str] = Header(None)) -> dict:
    session_id = _resolve_session_id(x_session_id)
    reset_session_state(session_id, _SESSION_STORE)
    return {
        "status": "success",
        "session_id": session_id
    }
