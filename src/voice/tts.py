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
    
    # Convert monetary amounts to speech-friendly format
    def format_money_for_speech(match):
        amount = match.group(1)
        try:
            if '.' in amount:
                dollars_str, frac_str = amount.split('.', 1)
                dollars = int(dollars_str)
                # Round fractional part to nearest cent
                # Validate that frac_str contains only digits before conversion
                if frac_str.isdigit():
                    cents = int(round(float(f"0.{frac_str}") * 100))
                else:
                    cents = 0
                if cents >= 100:
                    dollars += 1
                    cents = 0
            else:
                dollars = int(amount)
                cents = 0

            if dollars == 0:
                if cents == 0:
                    return "zero dollars"
                elif cents == 1:
                    return "1 cent"
                else:
                    return f"{cents} cents"
            elif cents == 0:
                if dollars == 1:
                    return "1 dollar"
                else:
                    return f"{dollars} dollars"
            else:
                dollar_str = "1 dollar" if dollars == 1 else f"{dollars} dollars"
                cent_str = "1 cent" if cents == 1 else f"{cents} cents"
                return f"{dollar_str} and {cent_str}"
        except ValueError:
            # If parsing fails, just remove the dollar sign
            return amount
    
    # Pattern to match valid $XX.XX format and convert to speech-friendly text
    cleaned_text = re.sub(r'\$(\d+(?:\.\d{1,2})?)(?!\d)', format_money_for_speech, cleaned_text)
    
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