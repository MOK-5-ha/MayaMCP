"""Gradio interface launcher."""

import gradio as gr
from typing import Optional, Callable
from ..config.logging_config import get_logger
from .components import setup_avatar

logger = get_logger(__name__)

def launch_bartender_interface(
    handle_input_fn: Callable,
    clear_state_fn: Callable,
    avatar_path: Optional[str] = None
) -> gr.Blocks:
    """
    Create the Gradio interface for Maya the bartender and return it.

    Args:
        handle_input_fn: Function to handle user input
        clear_state_fn: Function to clear chat state
        avatar_path: Path to avatar image (will setup default if None)

    Returns:
        gr.Blocks: The interface object (not launched), suitable for external serving
    """
    # Setup avatar if not provided
    if avatar_path is None:
        try:
            avatar_path = setup_avatar()
        except Exception as e:
            logger.error(f"Failed to setup avatar: {e}")
            avatar_path = None
    
    # Create the interface
    ui_theme = gr.themes.Ocean()
    
    with gr.Blocks(theme=ui_theme) as demo:
        gr.Markdown("# MOK 5-ha - Meet Maya the Bartender 🍹👋")
        gr.Markdown("Welcome to MOK 5-ha! I'm Maya, your virtual bartender. Ask me for a drink or check your order.")

        # --- Define Session State Variables ---
        history_state = gr.State([])
        order_state = gr.State([])

        # --- Restructured Main Row with 2 Columns (Equal Scaling) ---
        with gr.Row():

            # --- Column 1: Avatar Image ---
            with gr.Column(scale=1, min_width=200): 
                gr.Image(
                    value=avatar_path,  
                    label="Bartender Avatar",
                    show_label=False,
                    interactive=False,
                    height=600, 
                    elem_classes=["avatar-image"]
                )

            # --- Column 2: Chat Interface ---
            with gr.Column(scale=1): 
                chatbot_display = gr.Chatbot(
                    [],
                    elem_id="chatbot",
                    label="Conversation",
                    height=489, 
                    type="messages"
                )
                agent_audio_output = gr.Audio(
                    label="Agent Voice",
                    autoplay=True,
                    streaming=False,
                    format="wav",
                    show_label=True,
                    interactive=False
                )
                msg_input = gr.Textbox(
                    label="Your Order / Message",
                    placeholder="What can I get for you? (e.g., 'I'd like a Margarita', 'Show my order')"
                )
                with gr.Row():
                    clear_btn = gr.Button("Clear Conversation")
                    submit_btn = gr.Button("Send", variant="primary")

        # --- Event Handlers ---
        submit_inputs = [msg_input, history_state]
        submit_outputs = [msg_input, chatbot_display, history_state, order_state, agent_audio_output]
        
        msg_input.submit(handle_input_fn, submit_inputs, submit_outputs)
        submit_btn.click(handle_input_fn, submit_inputs, submit_outputs)

        clear_outputs = [chatbot_display, history_state, order_state, agent_audio_output]
        clear_btn.click(clear_state_fn, [history_state], clear_outputs)

    # Return the interface for external serving
    logger.info("Gradio interface object ready")
    return demo