"""
Video generation module using Replicate API.
"""

import os
import sys
from pathlib import Path
from typing import Optional
import time

try:
    import replicate
    from replicate.exceptions import ReplicateError
except ImportError:
    replicate = None

from src.config.api_keys import get_api_keys

# Default model: Stability AI's Stable Video Diffusion (SVD) XT
# This is a good baseline for image-to-video.
DEFAULT_MODEL = "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb47ac63f69aa00bc95d88447591c9324f235fa99c"

def check_dependencies() -> bool:
    """Check if replicate is installed."""
    if replicate is None:
        print("Error: 'replicate' package is not installed.")
        print("Please install it running: pip install replicate")
        return False
    return True

def animate_avatar(
    input_path: str = "assets/bartender_avatar.jpg",
    output_path: str = "assets/bartender_avatar.mp4",
    model_version: str = DEFAULT_MODEL,
    motion_bucket_id: int = 127,
    cond_aug: float = 0.02,
) -> bool:
    """
    Generate a video from an image using Replicate.

    Args:
        input_path: Path to input image.
        output_path: Path to save output video.
        model_version: Replicate model version string.
        motion_bucket_id: Controls amount of motion (higher = more motion).
        cond_aug: Conditional augmentation (noise level).

    Returns:
        True if successful, False otherwise.
    """
    if not check_dependencies():
        return False

    api_token = os.environ.get("REPLICATE_API_TOKEN")
    if not api_token:
        # Try finding it in our config helper if user added it there
        # But usually Replicate SDK checks env var directly.
        print("Error: REPLICATE_API_TOKEN environment variable not set.")
        print("Please set it in your .env file.")
        return False

    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: Input file not found at {input_file.absolute()}")
        return False

    print(f"Starting animation generation for {input_file.name}...")
    print(f"Model: {model_version}")
    
    try:
        # Open source file
        with open(input_file, "rb") as file_handle:
            output = replicate.run(
                model_version,
                input={
                    "input_image": file_handle,
                    "video_length": "25_frames_with_svd_xt",
                    "sizing_strategy": "maintain_aspect_ratio",
                    "frames_per_second": 6,
                    "motion_bucket_id": motion_bucket_id,
                    "cond_aug": cond_aug,
                    "decoding_t": 1,
                    "seed": int(time.time()) 
                }
            )
        
        # Output is usually a URL or a list containing a URL
        video_url = output
        if isinstance(output, list):
            video_url = output[0]
            
        print(f"Generation successful! downloading from {video_url}...")
        
        # Download the video
        import requests
        response = requests.get(video_url)
        response.raise_for_status()
        
        output_file = Path(output_path)
        # Ensure directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "wb") as f:
            f.write(response.content)
            
        print(f"Video saved to {output_file.absolute()}")
        return True

    except ReplicateError as e:
        print(f"Replicate API Error: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        # Print full traceback for debugging
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Allow running directly to test
    if len(sys.argv) > 1:
        inp = sys.argv[1]
    else:
        inp = "assets/bartender_avatar.jpg"
        
    animate_avatar(input_path=inp)
