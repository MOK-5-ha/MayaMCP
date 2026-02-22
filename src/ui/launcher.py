"""Gradio interface launcher."""

import gradio as gr
from typing import Optional, Callable, List, Dict, Any, MutableMapping
from ..config.logging_config import get_logger
from .components import setup_avatar, create_streaming_components, create_streaming_toggle
from .tab_overlay import create_tab_overlay_html
from .api_key_modal import create_help_instructions_md, handle_key_submission
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
    handle_key_submission_fn: Optional[Callable] = None,
    handle_streaming_input_fn: Optional[Callable] = None,
    avatar_path: Optional[str] = None
) -> gr.Blocks:
    """
    Create the Gradio interface for Maya the bartender and return it.

    Args:
        handle_input_fn: Function to handle user input
        clear_state_fn: Function to clear chat state
        handle_key_submission_fn: Function to validate and store API keys (BYOK).
                                  If None, the default handle_key_submission is used.
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
    if not avatar_path:
        import os
        if os.path.exists("assets/bartender_avatar.mp4"):
             avatar_path = "assets/bartender_avatar.mp4"
        else:
             avatar_path = "assets/bartender_avatar.jpg"
            
    effective_avatar_path = avatar_path

    # Create the interface
    ui_theme = gr.themes.Ocean()

    with gr.Blocks(theme=ui_theme) as demo:
        gr.Markdown("# MOK 5-ha - Meet Maya the Bartender")

        # --- Define Session State Variables ---
        history_state = gr.State([])
        order_state = gr.State([])
        keys_validated_state = gr.State(False)
        
        # --- Payment State Variables (Requirements: 2.2, 6.2, 7.2, 7.3) ---
        tab_state = gr.State(DEFAULT_PAYMENT_STATE['tab_total'])
        balance_state = gr.State(DEFAULT_PAYMENT_STATE['balance'])
        prev_tab_state = gr.State(DEFAULT_PAYMENT_STATE['tab_total'])
        prev_balance_state = gr.State(DEFAULT_PAYMENT_STATE['balance'])
        tip_percentage_state = gr.State(DEFAULT_PAYMENT_STATE['tip_percentage'])
        tip_amount_state = gr.State(DEFAULT_PAYMENT_STATE['tip_amount'])

        # =================================================================
        # BYOK API Key Form (visible by default, hidden after validation)
        # =================================================================
        with gr.Column(visible=True) as api_key_column:
            gr.Markdown(
                "## Welcome to MOK 5-ha!\n"
                "To get started, please provide your API keys below."
            )

            gemini_key_input = gr.Textbox(
                label="Gemini API Key (required)",
                placeholder="Enter your Google Gemini API key...",
                type="password",
            )
            cartesia_key_input = gr.Textbox(
                label="Cartesia API Key (optional, for voice)",
                placeholder="Enter your Cartesia API key for TTS...",
                type="password",
            )

            key_error_display = gr.Markdown(value="", visible=True)

            submit_keys_btn = gr.Button("Start Chatting", variant="primary")

            with gr.Accordion("How to get API keys", open=False):
                gr.Markdown(create_help_instructions_md())

        # =================================================================
        # Main Chat Interface (hidden until keys validated)
        # =================================================================
        with gr.Column(visible=False) as chat_column:
            gr.Markdown(
                "Welcome to MOK 5-ha! I'm Maya, your virtual bartender. "
                "Ask me for a drink or check your order."
            )

            # Quota error overlay (initially empty, populated on 429 errors)
            quota_error_display = gr.HTML(value="", visible=True)

            # Streaming mode toggle
            streaming_toggle = create_streaming_toggle()

            # --- Main Row with 2 Columns (Equal Scaling) ---
            with gr.Row():

                # --- Column 1: Avatar with Tab Overlay ---
                with gr.Column(scale=1, min_width=200):
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
                    # Get streaming components
                    (chatbot_display, agent_audio_output, msg_input,
                     streaming_text_display, streaming_audio_player) = create_streaming_components()

                    # Hidden textbox to receive tip button clicks from JavaScript
                    tip_click_input = gr.Textbox(
                        value="",
                        visible=False,
                        elem_id="tip-click-input"
                    )
                    with gr.Row():
                        clear_btn = gr.Button("Clear Conversation")
                        submit_btn = gr.Button("Send", variant="primary")

        # =================================================================
        # Event Handlers
        # =================================================================

        # --- BYOK Key Submission ---
        if handle_key_submission_fn is None:
            handle_key_submission_fn = handle_key_submission

        submit_keys_btn.click(
            handle_key_submission_fn,
            inputs=[gemini_key_input, cartesia_key_input],
            outputs=[key_error_display, api_key_column, chat_column, keys_validated_state],
        )

        # Avatar state validation to ensure persistence
        avatar_state = gr.State(effective_avatar_path)

        # --- Chat Input Submission ---
        submit_inputs = [
            msg_input, history_state, tab_state, balance_state,
            tip_percentage_state, tip_amount_state, avatar_state, streaming_toggle
        ]
        submit_outputs = [
            msg_input, chatbot_display, history_state, order_state,
            agent_audio_output, avatar_overlay, tab_state, balance_state,
            prev_tab_state, prev_balance_state, tip_percentage_state,
            tip_amount_state, avatar_state, quota_error_display,
            streaming_text_display, streaming_audio_player
        ]
        
        def handle_input_wrapper(
            user_input: str, history: List[Dict[str, str]], 
            tab: float, balance: float, tip_pct: Optional[int], tip_amt: float,
            avatar: str, streaming_enabled: bool, request: gr.Request,
            tools=None, rag_retriever=None, rag_api_key: Optional[str] = None,
            app_state: Optional[MutableMapping] = None
        ):
            """Wrapper that chooses streaming or traditional handler based on toggle."""
            if handle_streaming_input_fn:
                return handle_streaming_input_fn(
                    user_input, history, tab, balance, tip_pct, tip_amt,
                    streaming_enabled, request, tools, rag_retriever, rag_api_key, app_state, avatar
                )
            else:
                return handle_input_fn(
                    user_input, history, tab, balance, tip_pct, tip_amt,
                    request, tools, rag_retriever, rag_api_key, app_state, avatar
                )
        
        msg_input.submit(handle_input_wrapper, submit_inputs, submit_outputs)
        submit_btn.click(handle_input_wrapper, submit_inputs, submit_outputs)
        
        # --- Tip Button JavaScript Callback ---
        tip_button_js = """
        function handleTipClick(percentage) {
            const tipInput = document.querySelector('#tip-click-input textarea, #tip-click-input input');
            if (tipInput) {
                tipInput.value = percentage.toString();
                tipInput.dispatchEvent(new Event('input', { bubbles: true }));
                setTimeout(() => {
                    tipInput.dispatchEvent(new Event('change', { bubbles: true }));
                }, 50);
            }
        }
        window.handleTipClick = handleTipClick;
        """
        gr.HTML(f"<script>{tip_button_js}</script>", visible=False)

        # --- Clear Button ---
        clear_outputs = [
            chatbot_display, history_state, order_state, agent_audio_output,
            avatar_overlay, tab_state, balance_state, prev_tab_state,
            prev_balance_state, tip_percentage_state, tip_amount_state,
            avatar_state, streaming_text_display, streaming_audio_player,
            quota_error_display
        ]
        
        def clear_with_overlay(request: gr.Request):
            result = clear_state_fn(request)
            overlay_html = create_avatar_with_overlay(
                avatar_path=effective_avatar_path,
                tab_amount=DEFAULT_PAYMENT_STATE['tab_total'],
                balance=DEFAULT_PAYMENT_STATE['balance'],
                prev_tab=DEFAULT_PAYMENT_STATE['tab_total'],
                prev_balance=DEFAULT_PAYMENT_STATE['balance'],
                tip_percentage=DEFAULT_PAYMENT_STATE['tip_percentage'],
                tip_amount=DEFAULT_PAYMENT_STATE['tip_amount']
            )
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
                DEFAULT_PAYMENT_STATE['tip_amount'],
                effective_avatar_path,
                "",  # streaming_text_display (empty)
                None,  # streaming_audio_player (empty)
                ""   # quota_error_display (empty)
            )
        
        clear_btn.click(clear_with_overlay, [], clear_outputs)
        
        # --- Tip Button Click Handler ---
        def handle_tip_click_wrapper(
            tip_percentage_str: str,
            current_tip_pct: Optional[int],
            current_tab: float,
            current_balance: float,
            history: List[Dict[str, str]],
            current_avatar: str,
            request: gr.Request
        ):
            """Wrapper to handle tip button clicks via the hidden input."""
            if not tip_percentage_str or not tip_percentage_str.strip():
                overlay_html = create_avatar_with_overlay(
                    avatar_path=current_avatar,
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
                    current_tab, current_balance, current_tip_pct, 0.0, current_avatar
                )
            
            try:
                percentage = int(tip_percentage_str.strip())
            except ValueError:
                logger.warning(f"Invalid tip percentage: {tip_percentage_str}")
                overlay_html = create_avatar_with_overlay(
                    avatar_path=current_avatar,
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
                    current_tab, current_balance, current_tip_pct, 0.0, current_avatar
                )
            
            overlay_html = create_avatar_with_overlay(
                avatar_path=current_avatar,
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
                current_tab, current_balance, current_tip_pct, 0.0, current_avatar
            )
        
        # Wire tip click input to handler
        tip_click_outputs = [
            tip_click_input, chatbot_display, history_state, agent_audio_output,
            avatar_overlay, tab_state, balance_state, prev_tab_state, prev_balance_state,
            tip_percentage_state, tip_amount_state, avatar_state
        ]
        tip_click_inputs = [
            tip_click_input, tip_percentage_state, tab_state, balance_state, history_state, avatar_state
        ]
        
        tip_click_input.change(
            handle_tip_click_wrapper,
            tip_click_inputs,
            tip_click_outputs
        )

    # Return the interface for external serving
    logger.info("Gradio interface object ready")
    return demo
