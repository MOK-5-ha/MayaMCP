"""Text-to-speech functionality using Cartesia."""

import re
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
import logging

from ..config.logging_config import get_logger
from ..config.model_config import get_cartesia_config

logger = get_logger(__name__)

# Define retryable exceptions for Cartesia
CARTESIA_RETRYABLE_EXCEPTIONS = (ConnectionError, TimeoutError)

def clean_text_for_tts(text: str) -> str:
    """
    Clean text for TTS to improve pronunciation and remove unwanted punctuation.
    
    Args:
        text: Raw text to be spoken
        
    Returns:
        Cleaned text suitable for TTS
    """
    if not text:
        return text
    
    # Replace "MOK 5-ha" with "Moksha" for proper pronunciation
    cleaned_text = re.sub(r'MOK 5-ha', 'Moksha', text, flags=re.IGNORECASE)
    
    # Remove problematic punctuation that TTS might pronounce
    # Keep periods, commas, question marks, exclamation marks for natural pauses
    # Remove: asterisks, hashtags, underscores, brackets, etc.
    punctuation_to_remove = [
        r'\*+',           # Asterisks (*,**,***)
        r'#+',            # Hashtags (#,##,###)
        r'_+',            # Underscores (_,__,___)
        r'`+',            # Backticks (`,'',''')
        r'\[.*?\]',       # Square brackets [text]
        r'[\[\]]',        # Individual square brackets
        r'\{.*?\}',       # Curly brackets {text}
        r'[{}]',          # Individual curly brackets
        r'<.*?>',         # Angle brackets <text>
        r'[<>]',          # Individual angle brackets
        r'~+',            # Tildes (~,~~)
        r'\^+',           # Carets (^,^^)
        r'=+',            # Equals signs (=,==,===)
        r'\|+',           # Pipes (|,||)
        r'\\+',           # Backslashes (\,\\)
        r'@+',            # At symbols (@,@@)
        r'&+',            # Ampersands (&,&&)
        r'%+',            # Percent signs (%,%%)
        r'\$+',           # Dollar signs ($,$$)
    ]
    
    for pattern in punctuation_to_remove:
        cleaned_text = re.sub(pattern, ' ', cleaned_text)
    
    # Clean up extra whitespace
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    
    # Log if significant changes were made
    if cleaned_text != text:
        logger.info(f"Cleaned TTS text: '{text[:30]}...' → '{cleaned_text[:30]}...'")
    
    return cleaned_text

def initialize_cartesia_client(api_key: str):
    """
    Initialize Cartesia client.
    
    Args:
        api_key: Cartesia API key
        
    Returns:
        Initialized Cartesia client
    """
    try:
        from cartesia import Cartesia
        
        client = Cartesia(api_key=api_key)
        logger.info("Successfully initialized Cartesia client.")
        return client
        
    except Exception as e:
        logger.error(f"Failed to initialize Cartesia client: {e}")
        raise RuntimeError("Cartesia client initialization failed.") from e

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type(CARTESIA_RETRYABLE_EXCEPTIONS),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
def get_voice_audio(
    text_to_speak: str, 
    cartesia_client, 
    voice_id: Optional[str] = None
) -> Optional[bytes]:
    """
    Call Cartesia API synchronously to synthesize speech and return WAV bytes.
    
    Args:
        text_to_speak: Text to convert to speech
        cartesia_client: Initialized Cartesia client
        voice_id: Voice ID to use (uses default from config if None)
        
    Returns:
        WAV audio data as bytes, or None if failed
    """
    if not text_to_speak or not text_to_speak.strip():
        logger.warning("get_voice_audio received empty text.")
        return None
        
    if not cartesia_client:
        logger.error("Cartesia client not provided, cannot generate audio.")
        return None

    try:
        # Get Cartesia configuration
        config = get_cartesia_config()
        if voice_id is None:
            voice_id = config["voice_id"]
        
        # Clean text for TTS (pronunciation fixes and punctuation removal)
        text_for_tts = clean_text_for_tts(text_to_speak)

        logger.info(f"Requesting TTS from Cartesia (Voice ID: {voice_id}) for: '{text_for_tts[:50]}...'")

        # Call Cartesia TTS API
        audio_generator = cartesia_client.tts.bytes(
            model_id=config["model_id"],
            transcript=text_for_tts,  
            voice={
                "mode": "id",
                "id": voice_id,
            },
            language=config["language"],
            output_format=config["output_format"],
        )

        # Concatenate chunks from the generator for a blocking result
        audio_data = b"".join(chunk for chunk in audio_generator)

        if not audio_data:
            logger.warning("Cartesia TTS returned empty audio data.")
            return None

        logger.info(f"Received {len(audio_data)} bytes of WAV audio data from Cartesia.")
        return audio_data

    except Exception as e:
        # Catch any other unexpected error during TTS
        logger.exception(f"Unexpected error generating voice audio with Cartesia: {e}")
        return None