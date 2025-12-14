"""Gradio interface launcher."""

import gradio as gr
from typing import Optional, Callable, Tuple, List, Dict, Any
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
    prev_balance: float = 1000.0,
    tip_percentage: Optional[int] = None,
    tip_amount: float = 0.0
) -> str:
    """
    Create avatar image with tab overlay component.
    
    Args:
        avatar_path: Path to the avatar image
        tab_amount: Current tab total
        balance: Current user balance
        prev_tab: Previous tab amount (for animation)
        prev_balance: Previous balance (for animation)
        tip_percentage: Currently selected tip percentage (10, 15, 20) or None
        tip_amount: Current tip amount
        
    Returns:
        HTML string with avatar and overlay
        
    Requirements: 2.1, 7.2, 7.3
    """
    return create_tab_overlay_html(
        tab_amount=tab_amount,
        balance=balance,
        prev_tab=prev_tab,
        prev_balance=prev_balance,
        avatar_path=avatar_path,
        tip_percentage=tip_percentage,
        tip_amount=tip_amount
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
        
        # --- Payment State Variables (Requirements: 2.2, 6.2, 7.2, 7.3) ---
        tab_state = gr.State(DEFAULT_PAYMENT_STATE['tab_total'])  # Current tab amount
        balance_state = gr.State(DEFAULT_PAYMENT_STATE['balance'])  # Current balance
        prev_tab_state = gr.State(DEFAULT_PAYMENT_STATE['tab_total'])  # Previous tab for animation
        prev_balance_state = gr.State(DEFAULT_PAYMENT_STATE['balance'])  # Previous balance for animation
        tip_percentage_state = gr.State(DEFAULT_PAYMENT_STATE['tip_percentage'])  # Current tip percentage (10, 15, 20, or None)
        tip_amount_state = gr.State(DEFAULT_PAYMENT_STATE['tip_amount'])  # Current tip amount

        # --- Restructured Main Row with 2 Columns (Equal Scaling) ---
        with gr.Row():

            # --- Column 1: Avatar with Tab Overlay (Requirements: 2.1, 7.1) ---
            with gr.Column(scale=1, min_width=200):
                # Create initial overlay HTML
                initial_overlay_html = create_avatar_with_overlay(
                    avatar_path=effective_avatar_path,
                    tab_amount=DEFAULT_PAYMENT_STATE['tab_total'],
                    balance=DEFAULT_PAYMENT_STATE['balance'],
                    prev_tab=DEFAULT_PAYMENT_STATE['tab_total'],
                    prev_balance=DEFAULT_PAYMENT_STATE['balance'],
                    tip_percentage=DEFAULT_PAYMENT_STATE['tip_percentage'],
                    tip_amount=DEFAULT_PAYMENT_STATE['tip_amount']
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
                # Hidden textbox to receive tip button clicks from JavaScript (Requirements: 7.1, 7.11)
                tip_click_input = gr.Textbox(
                    value="",
                    visible=False,
                    elem_id="tip-click-input"
                )
                with gr.Row():
                    clear_btn = gr.Button("Clear Conversation")
                    submit_btn = gr.Button("Send", variant="primary")

        # --- Event Handlers ---
        # Include tab/balance/tip state in inputs and outputs for animation (Requirements: 2.2, 2.3, 7.2, 7.3)
        submit_inputs = [msg_input, history_state, tab_state, balance_state, tip_percentage_state, tip_amount_state]
        submit_outputs = [
            msg_input, chatbot_display, history_state, order_state, agent_audio_output,
            avatar_overlay, tab_state, balance_state, prev_tab_state, prev_balance_state,
            tip_percentage_state, tip_amount_state
        ]
        
        msg_input.submit(handle_input_fn, submit_inputs, submit_outputs)
        submit_btn.click(handle_input_fn, submit_inputs, submit_outputs)
        
        # --- Tip Button JavaScript Callback (Requirements: 7.1, 7.11) ---
        # JavaScript to handle tip button clicks and trigger Gradio event
        tip_button_js = """
        function handleTipClick(percentage) {
            // Find the hidden tip input element
            const tipInput = document.querySelector('#tip-click-input textarea, #tip-click-input input');
            if (tipInput) {
                // Set the value to the percentage clicked
                tipInput.value = percentage.toString();
                // Trigger input event to notify Gradio
                tipInput.dispatchEvent(new Event('input', { bubbles: true }));
                // Small delay then trigger change event
                setTimeout(() => {
                    tipInput.dispatchEvent(new Event('change', { bubbles: true }));
                }, 50);
            }
        }
        // Make function globally available
        window.handleTipClick = handleTipClick;
        """
        
        # Add JavaScript to the page
        gr.HTML(f"<script>{tip_button_js}</script>", visible=False)

        # Clear outputs include tab overlay reset (Requirements: 1.1, 7.10)
        clear_outputs = [
            chatbot_display, history_state, order_state, agent_audio_output,
            avatar_overlay, tab_state, balance_state, prev_tab_state, prev_balance_state,
            tip_percentage_state, tip_amount_state
        ]
        
        # Create wrapper for clear function that includes avatar_path
        def clear_with_overlay(request: gr.Request):
            result = clear_state_fn(request)
            # Reset overlay to default state using DEFAULT_PAYMENT_STATE as single source of truth
            overlay_html = create_avatar_with_overlay(
                avatar_path=effective_avatar_path,
                tab_amount=DEFAULT_PAYMENT_STATE['tab_total'],
                balance=DEFAULT_PAYMENT_STATE['balance'],
                prev_tab=DEFAULT_PAYMENT_STATE['tab_total'],
                prev_balance=DEFAULT_PAYMENT_STATE['balance'],
                tip_percentage=DEFAULT_PAYMENT_STATE['tip_percentage'],
                tip_amount=DEFAULT_PAYMENT_STATE['tip_amount']
            )
            # Return: chatbot, history, order, audio, overlay, tab, balance, prev_tab, prev_balance, tip_pct, tip_amt
            return (
                result[0],  # chatbot
                result[1],  # history
                result[2],  # order
                result[3],  # audio
                overlay_html,
                DEFAULT_PAYMENT_STATE['tab_total'],
                DEFAULT_PAYMENT_STATE['balance'],
                DEFAULT_PAYMENT_STATE['tab_total'],
                DEFAULT_PAYMENT_STATE['balance'],
                DEFAULT_PAYMENT_STATE['tip_percentage'],
                DEFAULT_PAYMENT_STATE['tip_amount']
            )
        
        clear_btn.click(clear_with_overlay, [], clear_outputs)
        
        # --- Tip Button Click Handler (Requirements: 7.1, 7.2, 7.5, 7.6, 7.11, 7.12) ---
        # Note: The actual tip handling is done via the handle_tip_button_click function
        # which is called when the hidden tip_click_input changes.
        # The tip buttons in the overlay call handleTipClick(percentage) which updates
        # the hidden input, triggering this handler.
        # 
        # For now, we wire the tip click to send a message through the normal chat flow.
        # The tip notification message is generated and sent to Maya.
        
        def handle_tip_click_wrapper(
            tip_percentage_str: str,
            current_tip_pct: Optional[int],
            current_tab: float,
            current_balance: float,
            history: List[Dict[str, str]],
            request: gr.Request
        ):
            """Wrapper to handle tip button clicks via the hidden input."""
            from .handlers import handle_tip_button_click
            
            # Parse the percentage from the string
            if not tip_percentage_str or not tip_percentage_str.strip():
                # No tip click, return unchanged state
                overlay_html = create_avatar_with_overlay(
                    avatar_path=effective_avatar_path,
                    tab_amount=current_tab,
                    balance=current_balance,
                    prev_tab=current_tab,
                    prev_balance=current_balance,
                    tip_percentage=current_tip_pct,
                    tip_amount=0.0
                )
                return (
                    "", history, history, None,
                    overlay_html, current_tab, current_balance,
                    current_tab, current_balance, current_tip_pct, 0.0
                )
            
            try:
                percentage = int(tip_percentage_str.strip())
            except ValueError:
                logger.warning(f"Invalid tip percentage: {tip_percentage_str}")
                overlay_html = create_avatar_with_overlay(
                    avatar_path=effective_avatar_path,
                    tab_amount=current_tab,
                    balance=current_balance,
                    prev_tab=current_tab,
                    prev_balance=current_balance,
                    tip_percentage=current_tip_pct,
                    tip_amount=0.0
                )
                return (
                    "", history, history, None,
                    overlay_html, current_tab, current_balance,
                    current_tab, current_balance, current_tip_pct, 0.0
                )
            
            # This is a placeholder - the actual implementation requires
            # the LLM and other dependencies to be passed in.
            # For now, we'll just update the tip state without Maya's response.
            from ..utils.state_manager import set_tip, get_payment_state
            
            session_id = "default"
            if request:
                session_id = request.session_hash
            
            # Get app_state - this needs to be injected properly
            # For now, use a simple dict (will be replaced in main.py integration)
            app_state = {}
            
            try:
                new_tip_amount, total = set_tip(session_id, app_state, percentage)
            except ValueError as e:
                logger.error(f"Invalid tip percentage: {e}")
                overlay_html = create_avatar_with_overlay(
                    avatar_path=effective_avatar_path,
                    tab_amount=current_tab,
                    balance=current_balance,
                    prev_tab=current_tab,
                    prev_balance=current_balance,
                    tip_percentage=current_tip_pct,
                    tip_amount=0.0
                )
                return (
                    "", history, history, None,
                    overlay_html, current_tab, current_balance,
                    current_tab, current_balance, current_tip_pct, 0.0
                )
            
            payment_state = get_payment_state(session_id, app_state)
            new_tip_pct = payment_state['tip_percentage']
            new_tab = payment_state['tab_total']
            new_balance = payment_state['balance']
            
            overlay_html = create_avatar_with_overlay(
                avatar_path=effective_avatar_path,
                tab_amount=new_tab,
                balance=new_balance,
                prev_tab=current_tab,
                prev_balance=current_balance,
                tip_percentage=new_tip_pct,
                tip_amount=new_tip_amount
            )
            
            return (
                "", history, history, None,
                overlay_html, new_tab, new_balance,
                current_tab, current_balance, new_tip_pct, new_tip_amount
            )
        
        # Wire tip click input to handler
        tip_click_outputs = [
            tip_click_input, chatbot_display, history_state, agent_audio_output,
            avatar_overlay, tab_state, balance_state, prev_tab_state, prev_balance_state,
            tip_percentage_state, tip_amount_state
        ]
        tip_click_inputs = [
            tip_click_input, tip_percentage_state, tab_state, balance_state, history_state
        ]
        
        tip_click_input.change(
            handle_tip_click_wrapper,
            tip_click_inputs,
            tip_click_outputs
        )

    # Return the interface for external serving
    logger.info("Gradio interface object ready")
    return demo
