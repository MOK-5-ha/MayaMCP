"""Gradio event handlers."""

from typing import List, Dict, Tuple, Any
from ..config.logging_config import get_logger
from ..conversation.processor import process_order
from ..voice.tts import get_voice_audio
from ..utils.state_manager import reset_session_state, get_current_order_state

logger = get_logger(__name__)

def handle_gradio_input(
    user_input: str,
    session_history_state: List[Dict[str, str]],
    llm,
    cartesia_client=None,
    rag_index=None,
    rag_documents: List[str] = None,
    api_key: str = None
) -> Tuple[str, List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, Any]], Any]:
    """
    Gradio callback: Takes input/state, calls logic & TTS, returns updates.
    
    Args:
        user_input: User's text input
        session_history_state: Current session history
        llm: Initialized LLM instance
        cartesia_client: Cartesia client for TTS (optional)
        rag_index: FAISS index for RAG (optional)
        rag_documents: Documents for RAG (optional)
        api_key: API key for various services
        
    Returns:
        Tuple of (empty_input, updated_history, updated_history_for_gradio, updated_order, audio_data)
    """
    logger.info(f"Gradio input: '{user_input}'")
    logger.debug(f"Received session history state (len {len(session_history_state)}): {session_history_state}")

    # Call text processing logic first
    response_text, updated_history, updated_history_for_gradio, updated_order, _ = process_order(
        user_input_text=user_input,
        current_session_history=session_history_state,
        llm=llm,
        rag_index=rag_index,
        rag_documents=rag_documents,
        api_key=api_key
    )

    # --- Get Voice Audio ---
    audio_data = None 
    if cartesia_client and response_text and response_text.strip():
        audio_data = get_voice_audio(response_text, cartesia_client) 
        if audio_data is None:
            logger.warning("Failed to get audio data from get_voice_audio.")
    else:
        logger.info("No response text generated or TTS not available, skipping TTS.")

    # Return updates including audio data (which might be None)
    # First return value is empty string to clear the input field
    return "", updated_history, updated_history, get_current_order_state(), audio_data

def clear_chat_state() -> Tuple[List, List, List, None]:
    """
    Clear UI/session state including audio.
    
    Returns:
        Tuple of (empty_chatbot, empty_history, empty_order, no_audio)
    """
    logger.info("Clear button clicked - Resetting session state.")
    
    # Reset the backend state
    reset_session_state()
    
    # Return empty lists for Chatbot/history/order, and None for the audio component
    return [], [], [], None