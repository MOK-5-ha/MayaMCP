"""Unit tests for RAG embeddings."""

from types import SimpleNamespace as NS
from unittest.mock import MagicMock, patch

from src.rag.embeddings import DEFAULT_TASK_TYPE, EMBEDDING_MODEL, get_embedding, get_embeddings_batch


def _make_mock_client(embed_return=None, embed_side_effect=None):
    """Helper to create a mock genai client."""
    client = MagicMock()
    if embed_side_effect is not None:
        client.models.embed_content.side_effect = embed_side_effect
    elif embed_return is not None:
        client.models.embed_content.return_value = embed_return
    return client


class TestGetEmbedding:
    """Test cases for get_embedding function."""

    def test_get_embedding_successful(self, monkeypatch):
        """Test successful embedding generation."""
        mock_response = NS(embeddings=[NS(values=[0.1, 0.2, 0.3, 0.4, 0.5])])
        client = _make_mock_client(embed_return=mock_response)
        monkeypatch.setattr('src.rag.embeddings._get_embed_client', lambda: client)

        result = get_embedding("test text")

        # Verify embed_content was called
        client.models.embed_content.assert_called_once()
        call_kwargs = client.models.embed_content.call_args
        assert call_kwargs[1]['model'] == EMBEDDING_MODEL
        assert call_kwargs[1]['contents'] == "test text"
        # Default task_type should produce a config with DEFAULT_TASK_TYPE
        assert call_kwargs[1]['config'].task_type == DEFAULT_TASK_TYPE

        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]

    def test_get_embedding_no_api_key(self, monkeypatch):
        """Test embedding generation when no API key is available."""
        monkeypatch.setattr('src.rag.embeddings._get_embed_client', lambda: None)

        result = get_embedding("test text")
        assert result is None

    def test_get_embedding_with_list_response(self, monkeypatch):
        """Test embedding generation with list in embeddings."""
        mock_response = NS(embeddings=[[0.1, 0.2, 0.3]])
        client = _make_mock_client(embed_return=mock_response)
        monkeypatch.setattr('src.rag.embeddings._get_embed_client', lambda: client)

        result = get_embedding("test text")
        assert result == [0.1, 0.2, 0.3]

    def test_get_embedding_unexpected_response_structure(self, monkeypatch):
        """Test embedding generation with unexpected response structure."""
        mock_response = NS(some_other_field="unexpected")
        client = _make_mock_client(embed_return=mock_response)
        monkeypatch.setattr('src.rag.embeddings._get_embed_client', lambda: client)

        result = get_embedding("test text")
        assert result is None

    def test_get_embedding_exception_handling(self, monkeypatch):
        """Test embedding generation with exception handling."""
        client = _make_mock_client(embed_side_effect=Exception("API Error"))
        monkeypatch.setattr('src.rag.embeddings._get_embed_client', lambda: client)

        result = get_embedding("test text")
        assert result is None

    def test_get_embedding_with_different_task_type(self, monkeypatch):
        """Test embedding generation with different task type."""
        mock_response = NS(embeddings=[NS(values=[0.1, 0.2, 0.3])])
        client = _make_mock_client(embed_return=mock_response)
        monkeypatch.setattr('src.rag.embeddings._get_embed_client', lambda: client)

        result = get_embedding("test text", "CLASSIFICATION")

        # Verify embed_content was called with a config for task_type
        call_kwargs = client.models.embed_content.call_args
        assert call_kwargs[1]['model'] == EMBEDDING_MODEL
        assert call_kwargs[1]['contents'] == "test text"
        config = call_kwargs[1]['config']
        assert config is not None
        assert config.task_type == "CLASSIFICATION"

        assert result == [0.1, 0.2, 0.3]


