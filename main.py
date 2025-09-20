#!/usr/bin/env python3
"""
MayaMCP - AI Bartending Agent

Main application entry point for Maya, the philosophical bartender.
"""

import os
import sys
from functools import partial

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import (
    setup_logging, 
    get_api_keys, 
    validate_api_keys
)
from src.config.logging_config import get_logger
from src.llm import initialize_llm, get_all_tools
from src.config.model_config import get_model_config, is_valid_gemini_model
from src.rag import initialize_vector_store, initialize_memvid_store
from src.voice import initialize_cartesia_client
from src.ui import launch_bartender_interface, handle_gradio_input, clear_chat_state
from src.utils import initialize_state

def main():
    """Main application entry point."""
    # Setup logging
    logger = setup_logging()
    logger.info("Starting MayaMCP - AI Bartending Agent")
    
    try:
        # Validate API keys
        api_keys = get_api_keys()
        if not validate_api_keys():
            logger.error("Required API keys not found. Please check your .env file.")
            logger.error("Required: GEMINI_API_KEY, CARTESIA_API_KEY")
            sys.exit(1)
        
        logger.info("API keys validated successfully")

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

        # Initialize LLM with tools
        tools = get_all_tools()
        llm = initialize_llm(api_key=api_keys["google_api_key"], tools=tools)
        logger.info(f"LLM initialized with {len(tools)} tools")
        
        # Initialize RAG system - try Memvid first, fallback to FAISS
        try:
            # Try Memvid first
            logger.info("Attempting to initialize Memvid-based RAG...")
            rag_retriever, rag_documents = initialize_memvid_store()
            rag_index = None  # Memvid uses retriever instead of index
            logger.info(f"Memvid RAG system initialized with {len(rag_documents)} documents")
        except Exception as e:
            logger.warning(f"Memvid initialization failed: {e}. Falling back to FAISS...")
            try:
                rag_index, rag_documents = initialize_vector_store()
                rag_retriever = None  # FAISS uses index instead of retriever
                logger.info(f"FAISS RAG system initialized with {len(rag_documents)} documents")
            except Exception as e2:
                logger.warning(f"FAISS initialization also failed: {e2}. Continuing without RAG.")
                rag_index, rag_documents, rag_retriever = None, None, None
        
        # Initialize Cartesia TTS client
        try:
            cartesia_client = initialize_cartesia_client(api_keys["cartesia_api_key"])
            logger.info("Cartesia TTS client initialized")
        except Exception as e:
            logger.warning(f"Cartesia initialization failed: {e}. Continuing without TTS.")
            cartesia_client = None
        
        # Create partially applied handler functions with dependencies
        # Pass the rag_retriever from our local scope
        rag_retriever_param = rag_retriever if 'rag_retriever' in locals() else None
        
        handle_input_with_deps = partial(
            handle_gradio_input,
            llm=llm,
            cartesia_client=cartesia_client,
            rag_index=rag_index,
            rag_documents=rag_documents,
            rag_retriever=rag_retriever_param,
            api_key=api_keys["google_api_key"]
        )
        
        # Launch the Gradio interface
        logger.info("Launching Gradio interface...")
        try:
            launch_bartender_interface(
                handle_input_fn=handle_input_with_deps,
                clear_state_fn=clear_chat_state
            )
        except Exception as ui_err:
            logger.warning(f"Failed to launch Gradio interface: {ui_err}. Application will continue without UI.")
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Critical error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()