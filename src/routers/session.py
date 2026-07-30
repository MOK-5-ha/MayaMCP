"""Session management endpoints."""

import secrets
from typing import MutableMapping, Optional
from fastapi import APIRouter, Header, HTTPException, Request, Response

from ..schemas.session import KeySubmissionRequest, SessionStatusResponse
from ..utils.state_manager import (
    get_session_lock,
    has_valid_keys,
    reset_session_state,
    set_api_keys,
)

router = APIRouter(prefix="/session", tags=["Session"])

# Process-local fallback store
_SESSION_STORE = {}


def get_session_store(request: Request) -> MutableMapping:
    if hasattr(request.app.state, "session_store") and request.app.state.session_store is not None:
        return request.app.state.session_store
    return _SESSION_STORE


def resolve_session_id(x_session_id: Optional[str] = None) -> str:
    if x_session_id and x_session_id.strip():
        return x_session_id.strip()
    return f"sess_{secrets.token_urlsafe(12)}"


@router.get("/status", response_model=SessionStatusResponse)
def get_session_status(
    request: Request,
    response: Response,
    x_session_id: Optional[str] = Header(None)
) -> SessionStatusResponse:
    session_id = resolve_session_id(x_session_id)
    response.headers["X-Session-ID"] = session_id
    store = get_session_store(request)
    lock = get_session_lock(session_id)
    with lock:
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
    response: Response,
    x_session_id: Optional[str] = Header(None)
) -> dict:
    session_id = resolve_session_id(x_session_id)
    response.headers["X-Session-ID"] = session_id
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
    response: Response,
    x_session_id: Optional[str] = Header(None)
) -> dict:
    session_id = resolve_session_id(x_session_id)
    response.headers["X-Session-ID"] = session_id
    store = get_session_store(request)
    reset_session_state(session_id, store)
    return {
        "status": "success",
        "session_id": session_id
    }
