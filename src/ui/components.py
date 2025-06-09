"""UI component setup and management."""

import requests
import io
from PIL import Image
from typing import Optional
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