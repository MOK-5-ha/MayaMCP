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
        except FileNotFoundError as e:
            error_msg = f"State manager initialization failed - required file not found: {e.filename if e.filename else 'unknown file'} ({e})"
            logger.error(error_msg)
            raise
        except PermissionError as e:
            error_msg = f"State manager initialization failed - permission denied accessing: {e.filename if e.filename else 'unknown file'} ({e})"
            logger.error(error_msg)
            raise
        except OSError as e:
            error_msg = f"State manager initialization failed - OS error: {e.strerror if e.strerror else str(e)} (errno: {e.errno if e.errno else 'unknown'})"
            logger.error(error_msg)
            raise
        except ValueError as e:
            error_msg = f"State manager initialization failed - invalid configuration or value: {e}"
            logger.error(error_msg)
            raise
        except ImportError as e:
            error_msg = f"State manager initialization failed - missing required module: {e.name if e.name else 'unknown module'} ({e})"
            logger.error(error_msg)
            raise
        except Exception as e:
            error_msg = f"State manager initialization failed with unexpected error: {type(e).__name__}: {e}"
            logger.error(error_msg, exc_info=True)
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
        # Validate first response
        if not isinstance(response, str) or not response.strip():
            if logger:
                logger.error("First interaction response is empty or not a string")
            raise AssertionError("First interaction response is empty or not a string")
        if not isinstance(updated_history, list) or not updated_history or not isinstance(updated_history[-1], dict):
            if logger:
                logger.error("Updated history after first interaction is missing or malformed")
            raise AssertionError("Updated history after first interaction is missing or malformed")
        if 'role' not in updated_history[-1] or 'content' not in updated_history[-1] or not updated_history[-1]['content']:
            if logger:
                logger.error("Updated history last entry after first interaction lacks required keys/content")
            raise AssertionError("Updated history last entry after first interaction lacks required keys/content")
        if len(updated_history) < 2:
            if logger:
                logger.error("Updated history after first interaction is unexpectedly short")
            raise AssertionError("Updated history after first interaction is unexpectedly short")
        if not isinstance(updated_order, list):
            if logger:
                logger.error("Updated order after first interaction is not a list")
            raise AssertionError("Updated order after first interaction is not a list")
        
        # Test getting the order
        response2, updated_history2, _, _, _ = process_order(
            user_input_text="What's in my order?",
            current_session_history=updated_history,
            llm=llm,
            rag_index=rag_index, 
            rag_documents=rag_documents,
            api_key=api_keys["google_api_key"]
        )
        # Validate second response
        if not isinstance(response2, str) or not response2.strip():
            if logger:
                logger.error("Second interaction response is empty or not a string")
            raise AssertionError("Second interaction response is empty or not a string")
        if not isinstance(updated_history2, list) or not updated_history2 or not isinstance(updated_history2[-1], dict):
            if logger:
                logger.error("Updated history after second interaction is missing or malformed")
            raise AssertionError("Updated history after second interaction is missing or malformed")
        if 'role' not in updated_history2[-1] or 'content' not in updated_history2[-1] or not updated_history2[-1]['content']:
            if logger:
                logger.error("Updated history last entry after second interaction lacks required keys/content")
            raise AssertionError("Updated history last entry after second interaction lacks required keys/content")
        
        # Test bill
        response3, _, _, _, _ = process_order(
            user_input_text="What's my bill?",
            current_session_history=updated_history2,
            llm=llm,
            rag_index=rag_index,
            rag_documents=rag_documents, 
            api_key=api_keys["google_api_key"]
        )
        # Validate third response
        if not isinstance(response3, str) or not response3.strip():
            if logger:
                logger.error("Third interaction (bill) response is empty or not a string")
            raise AssertionError("Third interaction (bill) response is empty or not a string")
        
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
            
            # Clean up LLM client
            if llm is not None:
                try:
                    # Close LLM client if it has a close method
                    if hasattr(llm, 'close'):
                        llm.close()
                        if logger:
                            logger.info("✅ LLM client closed")
                except Exception as llm_cleanup_error:
                    if logger:
                        logger.error(f"Failed to close LLM client: {llm_cleanup_error}")
            
            # Clean up vector store/RAG index
            if rag_index is not None:
                try:
                    # Close vector store if it has cleanup methods
                    if hasattr(rag_index, 'close'):
                        rag_index.close()
                        if logger:
                            logger.info("✅ Vector store closed")
                    elif hasattr(rag_index, 'cleanup'):
                        rag_index.cleanup()
                        if logger:
                            logger.info("✅ Vector store cleaned up")
                except Exception as rag_cleanup_error:
                    if logger:
                        logger.error(f"Failed to cleanup vector store: {rag_cleanup_error}")
            
            # Clean up Cartesia client
            if cartesia_client is not None:
                try:
                    # Close Cartesia client if it has a close method
                    if hasattr(cartesia_client, 'close'):
                        cartesia_client.close()
                        if logger:
                            logger.info("✅ Cartesia client closed")
                    # Clean up any active connections or sessions
                    if hasattr(cartesia_client, 'cleanup'):
                        cartesia_client.cleanup()
                        if logger:
                            logger.info("✅ Cartesia client cleaned up")
                except Exception as cartesia_cleanup_error:
                    if logger:
                        logger.error(f"Failed to cleanup Cartesia client: {cartesia_cleanup_error}")
            
            # Reset state manager to clean state
            try:
                from src.utils.state_manager import reset_state, clear_session_data
                # Clear any session data that might be lingering
                if hasattr(sys.modules.get('src.utils.state_manager'), 'clear_session_data'):
                    clear_session_data()
                    if logger:
                        logger.info("✅ Session data cleared")
                
                # Reset state manager to initial state
                if hasattr(sys.modules.get('src.utils.state_manager'), 'reset_state'):
                    reset_state()
                    if logger:
                        logger.info("✅ State manager reset")
            except ImportError:
                # Functions don't exist, skip silently
                pass
            except Exception as state_cleanup_error:
                if logger:
                    logger.error(f"Failed to cleanup state manager: {state_cleanup_error}")
            
            # Clean up any temporary files that might have been created
            try:
                import tempfile
                temp_dir = Path(tempfile.gettempdir())
                # Look for any temporary files that might have been created by this test
                maya_temp_files = list(temp_dir.glob("maya_test_*"))
                for temp_file in maya_temp_files:
                    try:
                        if temp_file.is_file():
                            temp_file.unlink()
                        elif temp_file.is_dir():
                            import shutil
                            shutil.rmtree(temp_file)
                        if logger:
                            logger.info(f"✅ Removed temporary file/dir: {temp_file}")
                    except Exception as file_cleanup_error:
                        if logger:
                            logger.error(f"Failed to remove temporary file {temp_file}: {file_cleanup_error}")
            except Exception as temp_cleanup_error:
                if logger:
                    logger.error(f"Failed during temporary file cleanup: {temp_cleanup_error}")
            
            if logger:
                logger.info("✅ Cleanup completed")
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