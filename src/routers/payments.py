"""Payment management endpoints."""


from fastapi import APIRouter, Header, HTTPException, Request, Response

from ..schemas.payment import PaymentStateResponse, TipRequest
from ..utils.helpers import get_overlay_payment_data
from ..utils.state_manager import get_payment_state, update_payment_state
from .session import get_session_store, resolve_session_id

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("/tab", response_model=PaymentStateResponse)
def get_payment_tab(
    request: Request,
    response: Response,
    x_session_id: str | None = Header(None)
) -> PaymentStateResponse:
    session_id = resolve_session_id(x_session_id)
    response.headers["X-Session-ID"] = session_id
    store = get_session_store(request)
    payment_state = get_payment_state(session_id, store)
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
    tip_req: TipRequest,
    request: Request,
    response: Response,
    x_session_id: str | None = Header(None)
) -> PaymentStateResponse:
    session_id = resolve_session_id(x_session_id)
    response.headers["X-Session-ID"] = session_id
    store = get_session_store(request)

    if tip_req.tip_percentage is not None and tip_req.tip_amount is not None:
        raise HTTPException(
            status_code=400,
            detail="Provide either tip_percentage or tip_amount, not both."
        )

    if tip_req.tip_percentage is not None and tip_req.tip_percentage not in {10, 15, 20}:
        raise HTTPException(status_code=400, detail="Tip percentage must be 10, 15, or 20")

    kwargs = {}
    if tip_req.tip_percentage is not None:
        kwargs["tip_percentage"] = tip_req.tip_percentage
    if tip_req.tip_amount is not None:
        kwargs["tip_amount"] = tip_req.tip_amount

    update_payment_state(session_id, store, kwargs)

    updated_state = get_payment_state(session_id, store)
    tab_total, balance, tip_percentage, tip_amount = get_overlay_payment_data(updated_state)

    return PaymentStateResponse(
        tab_amount=tab_total,
        balance=balance,
        tip_percentage=tip_percentage,
        tip_amount=tip_amount,
        status=updated_state.get("payment_status", "pending")
    )
