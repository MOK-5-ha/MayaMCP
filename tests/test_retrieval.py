#!/usr/bin/env python3
"""
Unit tests for src.rag.retrieval module.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock

from src.rag.retrieval import retrieve_relevant_passages


class TestRetrieval:
    """Test cases for retrieval functions."""

    @patch('src.rag.retrieval.search_similar_documents')
    @patch('src.rag.retrieval.logger')
    def test_retrieve_relevant_passages_success(self, mock_logger, mock_search):
        """Test successful retrieval of relevant passages."""
        # Setup mocks
        mock_index = MagicMock()
        documents = ["Doc 1", "Doc 2", "Doc 3"]
        query_text = "test query"
        expected_results = ["Doc 1", "Doc 3"]
        mock_search.return_value = expected_results

        # Call function
        result = retrieve_relevant_passages(mock_index, documents, query_text, n_results=2)

        # Assertions
        mock_search.assert_called_once_with(
            index=mock_index,
            documents=documents,
            query_text=query_text,
            n_results=2
        )
        mock_logger.debug.assert_called()
        debug_call_args = mock_logger.debug.call_args[0][0]
        assert "Retrieved 2 documents" in debug_call_args
        assert "test query" in debug_call_args

        assert result == expected_results

    @patch('src.rag.retrieval.search_similar_documents')
    @patch('src.rag.retrieval.logger')
    def test_retrieve_relevant_passages_default_n_results(self, mock_logger, mock_search):
        """Test retrieval with default n_results parameter."""
        mock_index = MagicMock()
        documents = ["Doc 1", "Doc 2"]
        query_text = "test query"
        expected_results = ["Doc 1"]
        mock_search.return_value = expected_results

        # Call function without n_results (should default to 1)
        result = retrieve_relevant_passages(mock_index, documents, query_text)

        # Verify default n_results=1 is passed
        mock_search.assert_called_once_with(
            index=mock_index,
            documents=documents,
            query_text=query_text,
            n_results=1
        )
        assert result == expected_results

    @patch('src.rag.retrieval.search_similar_documents')
    @patch('src.rag.retrieval.logger')
    def test_retrieve_relevant_passages_empty_results(self, mock_logger, mock_search):
        """Test retrieval when no documents are found."""
        mock_index = MagicMock()
        documents = ["Doc 1", "Doc 2"]
        query_text = "nonexistent query"
        mock_search.return_value = []

        # Call function
        result = retrieve_relevant_passages(mock_index, documents, query_text)

        # Assertions
        mock_search.assert_called_once()
        mock_logger.debug.assert_called()
        debug_call_args = mock_logger.debug.call_args[0][0]
        assert "Retrieved 0 documents" in debug_call_args

        assert result == []

    @patch('src.rag.retrieval.search_similar_documents')
    @patch('src.rag.retrieval.logger')
    def test_retrieve_relevant_passages_exception_handling(self, mock_logger, mock_search):
        """Test retrieval when search_similar_documents raises exception."""
        mock_index = MagicMock()
        documents = ["Doc 1", "Doc 2"]
        query_text = "test query"

        # Mock search to raise exception
        mock_search.side_effect = ValueError("Search failed")

        # Call function
        result = retrieve_relevant_passages(mock_index, documents, query_text)

        # Assertions
        mock_search.assert_called_once_with(
            index=mock_index,
            documents=documents,
            query_text=query_text,
            n_results=1
        )
        mock_logger.error.assert_called_once()
        error_call_args = mock_logger.error.call_args[0][0]
        assert "Error in document retrieval" in error_call_args

        assert result == []

    @patch('src.rag.retrieval.search_similar_documents')
    @patch('src.rag.retrieval.logger')
    def test_retrieve_relevant_passages_different_exception_types(self, mock_logger, mock_search):
        """Test retrieval handles different exception types."""
        mock_index = MagicMock()
        documents = ["Doc 1"]
        query_text = "test query"

        # Test with different exception types
        exceptions_to_test = [
            RuntimeError("Runtime error"),
            ConnectionError("Connection failed"),
            KeyError("Key not found"),
            AttributeError("Attribute error")
        ]

        for exception in exceptions_to_test:
            mock_search.side_effect = exception
            mock_logger.reset_mock()

            result = retrieve_relevant_passages(mock_index, documents, query_text)

            assert result == []
            mock_logger.error.assert_called_once()

    @patch('src.rag.retrieval.search_similar_documents')
    @patch('src.rag.retrieval.logger')
    def test_retrieve_relevant_passages_empty_documents(self, mock_logger, mock_search):
        """Test retrieval with empty document list."""
        mock_index = MagicMock()
        documents = []
        query_text = "test query"
        mock_search.return_value = []

        # Call function
        result = retrieve_relevant_passages(mock_index, documents, query_text)

        # Should still call search_similar_documents
        mock_search.assert_called_once_with(
            index=mock_index,
            documents=documents,
            query_text=query_text,
            n_results=1
        )
        assert result == []

    @patch('src.rag.retrieval.search_similar_documents')
    @patch('src.rag.retrieval.logger')
    def test_retrieve_relevant_passages_empty_query(self, mock_logger, mock_search):
        """Test retrieval with empty query string."""
        mock_index = MagicMock()
        documents = ["Doc 1", "Doc 2"]
        query_text = ""
        mock_search.return_value = []

        # Call function
        result = retrieve_relevant_passages(mock_index, documents, query_text)

        # Should still call search_similar_documents
        mock_search.assert_called_once_with(
            index=mock_index,
            documents=documents,
            query_text=query_text,
            n_results=1
        )
        assert result == []

    @patch('src.rag.retrieval.search_similar_documents')
    @patch('src.rag.retrieval.logger')
    def test_retrieve_relevant_passages_with_none_index(self, mock_logger, mock_search):
        """Test retrieval behavior with None index."""
        mock_search.side_effect = AttributeError("NoneType has no attribute")
        
        result = retrieve_relevant_passages(None, ["Doc 1"], "query")
        
        assert result == []
        mock_logger.error.assert_called_once()
        
    @patch('src.rag.retrieval.search_similar_documents')
    @patch('src.rag.retrieval.logger')
    def test_retrieve_relevant_passages_with_none_documents(self, mock_logger, mock_search):
        """Test retrieval behavior with None documents."""
        mock_search.side_effect = ValueError("Documents cannot be None")
        
        # Pass mock index but None documents
        result = retrieve_relevant_passages(MagicMock(), None, "query")
        
        assert result == []
        mock_logger.error.assert_called_once()
        
    @patch('src.rag.retrieval.search_similar_documents')
    @patch('src.rag.retrieval.logger')
    def test_retrieve_relevant_passages_with_none_query(self, mock_logger, mock_search):
        """Test retrieval behavior with None query."""
        mock_search.side_effect = ValueError("Query cannot be None")
        
        # Pass mock index but None query
        result = retrieve_relevant_passages(MagicMock(), ["Doc 1"], None)
        
        assert result == []
        mock_logger.error.assert_called_once()

    @patch('src.rag.retrieval.search_similar_documents')
    @patch('src.rag.retrieval.logger')
    def test_retrieve_relevant_passages_large_n_results(self, mock_logger, mock_search):
        """Test retrieval with large n_results value."""
        mock_index = MagicMock()
        documents = ["Doc 1", "Doc 2"]
        query_text = "test query"
        n_results = 100
        expected_results = ["Doc 1", "Doc 2"]
        mock_search.return_value = expected_results

        # Call function with large n_results
        result = retrieve_relevant_passages(mock_index, documents, query_text, n_results=n_results)

        # Verify n_results is passed correctly
        mock_search.assert_called_once_with(
            index=mock_index,
            documents=documents,
            query_text=query_text,
            n_results=n_results
        )
        assert result == expected_results

    @patch('src.rag.retrieval.search_similar_documents')
    @patch('src.rag.retrieval.logger')
    def test_retrieve_relevant_passages_zero_n_results(self, mock_logger, mock_search):
        """Test retrieval with n_results=0."""
        mock_index = MagicMock()
        documents = ["Doc 1", "Doc 2"]
        query_text = "test query"
        mock_search.return_value = []

        # Call function with n_results=0
        result = retrieve_relevant_passages(mock_index, documents, query_text, n_results=0)

        # Verify n_results=0 is passed
        mock_search.assert_called_once_with(
            index=mock_index,
            documents=documents,
            query_text=query_text,
            n_results=0
        )
        assert result == []

    @patch('src.rag.retrieval.search_similar_documents')
    @patch('src.rag.retrieval.logger')
    def test_retrieve_relevant_passages_long_query_logging(self, mock_logger, mock_search):
        """Test that long queries are truncated in logging."""
        mock_index = MagicMock()
        documents = ["Doc 1"]
        # Create a long query string
        long_query = "This is a very long query string that should be truncated in the log message " * 5
        mock_search.return_value = ["Doc 1"]

        # Call function
        retrieve_relevant_passages(mock_index, documents, long_query)

        # Check that debug logging was called
        mock_logger.debug.assert_called_once()
        debug_call_args = mock_logger.debug.call_args[0][0]

        # Query should be truncated to 50 characters plus "..."
        assert "Retrieved 1 documents for query:" in debug_call_args
        # The logged query should be truncated (not the full long query)
        assert len(debug_call_args) < len(long_query)
        assert "..." in debug_call_args or len(debug_call_args) < len(f"Retrieved 1 documents for query: {long_query}")

    @patch('src.rag.retrieval.search_similar_documents')
    @patch('src.rag.retrieval.logger')
    def test_retrieve_relevant_passages_special_characters_in_query(self, mock_logger, mock_search):
        """Test retrieval with special characters in query."""
        mock_index = MagicMock()
        documents = ["Doc 1", "Doc 2"]
        query_text = "test query with $pecial ch@rs & símb0ls!"
        expected_results = ["Doc 1"]
        mock_search.return_value = expected_results

        # Call function
        result = retrieve_relevant_passages(mock_index, documents, query_text)

        # Should handle special characters without issues
        mock_search.assert_called_once_with(
            index=mock_index,
            documents=documents,
            query_text=query_text,
            n_results=1
        )
        assert result == expected_results

    @patch('src.rag.retrieval.search_similar_documents')
    @patch('src.rag.retrieval.logger')
    def test_retrieve_relevant_passages_unicode_query(self, mock_logger, mock_search):
        """Test retrieval with unicode characters in query."""
        mock_index = MagicMock()
        documents = ["Document with émojis 🔍", "Another doc"]
        query_text = "search with ünicöde and émojis 🎯"
        expected_results = ["Document with émojis 🔍"]
        mock_search.return_value = expected_results

        # Call function
        result = retrieve_relevant_passages(mock_index, documents, query_text)

        # Should handle unicode without issues
        mock_search.assert_called_once()
        assert result == expected_results

    @patch('src.rag.retrieval.search_similar_documents')
    @patch('src.rag.retrieval.logger')
    def test_retrieve_relevant_passages_arguments_passed_correctly(self, mock_logger, mock_search):
        """Test that arguments are correctly propagated to search function."""
        mock_index = MagicMock()
        documents = ["Doc 1"]
        query_text = "test"
        n_results = 5
        mock_search.return_value = []

        # Call function
        retrieve_relevant_passages(mock_index, documents, query_text, n_results)

        # Verify arguments were passed correctly (handling both positional and keyword args)
        mock_search.assert_called_once()
        args, kwargs = mock_search.call_args
        
        # Check index (arg 0 or kwarg 'index')
        actual_index = kwargs.get('index') if 'index' in kwargs else (args[0] if len(args) > 0 else None)
        assert actual_index == mock_index, "Index argument mismatch"
        
        # Check documents (arg 1 or kwarg 'documents')
        actual_docs = kwargs.get('documents') if 'documents' in kwargs else (args[1] if len(args) > 1 else None)
        assert actual_docs == documents, "Documents argument mismatch"
        
        # Check query_text (arg 2 or kwarg 'query_text')
        actual_query = kwargs.get('query_text') if 'query_text' in kwargs else (args[2] if len(args) > 2 else None)
        assert actual_query == query_text, "Query text argument mismatch"
        
        # Check n_results (arg 3 or kwarg 'n_results')
        actual_n = kwargs.get('n_results') if 'n_results' in kwargs else (args[3] if len(args) > 3 else None)
        assert actual_n == n_results, "n_results argument mismatch"

    def test_retrieve_relevant_passages_function_signature(self):
        """Test that function has correct signature and is importable."""
        from src.rag.retrieval import retrieve_relevant_passages
        import inspect

        # Check function exists and is callable
        assert callable(retrieve_relevant_passages)

        # Check function signature
        sig = inspect.signature(retrieve_relevant_passages)
        params = list(sig.parameters.keys())

        # Should have 4 parameters: index, documents, query_text, n_results
        assert len(params) == 4
        assert 'index' in params
        assert 'documents' in params
        assert 'query_text' in params
        assert 'n_results' in params

        # Check default value for n_results
        assert sig.parameters['n_results'].default == 1
