#!/usr/bin/env python3
"""
MayaMCP - AI Bartending Agent

Main application entry point for Maya, the philosophical bartender.
"""

import os
import sys
from functools import partial

from config import (
    setup_logging, 
    get_api_keys, 
)
from config.logging_config import get_logger
from llm import get_all_tools
from config.model_config import get_model_config, is_valid_gemini_model
from rag import initialize_memvid_store
from ui import launch_bartender_interface, handle_gradio_input, clear_chat_state, handle_gradio_streaming_input
from ui.api_key_modal import handle_key_submission
from utils import initialize_state
from utils.state_manager import start_session_cleanup, stop_session_cleanup
from utils.rate_limiter import get_rate_limiter

def main():
    """Main application entry point."""
    # Setup logging
    logger = setup_logging()
    logger.info("Starting MayaMCP - AI Bartending Agent (BYOK mode)")
    
    try:
        # Load API keys (optional now -- used only for RAG initialisation)
        api_keys = get_api_keys()
        google_api_key = api_keys.get("google_api_key")

        if google_api_key:
            logger.info("Found GEMINI_API_KEY in environment (will use for RAG)")
        else:
            logger.info("No GEMINI_API_KEY in environment; RAG will use session keys or be skipped")

        # Proactive model validation (warning-only)
        model_cfg = get_model_config()
        model_name = model_cfg.get("model_version")
        if model_name and not is_valid_gemini_model(model_name):
            logger.warning(
                f"Configured GEMINI_MODEL_VERSION '{model_name}' not in known list. "
                "Maya will continue to start, but you may want to verify the model "
                "identifier against Google AI docs: https://ai.google.dev/gemini-api/docs/models"
            )

        # Initialize application state
        initialize_state()
        logger.info("Application state initialized")
        
        # Start security services
        start_session_cleanup()
        get_rate_limiter()  # Initialize singleton
        logger.info("Security services initialized: session cleanup, rate limiting")

        # Get tool definitions (static, shared across all sessions)
        tools = get_all_tools()
        logger.info(f"Loaded {len(tools)} tool definitions")

        # Initialize RAG system - Memvid only
        rag_retriever = None

        if google_api_key:
            try:
                logger.info("Attempting to initialize Memvid-based RAG...")
                rag_retriever, rag_documents = initialize_memvid_store()
                logger.info(f"Memvid RAG system initialized with {len(rag_documents)} documents")
            except Exception as e:
                logger.warning(f"Memvid initialization failed: {e}. Continuing without RAG.")
        else:
            logger.info("Skipping RAG initialization (no server-side Gemini key)")
        
        # NOTE: LLM and TTS are NOT initialised here.
        # Each user session provides their own keys (BYOK).
        # Per-session clients are lazily created via src/llm/session_registry.

        # Initialize app state for local run (ephemeral, in-memory)
        app_state = {}
        
        # Create partially applied handler functions with dependencies
        handle_input_with_deps = partial(
            handle_gradio_input,
            tools=tools,
            rag_retriever=rag_retriever,
            rag_api_key=google_api_key,
            app_state=app_state
        )

        handle_streaming_input_with_deps = partial(
            handle_gradio_streaming_input,
            tools=tools,
            rag_retriever=rag_retriever,
            rag_api_key=google_api_key,
            app_state=app_state
        )

        clear_state_with_deps = partial(
            clear_chat_state,
            app_state=app_state
        )

        handle_keys_with_deps = partial(
            handle_key_submission,
            app_state=app_state
        )
        
        # Launch the Gradio interface
        logger.info("Launching Gradio interface...")
        try:
            interface = launch_bartender_interface(
                handle_input_fn=handle_input_with_deps,
                handle_streaming_input_fn=handle_streaming_input_with_deps,
                clear_state_fn=clear_state_with_deps,
                handle_key_submission_fn=handle_keys_with_deps,
            )
            # Local/dev launch only; Modal serves via ASGI in deploy.py
            if os.getenv("PYTHON_ENV", "development").lower() != "production":
                interface.queue().launch(
                    server_name=os.getenv("HOST", "0.0.0.0"),
                    server_port=int(os.getenv("PORT", "8000")),
                    debug=os.getenv("DEBUG", "False").lower() == "true",
                )
        except Exception:
            logger.exception("Failed to launch Gradio interface")
            raise
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        # Cleanup security services
        try:
            # Clean up rate limiter session data
            rate_limiter = get_rate_limiter()
            rate_limiter.cleanup_expired_sessions(max_age_seconds=0)
            stop_session_cleanup()
            logger.info("Security services stopped")
        except Exception as e:
            logger.exception(f"Error stopping security services: {e}")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Critical error starting application: {e}")
        # Cleanup security services on error
        try:
            # Clean up rate limiter session data
            rate_limiter = get_rate_limiter()
            rate_limiter.cleanup_expired_sessions(max_age_seconds=0)
            stop_session_cleanup()
        except Exception:
            logger.exception("Error during security cleanup")
        sys.exit(1)

if __name__ == "__main__":
    main()
