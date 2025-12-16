"""Gradio event handlers."""

from typing import List, Dict, Tuple, Any, MutableMapping, Optional
import gradio as gr
from ..config.logging_config import get_logger
from ..conversation.processor import process_order
from ..voice.tts import get_voice_audio
from ..utils.state_manager import (
    reset_session_state,
    get_current_order_state,
    get_payment_state,
    set_tip,
    DEFAULT_PAYMENT_STATE
)
from .tab_overlay import (
    create_tab_overlay_html,
    generate_tip_notification,
    generate_tip_removal_notification
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
    llm,
    cartesia_client=None,
    rag_index=None,
    rag_documents: Optional[List[str]] = None,
    rag_retriever=None,
    api_key: Optional[str] = None,
    app_state: Optional[MutableMapping] = None,
    avatar_path: str = "assets/bartender_avatar.jpg"
) -> Tuple[str, List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, Any]], Any,
           str, float, float, float, float, Optional[int], float, str]:
    """
    Gradio callback: Takes input/state, calls logic & TTS, returns updates.

    Args:
        user_input: User's text input
        session_history_state: Current session history
        current_tab: Current tab amount (for animation)
        current_balance: Current balance (for animation)
        current_tip_percentage: Current tip percentage (for overlay)
        current_tip_amount: Current tip amount (for overlay)
        request: Gradio request object containing session info
        llm: Initialized LLM instance
        cartesia_client: Cartesia client for TTS (optional)
        rag_index: FAISS index for RAG (optional)
        rag_documents: Documents for RAG (optional)
        api_key: API key for various services
        app_state: Distributed state store (modal.Dict or dict)
        avatar_path: Current avatar path state (from Gradio state)

    Returns:
        Tuple of (empty_input, updated_history, updated_history_for_gradio,
                  updated_order, audio_data, overlay_html, new_tab, new_balance,
                  prev_tab, prev_balance, new_tip_percentage, new_tip_amount, updated_avatar_path)

    Requirements: 2.2, 6.2, 7.3, 7.4
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
    emotion_state = None  # Default to None (no change) if not parsed
    try:
        response_text, updated_history, updated_history_for_gradio, updated_order, _, emotion_state = process_order(
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
        # Return with unchanged payment state and unchanged avatar on error
        overlay_html = create_tab_overlay_html(
            tab_amount=current_tab,
            balance=current_balance,
            prev_tab=current_tab,
            prev_balance=current_balance,
            avatar_path=avatar_path, # Keep previous avatar state
            tip_percentage=current_tip_percentage,
            tip_amount=current_tip_amount
        )
        return (
            "", safe_history, safe_history,
            get_current_order_state(session_id, app_state), None,
            overlay_html, current_tab, current_balance, current_tab, current_balance,
            current_tip_percentage, current_tip_amount, avatar_path
        )

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
    new_tab = payment_state['tab_total']
    new_balance = payment_state['balance']
    new_tip_percentage = payment_state['tip_percentage']
    new_tip_amount = payment_state['tip_amount']

    # Resolve Avatar based on Emotion State
    # Note: Assumes placeholder files exist: maya_neutral.mp4, maya_happy.mp4, etc.
    import os
    
    # Defaults to current path (persistence)
    final_avatar_path = avatar_path 

    if emotion_state:
        # Safe fallback if unknown emotion
        valid_emotions = ["neutral", "happy", "flustered", "thinking", "mixing", "upset"]
        if emotion_state not in valid_emotions:
            emotion_state = "neutral"
        
        # Construct filename
        # e.g. assets/maya_happy.mp4
        emotion_filename = f"maya_{emotion_state}.mp4" 
        potential_path = f"assets/{emotion_filename}"
        
        # Check if file exists, if not, do not change state (or fallback to neutral if logic dictates)
        # Here we only update if the emotion asset exists
        if os.path.exists(potential_path):
             final_avatar_path = potential_path
             logger.info(f"Emotion: {emotion_state} -> Avatar Path: {final_avatar_path}")
        else:
             logger.warning(f"Emotion {emotion_state} detected but asset {potential_path} missing. Keeping current avatar.")

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

    # Return updates including audio data (which might be None)
    # First return value is empty string to clear the input field
    # Also return overlay HTML and payment state for animation
    return (
        "", updated_history, updated_history_for_gradio, updated_order, audio_data,
        overlay_html, new_tab, new_balance, current_tab, current_balance,
        new_tip_percentage, new_tip_amount, final_avatar_path
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


def handle_tip_button_click(
    percentage: int,
    current_tip_percentage: Optional[int],
    current_tab: float,
    current_balance: float,
    session_history_state: List[Dict[str, str]],
    request: gr.Request,
    llm,
    cartesia_client=None,
    rag_index=None,
    rag_documents: Optional[List[str]] = None,
    rag_retriever=None,
    api_key: Optional[str] = None,
    app_state: Optional[MutableMapping] = None,
    avatar_path: str = "assets/bartender_avatar.jpg"
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], Any, str, float, float,
           float, float, Optional[int], float, str]:
    """
    Handle tip button click event.
    
    Implements toggle behavior: clicking the same percentage removes the tip.
    Sends notification to Maya about tip selection/removal.
    
    Args:
        percentage: The tip percentage clicked (10, 15, or 20)
        current_tip_percentage: Currently selected tip percentage or None
        current_tab: Current tab amount
        current_balance: Current balance
        session_history_state: Current session history
        request: Gradio request object
        llm: LLM instance for processing Maya's response
        cartesia_client: TTS client (optional)
        rag_index: RAG index (optional)
        rag_documents: RAG documents (optional)
        rag_retriever: RAG retriever (optional)
        api_key: API key (optional)
        app_state: State store
        avatar_path: Current avatar path state (from Gradio state)
        
    Returns:
        Tuple of (updated_history, updated_history_for_gradio, audio_data,
                  overlay_html, new_tab, new_balance, prev_tab, prev_balance,
                  new_tip_percentage, new_tip_amount, updated_avatar_path)
                  
    Requirements: 7.2, 7.5, 7.6, 7.11, 7.12
    """
    from ..conversation.processor import process_order
    from ..voice.tts import get_voice_audio
    
    if app_state is None:
        logger.warning("app_state not provided for tip handler")
        app_state = {}
    
    # Extract session ID
    session_id = "default"
    if request:
        session_id = request.session_hash
    
    logger.info(f"Tip button clicked for session {session_id}: {percentage}%")
    
    # Determine if this is a toggle (remove tip) or new selection
    is_toggle = (percentage == current_tip_percentage)
    
    # Update tip in state manager (handles toggle behavior internally)
    try:
        new_tip_amount, _total = set_tip(session_id, app_state, percentage)
    except ValueError as e:
        logger.exception("Invalid tip percentage")
        # Return unchanged state on error
        payment_state = get_payment_state(session_id, app_state)
        overlay_html = create_tab_overlay_html(
            tab_amount=current_tab,
            balance=current_balance,
            prev_tab=current_tab,
            prev_balance=current_balance,
            avatar_path=avatar_path,
            tip_percentage=current_tip_percentage,
            tip_amount=payment_state.get('tip_amount', 0.0)
        )
        return (
            session_history_state, session_history_state, None,
            overlay_html, current_tab, current_balance, current_tab, current_balance,
            current_tip_percentage, payment_state.get('tip_amount', 0.0), avatar_path
        )
    
    # Get updated payment state
    payment_state = get_payment_state(session_id, app_state)
    new_tip_percentage = payment_state['tip_percentage']
    new_tab = payment_state['tab_total']
    new_balance = payment_state['balance']
    
    # Generate notification message for Maya
    if is_toggle:
        # Tip was removed (toggle behavior)
        notification_message = generate_tip_removal_notification()
    else:
        # New tip selected
        notification_message = generate_tip_notification(
            percentage=percentage,
            tip_amount=new_tip_amount,
            tab_total=new_tab
        )
    
    logger.info(f"Sending tip notification to Maya: {notification_message}")
    
    # Process the notification through Maya
    emotion_state = None
    try:
        response_text, updated_history, updated_history_for_gradio, _, _, emotion_state = process_order(
            user_input_text=notification_message,
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
        logger.exception(f"Error processing tip notification: {e}")
        # Return with updated tip state but no Maya response, keep avatar
        overlay_html = create_tab_overlay_html(
            tab_amount=new_tab,
            balance=new_balance,
            prev_tab=current_tab,
            prev_balance=current_balance,
            avatar_path=avatar_path,
            tip_percentage=new_tip_percentage,
            tip_amount=new_tip_amount
        )
        return (
            session_history_state, session_history_state, None,
            overlay_html, new_tab, new_balance, current_tab, current_balance,
            new_tip_percentage, new_tip_amount, avatar_path
        )
    
    # Get voice audio for Maya's response
    audio_data = None
    if cartesia_client and response_text and response_text.strip():
        try:
            audio_data = get_voice_audio(response_text, cartesia_client)
        except Exception as tts_err:
            logger.warning(f"TTS generation failed for tip response: {tts_err}")
            
    # Resolve Avatar based on Emotion State
    import os
    final_avatar_path = avatar_path
    if emotion_state:
        valid_emotions = ["neutral", "happy", "flustered", "thinking", "mixing", "upset"]
        if emotion_state not in valid_emotions:
            emotion_state = "neutral"
        
        emotion_filename = f"maya_{emotion_state}.mp4" 
        potential_path = f"assets/{emotion_filename}"
        
        if os.path.exists(potential_path):
             final_avatar_path = potential_path
    
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
        updated_history, updated_history_for_gradio, audio_data,
        overlay_html, new_tab, new_balance, current_tab, current_balance,
        new_tip_percentage, new_tip_amount, final_avatar_path
    )