class TestGetEmbeddingsBatch:
    """Test cases for get_embeddings_batch function."""

    def test_get_embeddings_batch_successful(self, monkeypatch):
        """Test successful batch embedding generation."""
        mock_response = NS(embeddings=[
            NS(values=[0.1, 0.2]),
            NS(values=[0.3, 0.4]),
            NS(values=[0.5, 0.6])
        ])
        client = _make_mock_client(embed_return=mock_response)
        monkeypatch.setattr('src.rag.embeddings._get_embed_client', lambda: client)

        texts = ["text1", "text2", "text3"]
        result = get_embeddings_batch(texts)

        client.models.embed_content.assert_called_once()
        call_kwargs = client.models.embed_content.call_args
        assert call_kwargs[1]['model'] == EMBEDDING_MODEL
        assert call_kwargs[1]['contents'] == ["text1", "text2", "text3"]
        assert call_kwargs[1]['config'].task_type == DEFAULT_TASK_TYPE

        expected = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        assert result == expected

    def test_get_embeddings_batch_no_api_key(self, monkeypatch):
        """Test batch embedding generation when no API key is available."""
        monkeypatch.setattr('src.rag.embeddings._get_embed_client', lambda: None)

        texts = ["text1", "text2"]
        result = get_embeddings_batch(texts)
        assert result == [None, None]

    def test_get_embeddings_batch_with_list_response(self, monkeypatch):
        """Test batch embedding with plain list response format."""
        # This tests the case where embeddings are returned as plain lists
        # instead of objects with .values attribute
        mock_response = NS(embeddings=[
            [0.1, 0.2],
            [0.3, 0.4]
        ])
        client = _make_mock_client(embed_return=mock_response)
        monkeypatch.setattr('src.rag.embeddings._get_embed_client', lambda: client)

        texts = ["text1", "text2"]
        result = get_embeddings_batch(texts)
        assert result == [[0.1, 0.2], [0.3, 0.4]]

    def test_get_embeddings_batch_mismatch_length(self, monkeypatch):
        """Test batch embedding when response length doesn't match input."""
        mock_response = NS(embeddings=[
            NS(values=[0.1, 0.2]),
            NS(values=[0.3, 0.4])
        ])
        client = _make_mock_client(embed_return=mock_response)
        monkeypatch.setattr('src.rag.embeddings._get_embed_client', lambda: client)

        # Execute function with 3 texts but only 2 embeddings returned
        texts = ["text1", "text2", "text3"]
        result = get_embeddings_batch(texts)

        # Verify padding with None for missing embeddings
        expected = [[0.1, 0.2], [0.3, 0.4], None]
        assert result == expected

    def test_get_embeddings_batch_exception_handling(self, monkeypatch):
        """Test batch embedding with exception handling."""
        client = _make_mock_client(embed_side_effect=Exception("Batch API Error"))
        monkeypatch.setattr('src.rag.embeddings._get_embed_client', lambda: client)

        texts = ["text1", "text2"]
        result = get_embeddings_batch(texts)
        assert result == [None, None]

    def test_get_embeddings_batch_empty_input(self, monkeypatch):
        """Test batch embedding with empty input list.

        Verifies that the API client is not invoked when input is empty.
        """
        mock_client = MagicMock()
        monkeypatch.setattr(
            'src.rag.embeddings._get_embed_client',
            mock_client
        )

        result = get_embeddings_batch([])
        assert result == []
        mock_client.assert_not_called()

    def test_get_embeddings_batch_with_different_task_type(self, monkeypatch):
        """Test batch embedding with different task type."""
        mock_response = NS(embeddings=[NS(values=[0.1, 0.2])])
        client = _make_mock_client(embed_return=mock_response)
        monkeypatch.setattr('src.rag.embeddings._get_embed_client', lambda: client)

        texts = ["text1"]
        result = get_embeddings_batch(texts, "CLASSIFICATION")

        client.models.embed_content.assert_called_once()
        call_kwargs = client.models.embed_content.call_args
        assert call_kwargs[1]['model'] == EMBEDDING_MODEL
        assert call_kwargs[1]['contents'] == ["text1"]
        config = call_kwargs[1]['config']
        assert config is not None
        assert config.task_type == "CLASSIFICATION"

        assert result == [[0.1, 0.2]]

    def test_get_embeddings_batch_chunking(self, monkeypatch):
        """Test batch embedding with chunking for large inputs."""
        mock_response1 = NS(embeddings=[
            NS(values=[0.1, 0.2]),
            NS(values=[0.3, 0.4])
        ])
        mock_response2 = NS(embeddings=[
            NS(values=[0.5, 0.6])
        ])
        client = _make_mock_client(embed_side_effect=[mock_response1, mock_response2])
        monkeypatch.setattr('src.rag.embeddings._get_embed_client', lambda: client)

        with patch('src.rag.embeddings.BATCH_SIZE', 2):
            texts = ["text1", "text2", "text3"]
            result = get_embeddings_batch(texts)

            assert client.models.embed_content.call_count == 2

            expected = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
            assert result == expected
