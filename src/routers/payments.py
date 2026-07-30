"""Payment management endpoints."""

from typing import Optional
from fastapi import APIRouter, Header, HTTPException

from ..schemas.payment import PaymentStateResponse, TipRequest
from ..utils.helpers import get_overlay_payment_data
from ..utils.state_manager import get_payment_state, update_payment_state
from .session import _SESSION_STORE

router = APIRouter(prefix="/payments", tags=["Payments"])


def _resolve_session_id(x_session_id: Optional[str]) -> str:
    return x_session_id.strip() if x_session_id and x_session_id.strip() else "default"


@router.get("/tab", response_model=PaymentStateResponse)
def get_payment_tab(x_session_id: Optional[str] = Header(None)) -> PaymentStateResponse:
    session_id = _resolve_session_id(x_session_id)
    payment_state = get_payment_state(session_id, _SESSION_STORE)
    tab_total, balance, tip_percentage, tip_amount = get_overlay_payment_data(payment_state)
    
    return PaymentStateResponse(
        tab_amount=tab_total,
        balance=balance,
        tip_percentage=tip_percentage,
        tip_amount=tip_amount,
        status=payment_state.get("payment_status", "pending")
    )


@router.post("/tip", response_model=PaymentStateResponse)
def add_or_update_tip(
    request: TipRequest,
    x_session_id: Optional[str] = Header(None)
) -> PaymentStateResponse:
    session_id = _resolve_session_id(x_session_id)
    
    if request.tip_percentage is not None and request.tip_percentage not in {10, 15, 20}:
        raise HTTPException(status_code=400, detail="Tip percentage must be 10, 15, or 20")

    kwargs = {}
    if request.tip_percentage is not None:
        kwargs["tip_percentage"] = request.tip_percentage
    if request.tip_amount is not None:
        kwargs["tip_amount"] = request.tip_amount

    update_payment_state(session_id, _SESSION_STORE, kwargs)
    
    updated_state = get_payment_state(session_id, _SESSION_STORE)
    tab_total, balance, tip_percentage, tip_amount = get_overlay_payment_data(updated_state)
    
    return PaymentStateResponse(
        tab_amount=tab_total,
        balance=balance,
        tip_percentage=tip_percentage,
        tip_amount=tip_amount,
        status=updated_state.get("payment_status", "pending")
    )
