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
            logger.error(f"State initialization failed: {e}", exc_info=True) if logger else None
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
        # Cleanup resources if needed
        # Note: Most components don't require explicit cleanup, but this is where
        # you would add it if needed (e.g., closing connections, files, etc.)
        pass
    
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
    
    response2, updated_history2, analysis_result2, rag_context2, tool_calls2 = process_order(
        user_input_text="I'd like a whiskey on the rocks please",
        current_session_history=updated_history,
        llm=llm,
        rag_index=None,
        rag_documents=rag_documents,
        rag_retriever=memvid_retriever,
        api_key=api_keys["google_api_key"]
    )
    
    # Validate drink order response quality
    assert response2 is not None, "Drink order response should not be None"
    assert isinstance(response2, str), f"Drink order response should be string, got {type(response2)}"
    assert len(response2.strip()) > 0, "Drink order response should not be empty"
    assert len(response2) > 10, f"Drink order response too short ({len(response2)} chars)"
    
    # Validate history progression
    assert updated_history2 is not None, "Updated history2 should not be None"
    assert isinstance(updated_history2, list), f"Updated history2 should be list, got {type(updated_history2)}"
    assert len(updated_history2) > len(updated_history), "History should continue growing"
    
    # Validate order state was affected (drink order should update state)
    current_state = get_current_order_state()
    assert current_state is not None, "Order state should exist after drink order"
    
    print(f"🤖 Maya's response: {response2}")
    print(f"🛒 Order state: {current_state}")
    print(f"✅ Drink order validation passed: {len(response2)} chars, history: {len(updated_history2)} entries")
    
    print("\n🗣️  Testing casual follow-up (should use Memvid again)")
    print("-" * 55)
    
    response3, updated_history3, analysis_result3, rag_context3, tool_calls3 = process_order(
        user_input_text="You seem wise for a bartender",
        current_session_history=updated_history2,  # Use history from drink order
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
    assert len(updated_history3) > len(updated_history2), "Final history should be longest"
    
    # For casual conversation, we expect potential RAG context usage
    # (though we can't guarantee it will be used, depending on the conversation flow)
    
    print(f"🤖 Maya's Memvid-enhanced response: {response3}")
    print(f"✅ Follow-up validation passed: {len(response3)} chars, final history: {len(updated_history3)} entries")
    
    print("\n🎉 Full Memvid integration test completed!")
    print(f"📊 Final order history: {get_order_history()}")
    
    # Show video memory stats
    print(f"📹 Memvid stats: {memvid_retriever.get_stats()}")

if __name__ == "__main__":
    test_maya_memvid_full()