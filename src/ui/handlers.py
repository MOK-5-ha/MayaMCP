"""Gradio event handlers."""

from typing import Any, Dict, List, MutableMapping, Optional, Tuple

import gradio as gr

from ..config.logging_config import get_logger
from ..conversation.processor import process_order, process_order_stream
from ..llm.session_registry import (
    SessionLimitExceededError,
    get_session_llm,
    get_session_tts,
)
from ..utils.batch_state import batch_state_commits
from ..utils.errors import is_quota_error
from ..utils.helpers import append_to_history, get_overlay_payment_data
from ..utils.state_manager import (
    get_api_key_state,
    get_current_order_state,
    get_payment_state,
    has_valid_keys,
    reset_session_state,
)
from ..voice.tts import get_voice_audio
from .api_key_modal import QUOTA_ERROR_SENTINEL, create_quota_error_html
from .tab_overlay import (
    create_tab_overlay_html,
)

logger = get_logger(__name__)



def handle_gradio_input(
    user_input: str,
    session_history_state: List[Dict[str, str]],
    current_tab: float,
    current_balance: float,
    current_tip_percentage: Optional[int],
    current_tip_amount: float,
    request: gr.Request,
    tools=None,
    rag_retriever=None,
    rag_api_key: Optional[str] = None,
    app_state: Optional[MutableMapping] = None,
    avatar_path: str = "assets/bartender_avatar.jpg"
) -> Tuple[str, List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, Any]], Any,
           str, float, float, float, float, Optional[int], float, str, str]:
    """
    Gradio callback: Takes input/state, calls logic & TTS, returns updates.

    Uses per-session LLM and TTS clients from the BYOK session registry.

    Returns:
        Tuple of (empty_input, updated_history, updated_history_for_gradio,
                  updated_order, audio_data, overlay_html, new_tab, new_balance,
                  prev_tab, prev_balance, new_tip_percentage, new_tip_amount,
                  updated_avatar_path, quota_error_html)
    """
    if app_state is None:
        logger.warning("app_state not provided, using a temporary local dict")
        app_state = {}

    # Extract session ID from request
    session_id = "default"
    if request:
        session_id = request.session_hash or "default"
        logger.debug(f"Handling request for session: {session_id}")
    else:
        logger.warning("No request object provided, using default session ID")

    logger.info(f"Gradio input from {session_id}: '{user_input}'")

    # --- Get per-session API keys ---
    if not has_valid_keys(session_id, app_state):
        safe_history = append_to_history(session_history_state, user_input, 'Please provide your API keys first.')
        overlay_html = create_tab_overlay_html(
            tab_amount=current_tab, balance=current_balance,
            prev_tab=current_tab, prev_balance=current_balance,
            avatar_path=avatar_path,
            tip_percentage=current_tip_percentage, tip_amount=current_tip_amount
        )
        return (
            "", safe_history, safe_history,
            get_current_order_state(session_id, app_state), None,
            overlay_html, current_tab, current_balance, current_tab, current_balance,
            current_tip_percentage, current_tip_amount, avatar_path, ""
        )

    api_key_state = get_api_key_state(session_id, app_state)
    gemini_key = api_key_state['gemini_key']
    cartesia_key = api_key_state.get('cartesia_key')

    # Lazy-initialise per-session LLM and TTS
    llm = get_session_llm(session_id, gemini_key, tools)
    cartesia_client = get_session_tts(session_id, cartesia_key)

    # Use the user's gemini key for RAG if no dedicated RAG key was provided
    effective_rag_key = rag_api_key or gemini_key

    # Call text processing logic
    quota_error_html = ""
    try:
        # Use batch state commits to optimize remote dictionary operations
        with batch_state_commits(session_id, app_state):
            response_text, updated_history, updated_history_for_gradio, updated_order, _ = process_order(
                user_input_text=user_input,
                current_session_history=session_history_state,
                llm=llm,
                rag_retriever=rag_retriever,
                api_key=effective_rag_key,
                session_id=session_id,
                app_state=app_state
            )

            # Check for the quota-error sentinel returned by the processor
            if response_text == QUOTA_ERROR_SENTINEL:
                quota_error_html = create_quota_error_html()
                response_text = "It looks like your API key has hit its rate limit. Please check the popup for details."
                updated_history = append_to_history(session_history_state, user_input, response_text)
                updated_history_for_gradio = updated_history

        # --- Get Voice Audio ---
        audio_data = None
        if cartesia_client and response_text and response_text.strip():
            try:
                audio_data = get_voice_audio(response_text, cartesia_client)
            except Exception as tts_err:
                logger.warning(f"TTS generation failed: {tts_err}")
                audio_data = None
            if audio_data is None:
                logger.warning("Failed to get audio data from get_voice_audio.")
        else:
            logger.info("No response text generated or TTS not available, skipping TTS.")

        # Get updated payment state for overlay
        payment_state = get_payment_state(session_id, app_state)
        new_tab, new_balance, new_tip_percentage, new_tip_amount = get_overlay_payment_data(payment_state)

        # Avatar is now static
        final_avatar_path = avatar_path

        # Create overlay HTML with animation from previous to new values
        overlay_html = create_tab_overlay_html(
            tab_amount=new_tab,
            balance=new_balance,
            prev_tab=current_tab,
            prev_balance=current_balance,
            avatar_path=final_avatar_path,
            tip_percentage=new_tip_percentage,
            tip_amount=new_tip_amount
        )

        return (
            "", updated_history, updated_history_for_gradio, updated_order, audio_data,
            overlay_html, new_tab, new_balance, current_tab, current_balance,
            new_tip_percentage, new_tip_amount, final_avatar_path, quota_error_html
        )

    except Exception as e:
        if isinstance(e, SessionLimitExceededError):
            # Handle session limit exceeded specifically
            logger.warning(f"Session limit exceeded: {e}")
            friendly = "The bar is at capacity right now! Please try again in a moment."
            # No quota error popup for session limit exceeded
        elif is_quota_error(e):
            quota_error_html = create_quota_error_html()
            friendly = "It looks like your API key has hit its rate limit. Please check the popup for details."
        else:
            logger.exception(f"Error during process_order: {e}")
            friendly = "I'm having a small hiccup behind the bar, but I can still help you with drinks while I sort it out."

        safe_history = append_to_history(session_history_state, user_input, friendly)
        overlay_html = create_tab_overlay_html(
            tab_amount=current_tab, balance=current_balance,
            prev_tab=current_tab, prev_balance=current_balance,
            avatar_path=avatar_path,
            tip_percentage=current_tip_percentage, tip_amount=current_tip_amount
        )
        return (
            "", safe_history, safe_history,
            get_current_order_state(session_id, app_state), None,
            overlay_html, current_tab, current_balance, current_tab, current_balance,
            current_tip_percentage, current_tip_amount, avatar_path, quota_error_html
        )

