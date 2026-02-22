"""UI component setup and management."""

import requests
import io
from PIL import Image
from typing import Optional, Tuple
import gradio as gr
from ..config.logging_config import get_logger

logger = get_logger(__name__)


def setup_avatar(
    avatar_url: Optional[str] = None,
    save_path: str = "assets/bartender_avatar.jpg"
) -> str:
    """
    Download and setup the bartender avatar image.
    
    Args:
        avatar_url: URL to download avatar from. Uses default if None.
        save_path: Path to save the avatar image
        
    Returns:
        Path to the saved avatar image
    """
    # Default avatar URL
    if avatar_url is None:
        avatar_url = "https://github.com/gen-ai-capstone-project-bartender-agent/MOK-5-ha/blob/main/assets/bartender_avatar_ai_studio.jpeg?raw=true"

    try:
        # Download avatar
        response = requests.get(avatar_url)
        if response.status_code == 200:
            avatar_bytes = response.content
            avatar_image = Image.open(io.BytesIO(avatar_bytes))
            logger.info("Successfully downloaded avatar image")
        else:
            logger.warning(f"Failed to download avatar. Status code: {response.status_code}")
            # Create a blank avatar as fallback
            avatar_image = Image.new('RGB', (300, 300), color=(73, 109, 137))
            
    except Exception as e:
        logger.error(f"Error downloading avatar: {e}")
        # Create a blank avatar as fallback
        avatar_image = Image.new('RGB', (300, 300), color=(73, 109, 137))

    try:
        # Save avatar
        avatar_image.save(save_path)
        logger.info(f"Avatar saved to {save_path}")
        return save_path
        
    except Exception as e:
        logger.error(f"Error saving avatar: {e}")
        # Return a fallback path
        return "assets/bartender_avatar.jpg"


def create_streaming_components(
) -> Tuple[gr.Chatbot, gr.Audio, gr.Textbox, gr.Textbox, gr.Audio]:
    """
    Create Gradio components for streaming interface.
    
    Returns:
        Tuple of (chatbot_display, agent_audio_output, msg_input, 
                  streaming_text_display, streaming_audio_player)
    """
    # Main chatbot for conversation history
    chatbot_display = gr.Chatbot(
        [],
        elem_id="chatbot",
        label="Conversation",
        height=489,
        type="messages"
    )
    
    # Traditional audio output (fallback)
    agent_audio_output = gr.Audio(
        label="Agent Voice",
        autoplay=True,
        streaming=False,
        format="wav",
        show_label=True,
        interactive=False
    )
    
    # Streaming text display for real-time text
    streaming_text_display = gr.Textbox(
        label="Streaming Response",
        placeholder="Maya is thinking...",
        lines=3,
        max_lines=8,
        interactive=False,
        visible=False
    )
    
    # Streaming audio player for immediate playback
    streaming_audio_player = gr.Audio(
        label="Live Voice",
        autoplay=True,
        streaming=True,
        format="wav",
        show_label=True,
        interactive=False,
        visible=False
    )
    
    # Message input
    msg_input = gr.Textbox(
        label="Your Order / Message",
        placeholder="What can I get for you? (e.g., 'I'd like a Margarita', 'Show my order')"
    )
    
    return (
        chatbot_display,
        agent_audio_output,
        msg_input,
        streaming_text_display,
        streaming_audio_player
    )


def create_streaming_toggle():
    """
    Create toggle for streaming vs traditional mode.
    
    Returns:
        gr.Checkbox: Streaming mode toggle
    """
    return gr.Checkbox(
        label="Enable Streaming Mode",
        value=True,
        info="Show text and audio in real-time as Maya generates responses"
    )