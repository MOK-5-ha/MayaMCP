"""Suggestion chip delivery endpoints."""

from collections.abc import MutableMapping

from fastapi import APIRouter, Header, Request, Response

from ..config.logging_config import get_logger
from ..schemas.chips import ChipsResponse, SuggestionChipSet
from ..utils.state_manager import get_chip_state

logger = get_logger(__name__)
router = APIRouter(prefix="/chips", tags=["Chips"])

# Process-local fallback store
_SESSION_STORE = {}


def get_session_store(request: Request) -> MutableMapping:
    if hasattr(request.app.state, "session_store") and request.app.state.session_store is not None:
        return request.app.state.session_store
    return _SESSION_STORE


def _coerce_chips(value) -> list:
    """Normalize stored chip state into a chip list (handles both in-memory
    SuggestionChipSet objects and serialized dicts from remote stores)."""
    if value is None:
        return []
    if isinstance(value, SuggestionChipSet):
        return list(value.chips)
    if isinstance(value, dict):
        return list(SuggestionChipSet(**value).chips)
    return []


@router.get("", response_model=ChipsResponse)
def get_session_chips(
    request: Request,
    response: Response,
    x_session_id: str | None = Header(None),
    session_id: str | None = None,
) -> ChipsResponse:
    """Return the current suggestion chips for a session.

    Chips are generated asynchronously after each chat turn; the SPA polls
    this endpoint after the stream's ``complete`` event. Unknown or empty
    sessions yield an empty chip list (graceful-empty contract) — never wait
    on ``pending_task`` futures, which are in-process only.
    """
    candidate = x_session_id or session_id
    session_id = candidate.strip() if candidate and candidate.strip() else ""
    response.headers["X-Session-ID"] = session_id
    store = get_session_store(request)
    state = get_chip_state(session_id or None, store)
    chips = _coerce_chips(state.get("current_chips"))
    return ChipsResponse(
        session_id=session_id,
        chips=chips,
        generation_seq=int(state.get("generation_seq") or 0),
        failure_count=int(state.get("failure_count") or 0),
    )