def clear_chat_state(
    request: gr.Request,
    app_state: Optional[MutableMapping] = None
) -> Tuple[List, List, List, None]:
    """
    Clear UI/session state including audio.
    
    Returns:
        Tuple of (empty_chatbot, empty_history, empty_order, no_audio)
    """
    session_id = "default"
    if request:
        session_id = request.session_hash or "default"

    logger.info(f"Clear button clicked for session {session_id} - Resetting session state.")

    if app_state is None:
         logger.warning("app_state not provided for clear_chat_state, using ephemeral dict")
         app_state = {}

    # Reset the backend state
    try:
        reset_session_state(session_id, app_state)
    except Exception:
        logger.exception("Failed to reset session state")
        return [], [], [], None

    return [], [], [], None


def handle_gradio_input_stream(
    user_input: str,
    session_history_state: List[Dict[str, str]],
    current_tab: float,
    current_balance: float,
    current_tip_percentage: Optional[int],
    current_tip_amount: float,
    request: gr.Request,
    tools=None,
    rag_retriever=None,
    rag_api_key: Optional[str] = None,
    app_state: Optional[MutableMapping] = None,
    avatar_path: str = "assets/bartender_avatar.jpg"
):
    """
    Streaming Gradio callback for real-time text and audio generation.
    
    Args:
        Same as handle_gradio_input
        
    Yields:
        Streaming updates for Gradio interface
    """
    if app_state is None:
        logger.warning("app_state not provided, using a temporary local dict")
        app_state = {}

    # Extract session ID from request
    session_id = "default"
    if request:
        session_id = request.session_hash or "default"
    else:
        logger.warning("No request object provided, using default session ID")

    # Get API keys
    api_key_state = get_api_key_state(session_id, app_state)
    gemini_key = api_key_state['gemini_key']
    cartesia_key = api_key_state.get('cartesia_key')

    # Get session-specific clients
    try:
        llm = get_session_llm(session_id, gemini_key, tools)
        cartesia_client = get_session_tts(session_id, cartesia_key)
    except Exception as e:
        logger.error(f"Failed to get session clients: {e}")
        yield {
            'type': 'error',
            'content': "Failed to initialize session. Please refresh.",
            'history': session_history_state,
            'audio': None
        }
        return


    # Start streaming processing
    try:
        # Use the user's gemini key for RAG if no dedicated RAG key was provided
        effective_rag_key = rag_api_key or gemini_key

        # Start streaming processing
        response_stream = process_order_stream(
            user_input, session_history_state, llm,
            rag_retriever, effective_rag_key, session_id, app_state
        )

        updated_history = session_history_state[:]
        # Note: updated_history will be fully populated when completion or error event is received.
        # This keeps compatibility with the streaming generator structure.

        for event in response_stream:
            if event['type'] == 'text_chunk':
                # Yield text chunk for immediate display
                yield {
                    'type': 'text_chunk',
                    'content': event['content'],
                    'partial': event['partial']
                }

            elif event['type'] == 'sentence':
                # Generate audio for complete sentence
                if cartesia_client:
                    try:
                        audio_data = get_voice_audio(
                            event['content'], cartesia_client
                        )
                        if audio_data:
                            yield {
                                'type': 'audio_chunk',
                                'content': audio_data,
                                'sentence': event['content']
                            }
                    except Exception as tts_err:
                        logger.warning(f"TTS generation failed: {tts_err}")

            elif event['type'] == 'complete':
                # Final response ready
                final_text = event['content']

                # Update history
                updated_history = append_to_history(session_history_state, user_input, final_text)

                # Get final payment state
                final_payment_state = get_payment_state(session_id, app_state)
                new_tab, new_balance, new_tip_percentage, new_tip_amount = get_overlay_payment_data(final_payment_state)

                # Avatar is now static
                final_avatar_path = avatar_path

                # Create overlay HTML
                overlay_html = create_tab_overlay_html(
                    tab_amount=new_tab,
                    balance=new_balance,
                    prev_tab=current_tab,
                    prev_balance=current_balance,
                    avatar_path=final_avatar_path,
                    tip_percentage=new_tip_percentage,
                    tip_amount=new_tip_amount
                )

                # Yield completion event
                yield {
                    'type': 'complete',
                    'content': final_text,
                    'history': updated_history,
                    'order': get_current_order_state(session_id, app_state),
                    'overlay_html': overlay_html,
                    'avatar_path': final_avatar_path
                }

            elif event['type'] == 'error':
                # Handle errors
                error_text = event['content']

                updated_history = append_to_history(session_history_state, user_input, error_text)

                yield {
                    'type': 'error',
                    'content': error_text,
                    'history': updated_history
                }

    except SessionLimitExceededError as e:
        # Handle session limit exceeded
        logger.warning(f"Session limit exceeded: {e}")
        error_message = "The bar is at capacity right now! Please try again in a moment."

        error_history = append_to_history(session_history_state, user_input, error_message)

        error_payload = {
            'type': 'error',
            'content': error_message,
            'history': error_history
        }

        yield error_payload

    except Exception as e:
        # Handle quota errors and other exceptions
        if is_quota_error(e):
            quota_error_html = create_quota_error_html()
            error_message = "It looks like your API key has hit its rate limit. Please check the popup for details."
        else:
            logger.exception(f"Critical error in handle_gradio_input_stream: {e}")
            error_message = "I'm sorry, an unexpected error occurred. Please try again."
            quota_error_html = None

        error_history = append_to_history(session_history_state, user_input, error_message)

        error_payload = {
            'type': 'error',
            'content': error_message,
            'history': error_history
        }

        # Add quota error HTML if applicable
        if quota_error_html:
            error_payload['quota_error_html'] = quota_error_html

        yield error_payload


def handle_gradio_streaming_input(
    user_input: str,
    session_history_state: List[Dict[str, str]],
    current_tab: float,
    current_balance: float,
    current_tip_percentage: Optional[int],
    current_tip_amount: float,
    streaming_enabled: bool,
    request: gr.Request,
    tools=None,
    rag_retriever=None,
    rag_api_key: Optional[str] = None,
    app_state: Optional[MutableMapping] = None,
    avatar_path: str = "assets/bartender_avatar.jpg"
):
    """
    Handle Gradio input with streaming support.
    
    Args:
        streaming_enabled: Whether to use streaming or traditional mode
        
    Returns:
        Updates for Gradio interface components
    """
    if streaming_enabled:
        # Use streaming handler
        return handle_gradio_input_stream(
            user_input, session_history_state, current_tab, current_balance,
            current_tip_percentage, current_tip_amount, request, tools,
            rag_retriever, rag_api_key, app_state, avatar_path
        )
    else:
        # Use traditional handler
        return handle_gradio_input(
            user_input, session_history_state, current_tab, current_balance,
            current_tip_percentage, current_tip_amount, request, tools,
            rag_retriever, rag_api_key, app_state, avatar_path
        )
