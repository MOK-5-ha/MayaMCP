#!/usr/bin/env python3
"""
Full test of Maya with Memvid integration
"""

import sys
import os
sys.path.insert(0, 'src')

from src.config import get_api_keys, setup_logging
from src.llm import initialize_llm, get_all_tools  
from src.rag import initialize_memvid_store
from src.voice import initialize_cartesia_client
from src.conversation.processor import process_order
from src.utils.state_manager import initialize_state, get_current_order_state, get_order_history

def test_maya_memvid_full():
    """Test Maya's full interaction workflow with Memvid"""
    print("🍹🎬 Testing Maya with Memvid Integration")
    print("=" * 60)
    
    # Setup
    logger = setup_logging()
    api_keys = get_api_keys()
    
    # Initialize components
    print("📋 Initializing Maya with Memvid...")
    initialize_state()
    tools = get_all_tools()
    llm = initialize_llm(api_key=api_keys["google_api_key"], tools=tools)
    memvid_retriever, rag_documents = initialize_memvid_store()
    
    print("✅ All components initialized with Memvid RAG")
    
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
    
    response2, _, _, _, _ = process_order(
        user_input_text="I'd like a whiskey on the rocks please",
        current_session_history=updated_history,
        llm=llm,
        rag_index=None,
        rag_documents=rag_documents,
        rag_retriever=memvid_retriever,
        api_key=api_keys["google_api_key"]
    )
    
    print(f"🤖 Maya's response: {response2}")
    print(f"🛒 Order state: {get_current_order_state()}")
    
    print("\n🗣️  Testing casual follow-up (should use Memvid again)")
    print("-" * 55)
    
    response3, _, _, _, _ = process_order(
        user_input_text="You seem wise for a bartender",
        current_session_history=updated_history,
        llm=llm,
        rag_index=None,
        rag_documents=rag_documents,
        rag_retriever=memvid_retriever,
        api_key=api_keys["google_api_key"]
    )
    
    print(f"🤖 Maya's Memvid-enhanced response: {response3}")
    
    print("\n🎉 Full Memvid integration test completed!")
    print(f"📊 Final order history: {get_order_history()}")
    
    # Show video memory stats
    print(f"📹 Memvid stats: {memvid_retriever.get_stats()}")

if __name__ == "__main__":
    test_maya_memvid_full()