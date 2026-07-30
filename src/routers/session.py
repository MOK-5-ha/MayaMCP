"""Session management endpoints."""

from typing import MutableMapping, Optional
from fastapi import APIRouter, Header, HTTPException, Request

from ..schemas.session import KeySubmissionRequest, SessionStatusResponse
from ..utils.state_manager import has_valid_keys, reset_session_state, set_api_keys

router = APIRouter(prefix="/session", tags=["Session"])

# Process-local fallback store
_SESSION_STORE = {}


def get_session_store(request: Request) -> MutableMapping:
    if hasattr(request.app.state, "session_store") and request.app.state.session_store is not None:
        return request.app.state.session_store
    return _SESSION_STORE


def _resolve_session_id(x_session_id: Optional[str]) -> str:
    return x_session_id.strip() if x_session_id and x_session_id.strip() else "default"


@router.get("/status", response_model=SessionStatusResponse)
def get_session_status(
    request: Request,
    x_session_id: Optional[str] = Header(None)
) -> SessionStatusResponse:
    session_id = _resolve_session_id(x_session_id)
    store = get_session_store(request)
    valid = has_valid_keys(session_id, store)
    return SessionStatusResponse(
        session_id=session_id,
        has_valid_keys=valid,
        is_active=True,
    )


@router.post("/keys")
def submit_session_keys(
    request_data: KeySubmissionRequest,
    request: Request,
    x_session_id: Optional[str] = Header(None)
) -> dict:
    session_id = _resolve_session_id(x_session_id)
    if not request_data.gemini_key or not request_data.gemini_key.strip():
        raise HTTPException(status_code=400, detail="Gemini API key is required.")
    
    store = get_session_store(request)
    set_api_keys(
        session_id=session_id,
        store=store,
        gemini_key=request_data.gemini_key.strip(),
        cartesia_key=request_data.cartesia_key.strip() if request_data.cartesia_key else None
    )
    valid = has_valid_keys(session_id, store)
    return {
        "status": "success",
        "session_id": session_id,
        "has_valid_keys": valid
    }


@router.post("/reset")
def reset_session(
    request: Request,
    x_session_id: Optional[str] = Header(None)
) -> dict:
    session_id = _resolve_session_id(x_session_id)
    store = get_session_store(request)
    reset_session_state(session_id, store)
    return {
        "status": "success",
        "session_id": session_id
    }
