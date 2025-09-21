#!/usr/bin/env python3
"""
Test script to verify Memvid integration works

Environment variables:
- TEST_FORCE_REBUILD=1: Force expensive Memvid store rebuilds (default: 0 for CI efficiency)

Command-line options:
- pytest --force-rebuild: Force expensive Memvid store rebuilds
"""

import os
import pytest
from src.config import setup_logging, get_api_keys
from src.rag.memvid_store import initialize_memvid_store, search_memvid_documents
from src.rag.memvid_pipeline import memvid_rag_pipeline
from tests.test_config import (
    DIFFICULT_CUSTOMERS_QUERY,
    ROUGH_DAY_QUERY,
    memvid_queries
)

def test_memvid_integration(force_rebuild_flag):
    """
    Test Memvid integration with configurable rebuild behavior.
    
    Uses force_rebuild_flag fixture to determine whether to force expensive rebuilds:
    - CI/default: force_rebuild=False (faster, uses cached data)  
    - Development: TEST_FORCE_REBUILD=1 or --force-rebuild (ensures fresh data)
    """
    
    # Setup
    logger = setup_logging()
    api_keys = get_api_keys()
    
    # Initialize Memvid store with configurable rebuild flag
    # This will be False by default (for CI efficiency) unless overridden
    memvid_retriever, documents = initialize_memvid_store(force_rebuild=force_rebuild_flag)
    assert len(documents) > 0, "Should have documents in store"
    
    # Test search
    query = "What about difficult customers?"
    results = search_memvid_documents(memvid_retriever, query, n_results=2)
    assert len(results) > 0, f"Should retrieve documents for query: {query}"
    
    # Test full pipeline
    query = "I'm having a rough day"
    response = memvid_rag_pipeline(
        query_text=query,
        memvid_retriever=memvid_retriever,
        api_key=api_keys["google_api_key"]
    )
    assert response and len(response.strip()) > 0, "Should generate non-empty response"
    print(f"Query: '{query}'")
    print(f"Maya's Memvid-enhanced response: {response}")
    print("\n🎉 Memvid integration test completed successfully!")


def test_memvid_queries(force_rebuild_flag):
    """Test multiple Memvid queries from test_config."""
    # Setup
    logger = setup_logging()
    api_keys = get_api_keys()
    failures = []
    
    try:
        # Initialize Memvid store with configurable rebuild flag
        memvid_retriever, documents = initialize_memvid_store(force_rebuild=force_rebuild_flag)
        
        if memvid_retriever and len(documents) > 0:
            # Test with predefined queries
            test_queries = [DIFFICULT_CUSTOMERS_QUERY, ROUGH_DAY_QUERY] + memvid_queries
            
            for query in test_queries:
                try:
                    response = memvid_rag_pipeline(
                        query_text=query,
                        memvid_retriever=memvid_retriever,
                        api_key=api_keys["google_api_key"]
                    )
                    print(f"Query: '{query}'")
                    print(f"Maya's Memvid-enhanced response: {response}")
                except Exception as e:
                    error_msg = f"Query failed '{query}': {e}"
                    print(f"❌ {error_msg}")
                    failures.append(error_msg)
        else:
            error_msg = "RAG pipeline skipped: memvid_retriever not initialized"
            print(f"⚠️ {error_msg}")
            failures.append(error_msg)
            
    except Exception as e:
        error_msg = f"RAG pipeline failed: {e}"
        print(f"❌ {error_msg}")
        failures.append(error_msg)
    
    # Check for failures and report them
    if failures:
        failure_summary = "\n".join(f"  - {failure}" for failure in failures)
        print(f"\n❌ Test completed with {len(failures)} failure(s):")
        print(failure_summary)
        raise AssertionError(f"Memvid integration test failed with {len(failures)} error(s):\n{failure_summary}")
    else:
        print("\n🎉 Memvid queries test completed successfully!")


if __name__ == "__main__":
    # For standalone execution, we need to manually determine force_rebuild
    import os
    force_rebuild = os.getenv("TEST_FORCE_REBUILD", "0") == "1"
    test_memvid_integration(force_rebuild)
    test_memvid_queries(force_rebuild)