#!/usr/bin/env python3
"""
Unit tests for src.rag.vector_store module.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock, Mock
import faiss

from src.rag.vector_store import (
    initialize_vector_store,
    search_similar_documents,
    DEFAULT_DOCUMENTS
)


class TestVectorStore:
    """Test cases for vector store functions."""

    def test_default_documents_exist(self):
        """Test that DEFAULT_DOCUMENTS is properly defined."""
        assert DEFAULT_DOCUMENTS is not None
        assert isinstance(DEFAULT_DOCUMENTS, list)
        assert len(DEFAULT_DOCUMENTS) > 0
        assert all(isinstance(doc, str) for doc in DEFAULT_DOCUMENTS)
        assert all(len(doc.strip()) > 0 for doc in DEFAULT_DOCUMENTS)

    @patch('src.rag.vector_store.get_embeddings_batch')
    @patch('src.rag.vector_store.faiss.IndexFlatL2')
    @patch('src.rag.vector_store.logger')
    def test_initialize_vector_store_with_default_documents(self, mock_logger, mock_index_class, mock_get_embeddings):
        """Test initialize_vector_store with default documents."""
        # Setup mocks
        mock_embeddings = [np.random.rand(128).tolist() for _ in DEFAULT_DOCUMENTS]
        mock_get_embeddings.return_value = mock_embeddings

        mock_index = MagicMock()
        mock_index.ntotal = len(DEFAULT_DOCUMENTS)
        mock_index_class.return_value = mock_index

        # Call function
        index, documents = initialize_vector_store()

        # Assertions
        mock_get_embeddings.assert_called_once_with(DEFAULT_DOCUMENTS, task_type="RETRIEVAL_DOCUMENT")
        mock_index_class.assert_called_once_with(128)
        mock_index.add.assert_called_once()

        assert index == mock_index
        assert documents == DEFAULT_DOCUMENTS
        mock_logger.info.assert_called()

    @patch('src.rag.vector_store.get_embeddings_batch')
    @patch('src.rag.vector_store.faiss.IndexFlatL2')
    @patch('src.rag.vector_store.logger')
    def test_initialize_vector_store_with_custom_documents(self, mock_logger, mock_index_class, mock_get_embeddings):
        """Test initialize_vector_store with custom documents."""
        custom_docs = ["Document 1", "Document 2", "Document 3"]
        mock_embeddings = [np.random.rand(256).tolist() for _ in custom_docs]
        mock_get_embeddings.return_value = mock_embeddings

        mock_index = MagicMock()
        mock_index.ntotal = len(custom_docs)
        mock_index_class.return_value = mock_index

        # Call function
        index, documents = initialize_vector_store(custom_docs)

        # Assertions
        mock_get_embeddings.assert_called_once_with(custom_docs, task_type="RETRIEVAL_DOCUMENT")
        mock_index_class.assert_called_once_with(256)
        mock_index.add.assert_called_once()

        assert index == mock_index
        assert documents == custom_docs

    @patch('src.rag.vector_store.get_embeddings_batch')
    @patch('src.rag.vector_store.logger')
    def test_initialize_vector_store_with_failed_embeddings(self, mock_logger, mock_get_embeddings):
        """Test initialize_vector_store when some embeddings fail."""
        custom_docs = ["Good doc", "Bad doc", "Another good doc"]
        # Second embedding fails (None)
        mock_embeddings = [
            np.random.rand(128).tolist(),
            None,
            np.random.rand(128).tolist()
        ]
        mock_get_embeddings.return_value = mock_embeddings

        with patch('src.rag.vector_store.faiss.IndexFlatL2') as mock_index_class:
            mock_index = MagicMock()
            mock_index.ntotal = 2
            mock_index_class.return_value = mock_index

            # Call function
            index, documents = initialize_vector_store(custom_docs)

            # Assertions
            assert len(documents) == 2  # Only valid documents
            assert documents == ["Good doc", "Another good doc"]
            mock_logger.warning.assert_called_once_with("Could not generate embedding for document 1")

    @patch('src.rag.vector_store.get_embeddings_batch')
    @patch('src.rag.vector_store.logger')
    def test_initialize_vector_store_no_valid_embeddings(self, mock_logger, mock_get_embeddings):
        """Test initialize_vector_store when no valid embeddings are generated."""
        custom_docs = ["Bad doc 1", "Bad doc 2"]
        mock_get_embeddings.return_value = [None, None]

        # Should raise ValueError
        with pytest.raises(ValueError, match="No valid embeddings generated"):
            initialize_vector_store(custom_docs)

    @patch('src.rag.vector_store.get_embeddings_batch')
    def test_initialize_vector_store_empty_documents(self, mock_get_embeddings):
        """Test initialize_vector_store with empty document list."""
        mock_get_embeddings.return_value = []

        with pytest.raises(ValueError, match="No valid embeddings generated"):
            initialize_vector_store([])

    @patch('src.rag.vector_store.get_embeddings_batch')
    @patch('src.rag.vector_store.faiss.IndexFlatL2')
    @patch('src.rag.vector_store.np.array')
    @patch('src.rag.vector_store.logger')
    def test_initialize_vector_store_embedding_array_conversion(self, mock_logger, mock_np_array, mock_index_class, mock_get_embeddings):
        """Test that embeddings are properly converted to numpy array."""
        custom_docs = ["Test doc"]
        mock_embedding = [0.1, 0.2, 0.3]
        mock_get_embeddings.return_value = [mock_embedding]

        mock_array = MagicMock()
        mock_array.astype.return_value = mock_array
        mock_np_array.return_value = mock_array

        mock_index = MagicMock()
        mock_index.ntotal = 1
        mock_index_class.return_value = mock_index

        # Call function
        initialize_vector_store(custom_docs)

        # Verify array conversion
        mock_np_array.assert_called_once_with([mock_embedding])
        mock_array.astype.assert_called_once_with('float32')
        mock_index.add.assert_called_once_with(mock_array)

    @patch('src.rag.embeddings.get_embedding')
    @patch('src.rag.vector_store.logger')
    def test_search_similar_documents_success(self, mock_logger, mock_get_embedding):
        """Test successful document search."""
        # Setup mock index
        mock_index = MagicMock()
        mock_index.search.return_value = (
            np.array([[0.1, 0.3]]),  # distances
            np.array([[0, 2]])       # indices
        )

        documents = ["Doc 0", "Doc 1", "Doc 2"]
        query_embedding = np.random.rand(128).tolist()
        mock_get_embedding.return_value = query_embedding

        # Call function
        result = search_similar_documents(mock_index, documents, "test query", n_results=2)

        # Assertions
        mock_get_embedding.assert_called_once_with("test query", task_type="RETRIEVAL_QUERY")
        mock_index.search.assert_called_once()

        # Check search was called with correct array
        call_args = mock_index.search.call_args[0]
        search_array = call_args[0]
        assert search_array.dtype == np.float32
        assert search_array.shape == (1, 128)

        assert result == ["Doc 0", "Doc 2"]

    @patch('src.rag.embeddings.get_embedding')
    @patch('src.rag.vector_store.logger')
    def test_search_similar_documents_query_embedding_fails(self, mock_logger, mock_get_embedding):
        """Test search when query embedding generation fails."""
        mock_index = MagicMock()
        documents = ["Doc 0", "Doc 1"]
        mock_get_embedding.return_value = None

        # Call function
        result = search_similar_documents(mock_index, documents, "test query")

        # Assertions
        mock_get_embedding.assert_called_once_with("test query", task_type="RETRIEVAL_QUERY")
        mock_logger.warning.assert_called_once_with("Could not generate embedding for query")
        mock_index.search.assert_not_called()
        assert result == []

    @patch('src.rag.embeddings.get_embedding')
    def test_search_similar_documents_default_n_results(self, mock_get_embedding):
        """Test search with default n_results parameter."""
        mock_index = MagicMock()
        mock_index.search.return_value = (
            np.array([[0.1]]),  # distances
            np.array([[0]])     # indices
        )

        documents = ["Doc 0", "Doc 1"]
        query_embedding = np.random.rand(64).tolist()
        mock_get_embedding.return_value = query_embedding

        # Call without n_results (should default to 1)
        result = search_similar_documents(mock_index, documents, "test query")

        # Check search was called with n_results=1
        call_args = mock_index.search.call_args[0]
        assert call_args[1] == 1  # n_results parameter
        assert result == ["Doc 0"]

    @patch('src.rag.embeddings.get_embedding')
    def test_search_similar_documents_index_out_of_bounds(self, mock_get_embedding):
        """Test search when index returns indices beyond document list."""
        mock_index = MagicMock()
        mock_index.search.return_value = (
            np.array([[0.1, 0.2]]),     # distances
            np.array([[0, 5]])          # indices (5 is out of bounds)
        )

        documents = ["Doc 0", "Doc 1", "Doc 2"]  # Only 3 documents
        query_embedding = np.random.rand(64).tolist()
        mock_get_embedding.return_value = query_embedding

        # Call function
        result = search_similar_documents(mock_index, documents, "test query", n_results=2)

        # Should only return valid indices
        assert result == ["Doc 0"]

    @patch('src.rag.embeddings.get_embedding')
    def test_search_similar_documents_empty_documents(self, mock_get_embedding):
        """Test search with empty document list."""
        mock_index = MagicMock()
        mock_index.search.return_value = (
            np.array([[0.1]]),  # distances
            np.array([[0]])     # indices
        )

        query_embedding = np.random.rand(64).tolist()
        mock_get_embedding.return_value = query_embedding

        # Call function with empty documents
        result = search_similar_documents(mock_index, [], "test query")

        # Should return empty list
        assert result == []

    @patch('src.rag.embeddings.get_embedding')
    def test_search_similar_documents_empty_query(self, mock_get_embedding):
        """Test search with empty query string."""
        mock_index = MagicMock()
        documents = ["Doc 0", "Doc 1"]

        # Empty query should still call get_embedding
        mock_get_embedding.return_value = None

        result = search_similar_documents(mock_index, documents, "")

        mock_get_embedding.assert_called_once_with("", task_type="RETRIEVAL_QUERY")
        assert result == []

    @patch('src.rag.embeddings.get_embedding')
    @patch('src.rag.vector_store.np.array')
    def test_search_similar_documents_array_conversion(self, mock_np_array, mock_get_embedding):
        """Test proper numpy array conversion in search."""
        mock_index = MagicMock()
        mock_index.search.return_value = (np.array([[0.1]]), np.array([[0]]))

        documents = ["Doc 0"]
        query_embedding = [0.1, 0.2, 0.3]
        mock_get_embedding.return_value = query_embedding

        mock_array = MagicMock()
        mock_array.astype.return_value = mock_array
        mock_np_array.return_value = mock_array

        # Call function
        search_similar_documents(mock_index, documents, "test query")

        # Verify array conversion - check that our query embedding was converted
        mock_np_array.assert_any_call([query_embedding])
        mock_array.astype.assert_called_with('float32')
        mock_index.search.assert_called_once_with(mock_array, 1)

    @patch('src.rag.embeddings.get_embedding')
    def test_search_similar_documents_large_n_results(self, mock_get_embedding):
        """Test search with n_results larger than available documents."""
        mock_index = MagicMock()
        mock_index.search.return_value = (
            np.array([[0.1, 0.2]]),  # distances
            np.array([[0, 1]])       # indices
        )

        documents = ["Doc 0", "Doc 1"]
        query_embedding = np.random.rand(64).tolist()
        mock_get_embedding.return_value = query_embedding

        # Request more results than available documents
        result = search_similar_documents(mock_index, documents, "test query", n_results=10)

        # Should return all available documents
        assert len(result) <= len(documents)
        assert result == ["Doc 0", "Doc 1"]

    def test_search_similar_documents_imports_get_embedding(self):
        """Test that search_similar_documents imports get_embedding correctly."""
        # This test ensures the relative import works
        from src.rag.vector_store import search_similar_documents

        # The function should be importable and callable
        assert callable(search_similar_documents)
