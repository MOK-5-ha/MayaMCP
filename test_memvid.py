#!/usr/bin/env python3
"""
Test script to verify Memvid integration works
"""

import sys
import os
sys.path.insert(0, 'src')

from src.config import setup_logging, get_api_keys
from src.rag.memvid_store import initialize_memvid_store, search_memvid_documents
from src.rag.memvid_pipeline import memvid_rag_pipeline

def test_memvid_integration():
    """Test Memvid integration"""
    print("🎬 Testing Memvid Integration for Maya")
    print("=" * 50)
    
    # Setup
    logger = setup_logging()
    api_keys = get_api_keys()
    
    print("📋 Testing Memvid store initialization...")
    try:
        # Initialize Memvid store
        memvid_retriever, documents = initialize_memvid_store(force_rebuild=True)
        print(f"✅ Memvid store initialized with {len(documents)} documents")
        
        # Print retriever stats
        stats = memvid_retriever.get_stats()
        print(f"📊 Stats: {stats}")
        
    except Exception as e:
        print(f"❌ Memvid initialization failed: {e}")
        return
    
    print("\n🔍 Testing document retrieval...")
    try:
        # Test search
        query = "What about difficult customers?"
        results = search_memvid_documents(memvid_retriever, query, n_results=2)
        print(f"Query: '{query}'")
        print(f"Retrieved {len(results)} documents:")
        for i, doc in enumerate(results):
            print(f"  {i+1}. {doc[:100]}{'...' if len(doc) > 100 else ''}")
            
    except Exception as e:
        print(f"❌ Document retrieval failed: {e}")
        return
    
    print("\n🤖 Testing full Memvid RAG pipeline...")
    try:
        # Test full pipeline
        query = "I'm having a rough day"
        response = memvid_rag_pipeline(
            query_text=query,
            memvid_retriever=memvid_retriever,
            api_key=api_keys["google_api_key"]
        )
        print(f"Query: '{query}'")
        print(f"Maya's Memvid-enhanced response: {response}")
        
    except Exception as e:
        print(f"❌ RAG pipeline failed: {e}")
        return
    
    print("\n🎉 Memvid integration test completed successfully!")

if __name__ == "__main__":
    test_memvid_integration()