#!/usr/bin/env python3
"""
Test script to verify Maya's functionality. Used by Claude.
"""

import sys
import os
from pathlib import Path

# Compute absolute path to src directory based on this test file's location
test_file_dir = Path(__file__).resolve().parent
repo_root_dir = test_file_dir.parent
sys.path.insert(0, str(repo_root_dir))

from src.config import get_api_keys, setup_logging
from src.llm import initialize_llm, get_all_tools  
from src.rag import initialize_vector_store
from src.voice import initialize_cartesia_client
from src.conversation.processor import process_order
from src.utils.state_manager import initialize_state, get_current_order_state, get_order_history

def test_maya_interaction():
    """Test Maya's full interaction workflow"""
    logger = None
    llm = None
    rag_index = None
    cartesia_client = None
    
    try:
        # Setup and logging
        logger = setup_logging()
        logger.info("Starting Maya interaction test")
        
        # Get and validate API keys
        try:
            api_keys = get_api_keys()
            
            # Validate required API keys are present
            required_keys = ["google_api_key", "cartesia_api_key"]
            missing_keys = []
            for key in required_keys:
                if key not in api_keys or not api_keys[key]:
                    missing_keys.append(key)
            
            if missing_keys:
                error_msg = f"Missing required API keys: {', '.join(missing_keys)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
            logger.info("API keys validated successfully")
            
        except Exception as e:
            error_msg = f"Failed to get or validate API keys: {e}"
            if logger:
                logger.error(error_msg)
            else:
                print(f"❌ {error_msg}")
            raise
        
        # Initialize components with individual error handling
        try:
            logger.info("Initializing state manager...")
            initialize_state()
            logger.info("✅ State manager initialized")
        except Exception as e:
            error_msg = f"Failed to initialize state manager: {e}"
            logger.error(error_msg)
            raise
        
        try:
            logger.info("Getting LLM tools...")
            tools = get_all_tools()
            logger.info(f"✅ Retrieved {len(tools)} LLM tools")
        except Exception as e:
            error_msg = f"Failed to get LLM tools: {e}"
            logger.error(error_msg)
            raise
        
        try:
            logger.info("Initializing LLM client...")
            llm = initialize_llm(api_key=api_keys["google_api_key"], tools=tools)
            logger.info("✅ LLM client initialized")
        except Exception as e:
            error_msg = f"Failed to initialize LLM client: {e}"
            logger.error(error_msg)
            raise
        
        try:
            logger.info("Initializing vector store...")
            rag_index, rag_documents = initialize_vector_store()
            logger.info(f"✅ Vector store initialized with {len(rag_documents)} documents")
        except Exception as e:
            error_msg = f"Failed to initialize vector store: {e}"
            logger.error(error_msg)
            raise
        
        try:
            logger.info("Initializing Cartesia TTS client...")
            cartesia_client = initialize_cartesia_client(api_keys["cartesia_api_key"])
            logger.info("✅ Cartesia TTS client initialized")
        except Exception as e:
            error_msg = f"Failed to initialize Cartesia client: {e}"
            logger.error(error_msg)
            raise
        
        # Test conversation
        session_history = []
        
        response, updated_history, _, updated_order, _ = process_order(
            user_input_text="I would like a whiskey on the rocks please",
            current_session_history=session_history,
            llm=llm,
            rag_index=rag_index,
            rag_documents=rag_documents,
            api_key=api_keys["google_api_key"]
        )
        
        # Test getting the order
        response2, _, _, _, _ = process_order(
            user_input_text="What's in my order?",
            current_session_history=updated_history,
            llm=llm,
            rag_index=rag_index, 
            rag_documents=rag_documents,
            api_key=api_keys["google_api_key"]
        )
        
        # Test bill
        response3, _, _, _, _ = process_order(
            user_input_text="What's my bill?",
            current_session_history=updated_history,
            llm=llm,
            rag_index=rag_index,
            rag_documents=rag_documents, 
            api_key=api_keys["google_api_key"]
        )
        
        if not response3:
            logger.warning("Empty response for bill inquiry")
            
        logger.info("✅ Maya interaction test completed successfully")
        return True
        
    except Exception as e:
        error_msg = f"Maya interaction test failed: {e}"
        if logger:
            logger.error(error_msg, exc_info=True)
        else:
            print(f"❌ {error_msg}")
        
        # Perform cleanup if needed
        try:
            if logger:
                logger.info("Performing cleanup after test failure...")
            # Add any specific cleanup logic here if needed
            # For example, clearing state, closing connections, etc.
        except Exception as cleanup_error:
            cleanup_msg = f"Cleanup failed: {cleanup_error}"
            if logger:
                logger.error(cleanup_msg)
            else:
                print(f"❌ {cleanup_msg}")
        
        # Re-raise the original exception to ensure test failure is reported
        raise

if __name__ == "__main__":
    try:
        success = test_maya_interaction()
        if success:
            print("✅ Test completed successfully!")
            sys.exit(0)
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        sys.exit(1)