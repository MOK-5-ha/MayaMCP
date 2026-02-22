"""Streaming TTS functionality for pipelined audio generation."""

import threading
from typing import Generator, Optional, Callable
import queue
import time

from ..config.logging_config import get_logger
from .tts import get_voice_audio

logger = get_logger(__name__)


def generate_streaming_audio(
    sentence_generator: Generator[str, None, None],
    cartesia_client,
    voice_id: Optional[str] = None,
    on_audio_ready: Optional[Callable[[bytes], None]] = None
) -> Generator[dict, None, None]:
    """
    Generate streaming audio from sentence generator.
    
    Args:
        sentence_generator: Generator yielding complete sentences
        cartesia_client: Initialized Cartesia client
        voice_id: Voice ID to use
        on_audio_ready: Callback for when audio chunks are ready
        
    Yields:
        Dict with audio generation status and data
    """
    audio_queue = queue.Queue()
    generation_complete = threading.Event()
    
    def audio_worker():
        """Background thread to generate audio from sentences."""
        try:
            for sentence in sentence_generator:
                if not sentence or not sentence.strip():
                    continue
                    
                logger.debug(f"Generating TTS for sentence: '{sentence[:50]}...'")
                
                # Generate audio for this sentence
                audio_data = get_voice_audio(sentence, cartesia_client, voice_id)
                
                if audio_data:
                    audio_chunk = {
                        'type': 'audio_chunk',
                        'content': audio_data,
                        'sentence': sentence
                    }
                    
                    if on_audio_ready:
                        on_audio_ready(audio_data)
                    
                    audio_queue.put(audio_chunk)
                else:
                    # TTS failed for this sentence
                    logger.warning(f"TTS generation failed for sentence: '{sentence}'")
                    audio_queue.put({
                        'type': 'tts_error',
                        'content': None,
                        'sentence': sentence
                    })
            
            # Signal completion
            audio_queue.put({'type': 'generation_complete', 'content': None})
            
        except Exception as e:
            logger.error(f"Error in audio worker thread: {e}")
            audio_queue.put({
                'type': 'worker_error',
                'content': str(e),
                'sentence': None
            })
        finally:
            generation_complete.set()
    
    # Start audio generation in background thread
    worker_thread = threading.Thread(target=audio_worker, daemon=True)
    worker_thread.start()
    
    # Yield results as they become available
    try:
        while not generation_complete.is_set() or not audio_queue.empty():
            try:
                # Wait for audio chunk with timeout
                chunk = audio_queue.get(timeout=0.1)
                yield chunk
                
                if chunk['type'] == 'generation_complete':
                    break
                    
            except queue.Empty:
                # No chunk available, yield heartbeat to keep connection alive
                yield {'type': 'heartbeat', 'content': None}
                
    except Exception as e:
        logger.error(f"Error in streaming audio generator: {e}")
        yield {'type': 'generator_error', 'content': str(e)}
    
    # Wait for worker thread to complete
    worker_thread.join(timeout=5.0)
    if worker_thread.is_alive():
        logger.warning("Audio worker thread did not complete cleanly")


def create_pipelined_tts_generator(
    sentence_stream: Generator[dict, None, None],
    cartesia_client,
    voice_id: Optional[str] = None
) -> Generator[dict, None, None]:
    """
    Create a generator that handles both text streaming and TTS pipelining.
    
    Args:
        sentence_stream: Generator yielding sentence events from LLM
        cartesia_client: Initialized Cartesia client
        voice_id: Voice ID to use
        
    Yields:
        Dict with combined streaming and TTS events
    """
    # Extract sentences from the stream
    def sentence_extractor():
        for event in sentence_stream:
            if event['type'] == 'sentence':
                yield event['content']
            elif event['type'] == 'complete':
                # Flush any remaining content
                break
    
    # Start streaming audio generation
    sentence_gen = sentence_extractor()
    audio_gen = generate_streaming_audio(sentence_gen, cartesia_client, voice_id)
    
    # Yield text events immediately, audio events as they become available
    audio_events = list()
    
    for text_event in sentence_stream:
        # Always yield text events first
        yield text_event
        
        # Collect any available audio events
        if text_event['type'] in ['sentence', 'complete']:
            # Process accumulated audio events
            for audio_event in audio_events:
                yield audio_event
            audio_events.clear()
    
    # Yield any remaining audio events
    for audio_event in audio_events:
        yield audio_event
