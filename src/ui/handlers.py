"""Gradio event handlers."""

from typing import List, Dict, Tuple, Any, Optional, MutableMapping
import gradio as gr
from ..config.logging_config import get_logger
from ..conversation.processor import process_order
from ..voice.tts import get_voice_audio
from ..utils.state_manager import reset_session_state, get_current_order_state

logger = get_logger(__name__)

def handle_gradio_input(
    user_input: str,
    session_history_state: List[Dict[str, str]],
    request: gr.Request, 
    llm,
    cartesia_client=None,
    rag_index=None,
    rag_documents: List[str] = None,
    rag_retriever=None,
    api_key: str = None,
    app_state: MutableMapping = None
) -> Tuple[str, List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, Any]], Any]:
    """
    Gradio callback: Takes input/state, calls logic & TTS, returns updates.
    
    Args:
        user_input: User's text input
        session_history_state: Current session history
        request: Gradio request object containing session info
        llm: Initialized LLM instance
        cartesia_client: Cartesia client for TTS (optional)
        rag_index: FAISS index for RAG (optional)
        rag_documents: Documents for RAG (optional)
        api_key: API key for various services
        app_state: Distributed state store (modal.Dict or dict)
        
    Returns:
        Tuple of (empty_input, updated_history, updated_history_for_gradio, updated_order, audio_data)
    """
    if app_state is None:
        # Fallback for local testing if not injected
        logger.warning("app_state not provided, using a temporary local dict (state will be lost on restart)")
        app_state = {}

    # Extract session ID from request
    session_id = "default"
    if request:
        session_id = request.session_hash
        logger.debug(f"Handling request for session: {session_id}")
    else:
        logger.warning("No request object provided, using default session ID")

    logger.info(f"Gradio input from {session_id}: '{user_input}'")
    logger.debug(f"Received session history state (len {len(session_history_state)}): {session_history_state}")

    # Call text processing logic first
    try:
        response_text, updated_history, updated_history_for_gradio, updated_order, _ = process_order(
            user_input_text=user_input,
            current_session_history=session_history_state,
            llm=llm,
            rag_index=rag_index,
            rag_documents=rag_documents,
            rag_retriever=rag_retriever,
            api_key=api_key,
            session_id=session_id,
            app_state=app_state
        )
    except Exception as e:
        logger.exception(f"Error during process_order: {e}")
        friendly = "I'm having a small hiccup behind the bar, but I can still help you with drinks while I sort it out."
        safe_history = session_history_state[:]
        safe_history.append({'role': 'user', 'content': user_input})
        safe_history.append({'role': 'assistant', 'content': friendly})
        return "", safe_history, safe_history, get_current_order_state(session_id, app_state), None

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

    # Return updates including audio data (which might be None)
    # First return value is empty string to clear the input field
    return "", updated_history, updated_history_for_gradio, updated_order, audio_data

def clear_chat_state(request: gr.Request, app_state: MutableMapping = None) -> Tuple[List, List, List, None]:
    """
    Clear UI/session state including audio.
    
    Returns:
        Tuple of (empty_chatbot, empty_history, empty_order, no_audio)
    """
    session_id = "default"
    if request:
        session_id = request.session_hash
    
    logger.info(f"Clear button clicked for session {session_id} - Resetting session state.")
    
    if app_state is None:
         logger.warning("app_state not provided for clear_chat_state, using ephemeral dict")
         app_state = {}

    # Reset the backend state
    try:
        reset_session_state(session_id, app_state)
    except Exception:
        logger.exception("Failed to reset session state")
        # Return empty state to ensure clean UI even if backend reset failed
        return [], [], [], None

    # Return cleared state tuple
    return [], [], [], None
