import asyncio
import base64
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from ..conversation.processor import process_order, process_order_stream
from ..llm.session_registry import (
    SessionLimitExceededError,
    get_session_llm,
    get_session_tts,
)
from ..schemas.chat import ChatRequest, ChatResponse
from ..ui.api_key_modal import create_quota_error_html
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
    x_session_id: str | None = Header(None)
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
                if isinstance(audio_data, bytes) and audio_data:
                    audio_b64 = base64.b64encode(audio_data).decode("utf-8")
                elif isinstance(audio_data, str) and audio_data:
                    audio_b64 = audio_data
            except Exception:
                audio_b64 = None

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
        raise HTTPException(status_code=429, detail=f"Bar capacity reached: {e}") from e
    except Exception as e:
        if is_quota_error(e):
            return ChatResponse(
                response_text="It looks like your API key has hit its rate limit.",
                history=current_history,
                current_order=get_current_order_state(session_id, store),
                quota_error_html=create_quota_error_html()
            )
        raise HTTPException(status_code=500, detail=str(e)) from e


def derive_viseme(text_chunk: str) -> str:
    """Derive mouth flap viseme frame key from text chunk."""
    if not text_chunk or not text_chunk.strip():
        return "mouth_closed"

    last_char = text_chunk.strip()[-1].lower()
    if last_char in ('a', 'h'):
        return "mouth_talk_a"
    elif last_char in ('e', 'i', 'y'):
        return "mouth_talk_e"
    elif last_char in ('o', 'u', 'w'):
        return "mouth_talk_o"
    elif last_char in ('m', 'b', 'p'):
        return "mouth_closed"
    else:
        return "mouth_talk_a"


@router.api_route("/chat/stream", methods=["GET", "POST"])
async def chat_stream_endpoint(
    http_req: Request,
    message: str | None = Query(None),
    user_input: str | None = Query(None),
    session_id: str | None = Query(None),
    x_session_id: str | None = Header(None)
):
    effective_session_id = resolve_session_id(x_session_id, session_id)
    store = get_session_store(http_req)

    # Extract user input text from query, body, or ChatRequest
    input_message = message or user_input
    if http_req.method == "POST":
        try:
            body_json = await http_req.json()
            if isinstance(body_json, dict):
                input_message = body_json.get("message") or body_json.get("user_input") or input_message
        except Exception:
            input_message = input_message

    if not input_message or not input_message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message parameter or body payload is required for streaming."
        )

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
            # Emit session initialization event for EventSource / Phaser 3 clients
            init_event = {"type": "session", "session_id": effective_session_id}
            yield f"data: {json.dumps(init_event)}\n\n"

            llm = get_session_llm(effective_session_id, gemini_key)

            stream = process_order_stream(
                user_input_text=input_message,
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

                if isinstance(event, dict):
                    # Attach session_id and viseme tag for Phaser 3 animation rendering
                    event["session_id"] = effective_session_id
                    content_text = event.get("content") or event.get("text_chunk") or ""
                    if content_text:
                        event["viseme"] = derive_viseme(content_text)

                    if event.get("type") == "complete":
                        final_text = event.get("content") or event.get("full_response") or ""
                        if final_text:
                            updated_hist = append_to_history(current_history, input_message, final_text)
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

