"""Gradio interface launcher."""

import gradio as gr
from typing import Optional, Callable
from ..config.logging_config import get_logger
from .components import setup_avatar
from .tab_overlay import create_tab_overlay_html
from ..utils.state_manager import DEFAULT_PAYMENT_STATE

logger = get_logger(__name__)


def create_avatar_with_overlay(
    avatar_path: str,
    tab_amount: float = 0.0,
    balance: float = 1000.0,
    prev_tab: float = 0.0,
    prev_balance: float = 1000.0
) -> str:
    """
    Create avatar image with tab overlay component.
    
    Args:
        avatar_path: Path to the avatar image
        tab_amount: Current tab total
        balance: Current user balance
        prev_tab: Previous tab amount (for animation)
        prev_balance: Previous balance (for animation)
        
    Returns:
        HTML string with avatar and overlay
        
    Requirements: 2.1
    """
    return create_tab_overlay_html(
        tab_amount=tab_amount,
        balance=balance,
        prev_tab=prev_tab,
        prev_balance=prev_balance,
        avatar_path=avatar_path
    )

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
            logger.exception(f"Failed to setup avatar: {e}")
            avatar_path = None
    
    # Use default avatar path if not provided
    effective_avatar_path = avatar_path or "assets/bartender_avatar.jpg"

    # Create the interface
    ui_theme = gr.themes.Ocean()

    with gr.Blocks(theme=ui_theme) as demo:
        gr.Markdown("# MOK 5-ha - Meet Maya the Bartender 🍹👋")
        gr.Markdown("Welcome to MOK 5-ha! I'm Maya, your virtual bartender. Ask me for a drink or check your order.")

        # --- Define Session State Variables ---
        history_state = gr.State([])
        order_state = gr.State([])
        
        # --- Payment State Variables (Requirements: 2.2, 6.2) ---
        tab_state = gr.State(DEFAULT_PAYMENT_STATE['tab_total'])  # Current tab amount
        balance_state = gr.State(DEFAULT_PAYMENT_STATE['balance'])  # Current balance
        prev_tab_state = gr.State(DEFAULT_PAYMENT_STATE['tab_total'])  # Previous tab for animation
        prev_balance_state = gr.State(DEFAULT_PAYMENT_STATE['balance'])  # Previous balance for animation

        # --- Restructured Main Row with 2 Columns (Equal Scaling) ---
        with gr.Row():

            # --- Column 1: Avatar with Tab Overlay (Requirements: 2.1) ---
            with gr.Column(scale=1, min_width=200):
                # Create initial overlay HTML
                initial_overlay_html = create_avatar_with_overlay(
                    avatar_path=effective_avatar_path,
                    tab_amount=DEFAULT_PAYMENT_STATE['tab_total'],
                    balance=DEFAULT_PAYMENT_STATE['balance'],
                    prev_tab=DEFAULT_PAYMENT_STATE['tab_total'],
                    prev_balance=DEFAULT_PAYMENT_STATE['balance']
                )
                avatar_overlay = gr.HTML(
                    value=initial_overlay_html,
                    label="Bartender Avatar",
                    show_label=False,
                    elem_classes=["avatar-overlay"]
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
        # Include tab/balance state in inputs and outputs for animation (Requirements: 2.2, 2.3)
        submit_inputs = [msg_input, history_state, tab_state, balance_state]
        submit_outputs = [
            msg_input, chatbot_display, history_state, order_state, agent_audio_output,
            avatar_overlay, tab_state, balance_state, prev_tab_state, prev_balance_state
        ]
        
        msg_input.submit(handle_input_fn, submit_inputs, submit_outputs)
        submit_btn.click(handle_input_fn, submit_inputs, submit_outputs)

        # Clear outputs include tab overlay reset (Requirements: 1.1)
        clear_outputs = [
            chatbot_display, history_state, order_state, agent_audio_output,
            avatar_overlay, tab_state, balance_state, prev_tab_state, prev_balance_state
        ]
        
        # Create wrapper for clear function that includes avatar_path
        def clear_with_overlay(request: gr.Request):
            result = clear_state_fn(request)
            # Reset overlay to default state
            overlay_html = create_avatar_with_overlay(
                avatar_path=effective_avatar_path,
                tab_amount=DEFAULT_PAYMENT_STATE['tab_total'],
                balance=DEFAULT_PAYMENT_STATE['balance'],
                prev_tab=DEFAULT_PAYMENT_STATE['tab_total'],
                prev_balance=DEFAULT_PAYMENT_STATE['balance']
            )
            # Return: chatbot, history, order, audio, overlay, tab, balance, prev_tab, prev_balance
            return (
                result[0],  # chatbot
                result[1],  # history
                result[2],  # order
                result[3],  # audio
                overlay_html,
                DEFAULT_PAYMENT_STATE['tab_total'],
                DEFAULT_PAYMENT_STATE['balance'],
                DEFAULT_PAYMENT_STATE['tab_total'],
                DEFAULT_PAYMENT_STATE['balance']
            )
        
        clear_btn.click(clear_with_overlay, [], clear_outputs)

    # Return the interface for external serving
    logger.info("Gradio interface object ready")
    return demo
