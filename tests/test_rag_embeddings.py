"""Unit tests for RAG embeddings."""

from unittest.mock import Mock, patch, MagicMock
import pytest
from src.rag.embeddings import get_embedding, get_embeddings_batch


class TestGetEmbedding:
    """Test cases for get_embedding function."""

    @patch('src.rag.embeddings.get_google_api_key')
    @patch('src.rag.embeddings.genai.configure')
    @patch('src.rag.embeddings.genai.embed_content')
    def test_get_embedding_successful(self, mock_embed_content, mock_configure, mock_get_api_key):
        """Test successful embedding generation."""
        # Setup mocks
        mock_get_api_key.return_value = "test_api_key"
        
        mock_response = Mock()
        mock_response.embedding.values = [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_embed_content.return_value = mock_response

        # Execute function
        result = get_embedding("test text", "RETRIEVAL_DOCUMENT")

        # Verify API key was retrieved
        mock_get_api_key.assert_called_once()

        # Verify genai was configured
        mock_configure.assert_called_once_with(api_key="test_api_key")

        # Verify embed_content was called with correct parameters
        mock_embed_content.assert_called_once_with(
            model="text-embedding-004",
            content="test text",
            task_type="RETRIEVAL_DOCUMENT"
        )

        # Verify return value
        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]

    @patch('src.rag.embeddings.get_google_api_key')
    def test_get_embedding_no_api_key(self, mock_get_api_key):
        """Test embedding generation when no API key is available."""
        # Setup mocks
        mock_get_api_key.return_value = None

        # Execute function
        result = get_embedding("test text")

        # Verify API key was checked
        mock_get_api_key.assert_called_once()

        # Verify None was returned
        assert result is None

    @patch('src.rag.embeddings.get_google_api_key')
    @patch('src.rag.embeddings.genai.configure')
    @patch('src.rag.embeddings.genai.embed_content')
    def test_get_embedding_with_dict_response(self, mock_embed_content, mock_configure, mock_get_api_key):
        """Test embedding generation with dict response format."""
        # Setup mocks
        mock_get_api_key.return_value = "test_api_key"
        
        mock_response = {"embedding": {"values": [0.1, 0.2, 0.3]}}
        mock_embed_content.return_value = mock_response

        # Execute function
        result = get_embedding("test text")

        # Verify return value
        assert result == [0.1, 0.2, 0.3]

    @patch('src.rag.embeddings.get_google_api_key')
    @patch('src.rag.embeddings.genai.configure')
    @patch('src.rag.embeddings.genai.embed_content')
    def test_get_embedding_with_list_response(self, mock_embed_content, mock_configure, mock_get_api_key):
        """Test embedding generation with list response format."""
        # Setup mocks
        mock_get_api_key.return_value = "test_api_key"
        
        mock_response = {"embedding": [0.1, 0.2, 0.3]}
        mock_embed_content.return_value = mock_response

        # Execute function
        result = get_embedding("test text")

        # Verify return value
        assert result == [0.1, 0.2, 0.3]

    @patch('src.rag.embeddings.get_google_api_key')
    @patch('src.rag.embeddings.genai.configure')
    @patch('src.rag.embeddings.genai.embed_content')
    def test_get_embedding_unexpected_response_structure(self, mock_embed_content, mock_configure, mock_get_api_key):
        """Test embedding generation with unexpected response structure."""
        # Setup mocks
        mock_get_api_key.return_value = "test_api_key"
        
        mock_response = Mock()
        mock_response.some_other_field = "unexpected"
        mock_embed_content.return_value = mock_response

        # Execute function
        result = get_embedding("test text")

        # Verify None was returned for unexpected structure
        assert result is None

    @patch('src.rag.embeddings.get_google_api_key')
    @patch('src.rag.embeddings.genai.configure')
    @patch('src.rag.embeddings.genai.embed_content')
    def test_get_embedding_exception_handling(self, mock_embed_content, mock_configure, mock_get_api_key):
        """Test embedding generation with exception handling."""
        # Setup mocks
        mock_get_api_key.return_value = "test_api_key"
        mock_embed_content.side_effect = Exception("API Error")

        # Execute function
        result = get_embedding("test text")

        # Verify None was returned on exception
        assert result is None

    @patch('src.rag.embeddings.get_google_api_key')
    @patch('src.rag.embeddings.genai.configure')
    @patch('src.rag.embeddings.genai.embed_content')
    def test_get_embedding_with_different_task_type(self, mock_embed_content, mock_configure, mock_get_api_key):
        """Test embedding generation with different task type."""
        # Setup mocks
        mock_get_api_key.return_value = "test_api_key"
        
        mock_response = Mock()
        mock_response.embedding.values = [0.1, 0.2, 0.3]
        mock_embed_content.return_value = mock_response

        # Execute function with different task type
        result = get_embedding("test text", "CLASSIFICATION")

        # Verify embed_content was called with correct task type
        mock_embed_content.assert_called_once_with(
            model="text-embedding-004",
            content="test text",
            task_type="CLASSIFICATION"
        )

        # Verify return value
        assert result == [0.1, 0.2, 0.3]


