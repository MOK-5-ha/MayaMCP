import asyncio
import base64
import json
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from ..conversation.processor import process_order, process_order_stream
from ..llm.session_registry import (
    SessionLimitExceededError,
    get_session_llm,
    get_session_tts,
)
from ..schemas.chat import ChatRequest, ChatResponse
from ..utils.errors import is_quota_error
from ..utils.helpers import append_to_history, get_overlay_payment_data
from ..utils.state_manager import (
    get_api_key_state,
    get_current_order_state,
    get_payment_state,
    get_session_chat_history,
    has_valid_keys,
    set_session_chat_history,
)
from ..voice.tts import get_voice_audio
from ..ui.api_key_modal import create_quota_error_html

from .session import get_session_store, resolve_session_id

router = APIRouter(tags=["Chat"])


def _fetch_next_stream_event(stream_iterator):
    try:
        return False, next(stream_iterator)
    except StopIteration:
        return True, None


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    chat_req: ChatRequest,
    http_req: Request,
    http_resp: Response,
    x_session_id: Optional[str] = Header(None)
) -> ChatResponse:
    session_id = resolve_session_id(x_session_id)
    http_resp.headers["X-Session-ID"] = session_id
    store = get_session_store(http_req)
    
    if not has_valid_keys(session_id, store):
        raise HTTPException(
            status_code=400,
            detail="Please provide your API keys first before sending messages."
        )

    api_key_state = get_api_key_state(session_id, store)
    gemini_key = api_key_state["gemini_key"]
    cartesia_key = api_key_state.get("cartesia_key")

    current_history = get_session_chat_history(session_id, store)

    try:
        llm = get_session_llm(session_id, gemini_key)
        cartesia_client = get_session_tts(session_id, cartesia_key)

        response_text, updated_history, _, updated_order, _ = process_order(
            user_input_text=chat_req.user_input,
            current_session_history=current_history,
            llm=llm,
            rag_retriever=None,
            api_key=gemini_key,
            session_id=session_id,
            app_state=store,
        )

        set_session_chat_history(session_id, updated_history, store)

        audio_b64 = None
        if cartesia_client and response_text and response_text.strip():
            try:
                audio_data = get_voice_audio(response_text, cartesia_client)
                if audio_data and isinstance(audio_data, tuple) and len(audio_data) >= 2:
                    pass
            except Exception:
                pass

        payment_state = get_payment_state(session_id, store)
        tab_total, balance, tip_percentage, tip_amount = get_overlay_payment_data(payment_state)

        return ChatResponse(
            response_text=response_text,
            history=updated_history,
            current_order=updated_order,
            audio_base64=audio_b64,
            payment_summary={
                "tab_amount": tab_total,
                "balance": balance,
                "tip_percentage": tip_percentage,
                "tip_amount": tip_amount,
            }
        )

    except SessionLimitExceededError as e:
        raise HTTPException(status_code=429, detail=f"Bar capacity reached: {e}")
    except Exception as e:
        if is_quota_error(e):
            return ChatResponse(
                response_text="It looks like your API key has hit its rate limit.",
                history=current_history,
                current_order=get_current_order_state(session_id, store),
                quota_error_html=create_quota_error_html()
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/stream")
async def chat_stream_endpoint(
    message: str,
    http_req: Request,
    session_id: Optional[str] = Query(None),
    x_session_id: Optional[str] = Header(None)
):
    effective_session_id = resolve_session_id(x_session_id, session_id)
    store = get_session_store(http_req)
    
    if not has_valid_keys(effective_session_id, store):
        raise HTTPException(
            status_code=400,
            detail="Please provide your API keys first before streaming."
        )

    api_key_state = get_api_key_state(effective_session_id, store)
    gemini_key = api_key_state["gemini_key"]

    current_history = get_session_chat_history(effective_session_id, store)
    
    async def sse_generator() -> AsyncGenerator[str, None]:
        try:
            # Emit session initialization event for EventSource clients
            init_event = {"type": "session", "session_id": effective_session_id}
            yield f"data: {json.dumps(init_event)}\n\n"

            llm = get_session_llm(effective_session_id, gemini_key)

            stream = process_order_stream(
                user_input_text=message,
                current_session_history=current_history,
                llm=llm,
                rag_retriever=None,
                api_key=gemini_key,
                session_id=effective_session_id,
                app_state=store,
            )
            while True:
                is_done, event = await asyncio.to_thread(_fetch_next_stream_event, stream)
                if is_done:
                    break
                if event.get("type") == "complete":
                    final_text = event.get("content") or event.get("full_response") or ""
                    if final_text:
                        updated_hist = append_to_history(current_history, message, final_text)
                        set_session_chat_history(effective_session_id, updated_hist, store)
                yield f"data: {json.dumps(event)}\n\n"
        except SessionLimitExceededError as limit_err:
            error_event = {"type": "error", "content": f"Bar capacity reached: {limit_err}"}
            yield f"data: {json.dumps(error_event)}\n\n"
        except Exception as err:
            error_event = {"type": "error", "content": str(err)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={"X-Session-ID": effective_session_id}
    )
