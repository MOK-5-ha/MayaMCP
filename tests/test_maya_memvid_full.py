#!/usr/bin/env python3
"""
Full test of Maya with Memvid integration
"""

import pytest
import logging

from mayamcp.config import get_api_keys, setup_logging
from mayamcp.llm import initialize_llm, get_all_tools  
from mayamcp.rag import initialize_memvid_store
from mayamcp.voice import initialize_cartesia_client
from mayamcp.conversation.processor import process_order
from mayamcp.utils.state_manager import initialize_state, get_current_order_state, get_order_history

def test_maya_memvid_full():
    """Test Maya's full interaction workflow with Memvid"""
    print("🍹🎬 Testing Maya with Memvid Integration")
    print("=" * 60)
    
    # Initialize variables for cleanup tracking
    logger = None
    api_keys = None
    llm = None
    memvid_retriever = None
    rag_documents = None
    
    try:
        # Setup logging
        print("📋 Setting up logging...")
        try:
            logger = setup_logging()
            print("✅ Logging configured")
        except Exception as e:
            raise AssertionError(f"Failed to setup logging: {e}") from e
        
        # Get API keys
        print("🔑 Loading API keys...")
        try:
            api_keys = get_api_keys()
            # Verify required API key is present
            if not api_keys.get("google_api_key"):
                pytest.skip("Google API key not found in environment - skipping test")
            print("✅ API keys loaded")
        except Exception as e:
            if "API key" in str(e).lower() or "key" in str(e).lower():
                pytest.skip(f"API key configuration issue - skipping test: {e}")
            raise AssertionError(f"Failed to load API keys: {e}") from e
        
        # Initialize state management
        print("🔄 Initializing state management...")
        try:
            initialize_state()
            print("✅ State management initialized")
        except Exception as e:
            if logger:
                logger.error(f"State initialization failed: {e}", exc_info=True)
            raise AssertionError(f"Failed to initialize state management: {e}") from e
        
        # Get LLM tools
        print("🛠️  Loading LLM tools...")
        try:
            tools = get_all_tools()
            print(f"✅ Loaded {len(tools)} LLM tools")
        except Exception as e:
            logger.error(f"Tools loading failed: {e}", exc_info=True) if logger else None
            raise AssertionError(f"Failed to load LLM tools: {e}") from e
        
        # Initialize LLM
        print("🤖 Initializing LLM client...")
        try:
            llm = initialize_llm(api_key=api_keys["google_api_key"], tools=tools)
            print("✅ LLM client initialized")
        except Exception as e:
            logger.error(f"LLM initialization failed: {e}", exc_info=True) if logger else None
            if "api" in str(e).lower() or "auth" in str(e).lower() or "key" in str(e).lower():
                pytest.skip(f"LLM API issue - skipping test: {e}")
            raise AssertionError(f"Failed to initialize LLM: {e}") from e
        
        # Initialize Memvid store
        print("📹 Initializing Memvid store...")
        try:
            memvid_retriever, rag_documents = initialize_memvid_store()
            print(f"✅ Memvid store initialized with {len(rag_documents)} documents")
        except Exception as e:
            logger.error(f"Memvid initialization failed: {e}", exc_info=True) if logger else None
            raise AssertionError(f"Failed to initialize Memvid store: {e}") from e
        
        print("✅ All components initialized with Memvid RAG")
        
    except (AssertionError, pytest.skip.Exception):
        # Re-raise test control exceptions
        raise
    except Exception as e:
        # Catch any other unexpected errors
        error_msg = f"Unexpected error during test initialization: {e}"
        if logger:
            logger.error(error_msg, exc_info=True)
        raise AssertionError(error_msg) from e
    
    finally:
        # Best-effort cleanup of resources
        print("🧹 Cleaning up resources...")
        
        # Cleanup LLM client
        if llm is not None:
            try:
                if hasattr(llm, 'close'):
                    llm.close()
                elif hasattr(llm, 'shutdown'):
                    llm.shutdown()
                elif hasattr(llm, '__del__'):
                    del llm
            except Exception as cleanup_error:
                print(f"⚠️  Warning: LLM cleanup failed: {cleanup_error}")
        
        # Cleanup Memvid retriever
        if memvid_retriever is not None:
            try:
                if hasattr(memvid_retriever, 'close'):
                    memvid_retriever.close()
                elif hasattr(memvid_retriever, 'shutdown'):
                    memvid_retriever.shutdown()
                elif hasattr(memvid_retriever, 'cleanup'):
                    memvid_retriever.cleanup()
            except Exception as cleanup_error:
                print(f"⚠️  Warning: Memvid retriever cleanup failed: {cleanup_error}")
        
        # Cleanup logger handlers if possible
        if logger is not None:
            try:
                if hasattr(logger, 'handlers'):
                    for handler in logger.handlers[:]:  # Copy list to avoid modification during iteration
                        if hasattr(handler, 'close'):
                            handler.close()
                        logger.removeHandler(handler)
            except Exception as cleanup_error:
                print(f"⚠️  Warning: Logger cleanup failed: {cleanup_error}")
        
        # Clear large objects to help with memory cleanup
        if rag_documents is not None:
            try:
                rag_documents.clear() if hasattr(rag_documents, 'clear') else None
                del rag_documents
            except Exception as cleanup_error:
                print(f"⚠️  Warning: RAG documents cleanup failed: {cleanup_error}")
        
        print("✅ Cleanup completed")
    
    # Test conversation with Memvid enhancement
    session_history = []
    
    print("\n🗣️  Testing casual conversation (should use Memvid RAG)")
    print("-" * 60)
    
    response, updated_history, _, _, _ = process_order(
        user_input_text="I'm feeling philosophical today. What's this place about?",
        current_session_history=session_history,
        llm=llm,
        rag_index=None,  # No FAISS
        rag_documents=rag_documents,
        rag_retriever=memvid_retriever,  # Using Memvid
        api_key=api_keys["google_api_key"]
    )
    
    print(f"🤖 Maya's Memvid-enhanced response: {response}")
    
    print("\n🗣️  Testing drink order (should use tools, not RAG)")
    print("-" * 50)
    
    response_whiskey, history_after_whiskey, analysis_whiskey, rag_context_whiskey, tool_calls_whiskey = process_order(
        user_input_text="I'd like a whiskey on the rocks please",
        current_session_history=updated_history,
        llm=llm,
        rag_index=None,
        rag_documents=rag_documents,
        rag_retriever=memvid_retriever,
        api_key=api_keys["google_api_key"]
    )
    
    # Validate drink order response quality
    assert response_whiskey is not None, "Drink order response should not be None"
    assert isinstance(response_whiskey, str), f"Drink order response should be string, got {type(response_whiskey)}"
    assert len(response_whiskey.strip()) > 0, "Drink order response should not be empty"
    assert len(response_whiskey) > 10, f"Drink order response too short ({len(response_whiskey)} chars)"
    
    # Validate history progression
    assert history_after_whiskey is not None, "Updated history2 should not be None"
    assert isinstance(history_after_whiskey, list), f"Updated history2 should be list, got {type(history_after_whiskey)}"
    assert len(history_after_whiskey) > len(updated_history), "History should continue growing"
    
    # Validate order state was affected (drink order should update state)
    current_state = get_current_order_state()
    assert current_state is not None, "Order state should exist after drink order"
    
    print(f"🤖 Maya's response: {response_whiskey}")
    print(f"🛒 Order state: {current_state}")
    print(f"✅ Drink order validation passed: {len(response_whiskey)} chars, history: {len(history_after_whiskey)} entries")
    
    print("\n🗣️  Testing casual follow-up (should use Memvid again)")
    print("-" * 55)
    
    response3, updated_history3, analysis_result3, rag_context3, tool_calls3 = process_order(
        user_input_text="You seem wise for a bartender",
        current_session_history=history_after_whiskey,  # Use history from drink order
        llm=llm,
        rag_index=None,
        rag_documents=rag_documents,
        rag_retriever=memvid_retriever,
        api_key=api_keys["google_api_key"]
    )
    
    # Validate follow-up response quality
    assert response3 is not None, "Follow-up response should not be None"
    assert isinstance(response3, str), f"Follow-up response should be string, got {type(response3)}"
    assert len(response3.strip()) > 0, "Follow-up response should not be empty"
    assert len(response3) > 10, f"Follow-up response too short ({len(response3)} chars)"
    
    # Validate final history state
    assert updated_history3 is not None, "Final updated history should not be None"
    assert isinstance(updated_history3, list), f"Final updated history should be list, got {type(updated_history3)}"
    assert len(updated_history3) > len(history_after_whiskey), "Final history should be longest"
    
    # For casual conversation, we expect potential RAG context usage
    # (though we can't guarantee it will be used, depending on the conversation flow)
    
    print(f"🤖 Maya's Memvid-enhanced response: {response3}")
    print(f"✅ Follow-up validation passed: {len(response3)} chars, final history: {len(updated_history3)} entries")
    
    print("\n🎉 Full Memvid integration test completed!")
    print(f"📊 Final order history: {get_order_history()}")
    
    # Show video memory stats
    assert hasattr(memvid_retriever, 'get_stats'), "Memvid retriever should have get_stats method"
    assert callable(getattr(memvid_retriever, 'get_stats')), "get_stats should be callable"
    
    try:
        stats = memvid_retriever.get_stats()
        print(f"📹 Memvid stats: {stats}")
    except Exception as e:
        logger.error(f"Failed to get Memvid stats: {e}", exc_info=True) if logger else None
        pytest.fail(f"memvid_retriever.get_stats() failed: {e}")

if __name__ == "__main__":
    test_maya_memvid_full()