class TestGetEmbeddingsBatch:
    """Test cases for get_embeddings_batch function."""

    @patch('src.rag.embeddings.get_google_api_key')
    @patch('src.rag.embeddings.genai.configure')
    @patch('src.rag.embeddings.genai.batch_embed_contents')
    def test_get_embeddings_batch_successful(self, mock_batch_embed, mock_configure, mock_get_api_key):
        """Test successful batch embedding generation."""
        # Setup mocks
        mock_get_api_key.return_value = "test_api_key"
        
        mock_response = Mock()
        mock_response.embeddings = [
            Mock(values=[0.1, 0.2]),
            Mock(values=[0.3, 0.4]),
            Mock(values=[0.5, 0.6])
        ]
        mock_batch_embed.return_value = mock_response

        # Execute function
        texts = ["text1", "text2", "text3"]
        result = get_embeddings_batch(texts)

        # Verify API key was retrieved
        mock_get_api_key.assert_called_once()

        # Verify genai was configured
        mock_configure.assert_called_once_with(api_key="test_api_key")

        # Verify batch_embed_contents was called
        mock_batch_embed.assert_called_once()
        call_args = mock_batch_embed.call_args
        assert call_args[1]['model'] == "text-embedding-004"
        assert len(call_args[1]['requests']) == 3
        assert call_args[1]['requests'][0]['content'] == "text1"
        assert call_args[1]['requests'][1]['content'] == "text2"
        assert call_args[1]['requests'][2]['content'] == "text3"

        # Verify return value
        expected = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        assert result == expected

    @patch('src.rag.embeddings.get_google_api_key')
    def test_get_embeddings_batch_no_api_key(self, mock_get_api_key):
        """Test batch embedding generation when no API key is available."""
        # Setup mocks
        mock_get_api_key.return_value = None

        # Execute function
        texts = ["text1", "text2"]
        result = get_embeddings_batch(texts)

        # Verify API key was checked
        mock_get_api_key.assert_called_once()

        # Verify return value is list of None values
        assert result == [None, None]

    @patch('src.rag.embeddings.get_google_api_key')
    @patch('src.rag.embeddings.genai.configure')
    @patch('src.rag.embeddings.genai.batch_embed_contents')
    def test_get_embeddings_batch_fallback_to_individual(self, mock_batch_embed, mock_configure, mock_get_api_key):
        """Test batch embedding fallback to individual calls when batch API not available."""
        # Setup mocks
        mock_get_api_key.return_value = "test_api_key"
        
        # Mock that batch_embed_contents doesn't exist
        with patch('src.rag.embeddings.genai.batch_embed_contents', None):
            with patch('src.rag.embeddings.get_embedding') as mock_get_embedding:
                mock_get_embedding.side_effect = [
                    [0.1, 0.2],  # First call
                    [0.3, 0.4],  # Second call
                    [0.5, 0.6]   # Third call
                ]

                # Execute function
                texts = ["text1", "text2", "text3"]
                result = get_embeddings_batch(texts)

                # Verify individual embedding calls were made
                assert mock_get_embedding.call_count == 3
                mock_get_embedding.assert_any_call("text1", task_type="RETRIEVAL_DOCUMENT")
                mock_get_embedding.assert_any_call("text2", task_type="RETRIEVAL_DOCUMENT")
                mock_get_embedding.assert_any_call("text3", task_type="RETRIEVAL_DOCUMENT")

                # Verify return value
                expected = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
                assert result == expected

    @patch('src.rag.embeddings.get_google_api_key')
    @patch('src.rag.embeddings.genai.configure')
    @patch('src.rag.embeddings.genai.batch_embed_contents')
    def test_get_embeddings_batch_with_dict_response(self, mock_batch_embed, mock_configure, mock_get_api_key):
        """Test batch embedding with dict response format."""
        # Setup mocks
        mock_get_api_key.return_value = "test_api_key"
        
        mock_response = {
            "embeddings": [
                {"values": [0.1, 0.2]},
                {"values": [0.3, 0.4]}
            ]
        }
        mock_batch_embed.return_value = mock_response

        # Execute function
        texts = ["text1", "text2"]
        result = get_embeddings_batch(texts)

        # Verify return value
        assert result == [[0.1, 0.2], [0.3, 0.4]]

    @patch('src.rag.embeddings.get_google_api_key')
    @patch('src.rag.embeddings.genai.configure')
    @patch('src.rag.embeddings.genai.batch_embed_contents')
    def test_get_embeddings_batch_with_list_response(self, mock_batch_embed, mock_configure, mock_get_api_key):
        """Test batch embedding with list response format."""
        # Setup mocks
        mock_get_api_key.return_value = "test_api_key"
        
        mock_response = {
            "embeddings": [
                [0.1, 0.2],
                [0.3, 0.4]
            ]
        }
        mock_batch_embed.return_value = mock_response

        # Execute function
        texts = ["text1", "text2"]
        result = get_embeddings_batch(texts)

        # Verify return value
        assert result == [[0.1, 0.2], [0.3, 0.4]]

    @patch('src.rag.embeddings.get_google_api_key')
    @patch('src.rag.embeddings.genai.configure')
    @patch('src.rag.embeddings.genai.batch_embed_contents')
    def test_get_embeddings_batch_mismatch_length(self, mock_batch_embed, mock_configure, mock_get_api_key):
        """Test batch embedding when response length doesn't match input."""
        # Setup mocks
        mock_get_api_key.return_value = "test_api_key"
        
        mock_response = Mock()
        mock_response.embeddings = [
            Mock(values=[0.1, 0.2]),  # Only 2 embeddings
            Mock(values=[0.3, 0.4])
        ]
        mock_batch_embed.return_value = mock_response

        # Execute function with 3 texts but only 2 embeddings returned
        texts = ["text1", "text2", "text3"]
        result = get_embeddings_batch(texts)

        # Verify padding with None for missing embeddings
        expected = [[0.1, 0.2], [0.3, 0.4], None]
        assert result == expected

    @patch('src.rag.embeddings.get_google_api_key')
    @patch('src.rag.embeddings.genai.configure')
    @patch('src.rag.embeddings.genai.batch_embed_contents')
    def test_get_embeddings_batch_exception_handling(self, mock_batch_embed, mock_configure, mock_get_api_key):
        """Test batch embedding with exception handling."""
        # Setup mocks
        mock_get_api_key.return_value = "test_api_key"
        mock_batch_embed.side_effect = Exception("Batch API Error")

        # Execute function
        texts = ["text1", "text2"]
        result = get_embeddings_batch(texts)

        # Verify return value is list of None values
        assert result == [None, None]

    @patch('src.rag.embeddings.get_google_api_key')
    @patch('src.rag.embeddings.genai.configure')
    @patch('src.rag.embeddings.genai.batch_embed_contents')
    def test_get_embeddings_batch_empty_input(self, mock_batch_embed, mock_configure, mock_get_api_key):
        """Test batch embedding with empty input list."""
        # Execute function with empty list
        result = get_embeddings_batch([])

        # Verify empty list is returned
        assert result == []

    @patch('src.rag.embeddings.get_google_api_key')
    @patch('src.rag.embeddings.genai.configure')
    def test_get_embeddings_batch_with_different_task_type(self, mock_batch_embed, mock_configure, mock_get_api_key):
        """Test batch embedding with different task type."""
        # Setup mocks
        mock_get_api_key.return_value = "test_api_key"
        
        mock_response = Mock()
        mock_response.embeddings = [Mock(values=[0.1, 0.2])]
        mock_batch_embed.return_value = mock_response

        # Execute function with different task type
        texts = ["text1"]
        result = get_embeddings_batch(texts, "CLASSIFICATION")

        # Verify batch_embed_contents was called (task_type is forwarded)
        mock_batch_embed.assert_called_once()
        call_args = mock_batch_embed.call_args
        assert call_args[1]['model'] == "text-embedding-004"
        assert len(call_args[1]['requests']) == 1
        assert call_args[1]['requests'][0]['content'] == "text1"
        assert call_args[1]['requests'][0]['task_type'] == "CLASSIFICATION"

    @patch('src.rag.embeddings.get_google_api_key')
    @patch('src.rag.embeddings.genai.configure')
    @patch('src.rag.embeddings.genai.batch_embed_contents')
    def test_get_embeddings_batch_chunking(self, mock_batch_embed, mock_configure, mock_get_api_key):
        """Test batch embedding with chunking for large inputs."""
        # Setup mocks
        mock_get_api_key.return_value = "test_api_key"
        
        # Mock the batch size to be small to test chunking
        with patch('src.rag.embeddings.BATCH_SIZE', 2):
            mock_response1 = Mock()
            mock_response1.embeddings = [
                Mock(values=[0.1, 0.2]),
                Mock(values=[0.3, 0.4])
            ]
            
            mock_response2 = Mock()
            mock_response2.embeddings = [
                Mock(values=[0.5, 0.6])
            ]
            
            mock_batch_embed.side_effect = [mock_response1, mock_response2]

            # Execute function with 3 texts (will be chunked into 2 + 1)
            texts = ["text1", "text2", "text3"]
            result = get_embeddings_batch(texts)

            # Verify batch_embed_contents was called twice (chunked)
            assert mock_batch_embed.call_count == 2

            # Verify return value
            expected = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
            assert result == expected
