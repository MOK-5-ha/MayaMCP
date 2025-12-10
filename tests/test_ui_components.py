"""Unit tests for UI components."""

from unittest.mock import Mock, patch
import io
import requests
from src.ui.components import setup_avatar


class TestSetupAvatar:
    """Test cases for setup_avatar function."""

    @patch('src.ui.components.requests.get')
    @patch('src.ui.components.Image.open')
    @patch('src.ui.components.Image.new')
    def test_setup_avatar_successful_download(
        self, mock_image_new, mock_image_open, mock_requests_get
    ):
        """Test successful avatar download and save."""
        # Setup mocks
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'fake_image_data'
        mock_requests_get.return_value = mock_response

        mock_image = Mock()
        mock_image_open.return_value = mock_image

        # Execute function
        result = setup_avatar()

        # Verify HTTP request was made to default URL
        mock_requests_get.assert_called_once()
        call_args = mock_requests_get.call_args[0]
        expected_url = "https://github.com/gen-ai-capstone-project-bartender-agent/MOK-5-ha/blob/main/assets/bartender_avatar_ai_studio.jpeg?raw=true"
        assert call_args[0] == expected_url

        # Verify image was processed
        mock_image_open.assert_called_once()
        # Check that BytesIO was called with the correct content
        call_args = mock_image_open.call_args[0]
        assert len(call_args) == 1
        assert hasattr(call_args[0], 'getvalue')  # It's a BytesIO-like object
        assert call_args[0].getvalue() == b'fake_image_data'

        # Verify image was saved with correct path
        mock_image.save.assert_called_once_with("assets/bartender_avatar.jpg")

        # Verify return value matches saved path
        assert result == "assets/bartender_avatar.jpg"

    @patch('src.ui.components.requests.get')
    @patch('src.ui.components.Image.open')
    @patch('src.ui.components.Image.new')
    def test_setup_avatar_custom_url(
        self, mock_image_new, mock_image_open, mock_requests_get
    ):
        """Test avatar download with custom URL."""
        # Setup mocks
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'fake_image_data'
        mock_requests_get.return_value = mock_response

        mock_image = Mock()
        mock_image_open.return_value = mock_image

        custom_url = "https://example.com/custom_avatar.jpg"
        custom_save_path = "custom/path/avatar.jpg"

        # Execute function with custom parameters
        result = setup_avatar(avatar_url=custom_url, save_path=custom_save_path)

        # Verify HTTP request was made to custom URL
        mock_requests_get.assert_called_once_with(custom_url)

        # Verify image was saved to custom path
        mock_image.save.assert_called_once_with(custom_save_path)

        # Verify return value matches saved path
        assert result == custom_save_path

    @patch('src.ui.components.requests.get')
    @patch('src.ui.components.Image.new')
    def test_setup_avatar_http_error_fallback(
        self, mock_image_new, mock_requests_get
    ):
        """Test fallback behavior when HTTP request fails."""
        # Setup mocks for failed HTTP request
        mock_response = Mock()
        mock_response.status_code = 404
        mock_requests_get.return_value = mock_response

        mock_image = Mock()
        mock_image_new.return_value = mock_image

        # Execute function
        result = setup_avatar()

        # Verify HTTP request was attempted
        mock_requests_get.assert_called_once()

        # Verify fallback image was created
        mock_image_new.assert_called_once_with('RGB', (300, 300), color=(73, 109, 137))

        # Verify fallback image was saved with correct path
        mock_image.save.assert_called_once_with("assets/bartender_avatar.jpg")

        # Verify return value matches saved path
        assert result == "assets/bartender_avatar.jpg"

    @patch('src.ui.components.requests.get')
    @patch('src.ui.components.Image.new')
    def test_setup_avatar_request_exception_fallback(
        self, mock_image_new, mock_requests_get
    ):
        """Test fallback behavior when request raises exception."""
        # Setup mock to raise exception
        mock_requests_get.side_effect = requests.RequestException("Network error")

        mock_image = Mock()
        mock_image_new.return_value = mock_image

        # Execute function
        result = setup_avatar()

        # Verify exception was handled
        mock_requests_get.assert_called_once()

        # Verify fallback image was created
        mock_image_new.assert_called_once_with('RGB', (300, 300), color=(73, 109, 137))

        # Verify fallback image was saved with correct path
        mock_image.save.assert_called_once_with("assets/bartender_avatar.jpg")

        # Verify return value matches saved path
        assert result == "assets/bartender_avatar.jpg"

    @patch('src.ui.components.requests.get')
    @patch('src.ui.components.Image.open')
    @patch('src.ui.components.Image.new')
    def test_setup_avatar_save_exception_fallback(
        self, mock_image_new, mock_image_open, mock_requests_get
    ):
        """Test fallback behavior when image save fails."""
        # Setup mocks for successful download
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'fake_image_data'
        mock_requests_get.return_value = mock_response

        mock_image = Mock()
        mock_image_open.return_value = mock_image

        # Setup save to raise exception
        mock_image.save.side_effect = Exception("Save failed")

        # Execute function
        result = setup_avatar()

        # Verify HTTP request was made
        mock_requests_get.assert_called_once()

        # Verify image processing occurred
        mock_image_open.assert_called_once()
        # Check that BytesIO was called with the correct content
        call_args = mock_image_open.call_args[0]
        assert len(call_args) == 1
        assert hasattr(call_args[0], 'getvalue')  # It's a BytesIO-like object
        assert call_args[0].getvalue() == b'fake_image_data'

        # Verify save was attempted
        mock_image.save.assert_called_once_with("assets/bartender_avatar.jpg")

        # Verify return value is fallback path
        assert result == "assets/bartender_avatar.jpg"

    @patch('src.ui.components.requests.get')
    @patch('src.ui.components.Image.open')
    @patch('src.ui.components.Image.new')
    def test_setup_avatar_image_processing_error(
        self, mock_image_new, mock_image_open, mock_requests_get
    ):
        """Test behavior when image processing fails."""
        # Setup mocks for successful download but failed image processing
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'invalid_image_data'
        mock_requests_get.return_value = mock_response

        # Mock Image.open to raise exception
        mock_image_open.side_effect = Exception("Invalid image format")

        mock_image = Mock()
        mock_image_new.return_value = mock_image

        # Execute function
        result = setup_avatar()

        # Verify HTTP request was made
        mock_requests_get.assert_called_once()

        # Verify fallback image was created due to processing error
        mock_image_new.assert_called_once_with('RGB', (300, 300), color=(73, 109, 137))

        # Verify fallback image was saved with correct path
        mock_image.save.assert_called_once_with("assets/bartender_avatar.jpg")

        # Verify return value matches saved path
        assert result == "assets/bartender_avatar.jpg"

    @patch('src.ui.components.requests.get')
    @patch('src.ui.components.Image.open')
    @patch('src.ui.components.Image.new')
    def test_setup_avatar_empty_response_content(
        self, mock_image_new, mock_image_open, mock_requests_get
    ):
        """Test behavior when response has empty content."""
        # Setup mocks for successful response but empty content
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b''
        mock_requests_get.return_value = mock_response

        # Mock Image.open to raise exception for empty content
        mock_image_open.side_effect = Exception("Empty image content")

        mock_image = Mock()
        mock_image_new.return_value = mock_image

        # Execute function
        result = setup_avatar()

        # Verify HTTP request was made
        mock_requests_get.assert_called_once()

        # Verify fallback image was created due to empty content
        mock_image_new.assert_called_once_with('RGB', (300, 300), color=(73, 109, 137))

        # Verify fallback image was saved with correct path
        mock_image.save.assert_called_once_with("assets/bartender_avatar.jpg")

        # Verify return value matches saved path
        assert result == "assets/bartender_avatar.jpg"

    @patch('src.ui.components.requests.get')
    @patch('src.ui.components.Image.open')
    @patch('src.ui.components.Image.new')
    def test_setup_avatar_multiple_calls_same_path(
        self, mock_image_new, mock_image_open, mock_requests_get
    ):
        """Test multiple calls to setup_avatar with same path."""
        # Setup mocks
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'fake_image_data'
        mock_requests_get.return_value = mock_response

        mock_image = Mock()
        mock_image_open.return_value = mock_image

        # Execute function multiple times
        result1 = setup_avatar()
        result2 = setup_avatar()

        # Verify HTTP requests were made both times
        assert mock_requests_get.call_count == 2

        # Verify images were saved both times
        assert mock_image.save.call_count == 2

        # Verify return values match saved path
        assert result1 == "assets/bartender_avatar.jpg"
        assert result2 == "assets/bartender_avatar.jpg"

    @patch('src.ui.components.logger')
    @patch('src.ui.components.requests.get')
    @patch('src.ui.components.Image.open')
    @patch('src.ui.components.Image.new')
    def test_setup_avatar_logging_behavior(
        self, mock_image_new, mock_image_open, mock_requests_get, mock_logger
    ):
        """Test that appropriate logging occurs during avatar setup."""
        # Setup mocks for successful case
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'fake_image_data'
        mock_requests_get.return_value = mock_response

        mock_image = Mock()
        mock_image_open.return_value = mock_image

        # Execute function
        result = setup_avatar()

        # Verify image was saved with correct path
        mock_image.save.assert_called_once_with("assets/bartender_avatar.jpg")

        # Verify return value matches saved path
        assert result == "assets/bartender_avatar.jpg"

        # Verify logging calls were made
        mock_logger.info.assert_any_call("Successfully downloaded avatar image")
        mock_logger.info.assert_any_call("Avatar saved to assets/bartender_avatar.jpg")

    @patch('src.ui.components.logger')
    @patch('src.ui.components.requests.get')
    @patch('src.ui.components.Image.new')
    def test_setup_avatar_error_logging(
        self, mock_image_new, mock_requests_get, mock_logger
    ):
        """Test that error logging occurs when avatar setup fails."""
        # Setup mocks for failed HTTP request
        mock_response = Mock()
        mock_response.status_code = 500
        mock_requests_get.return_value = mock_response

        mock_image = Mock()
        mock_image_new.return_value = mock_image
        # Setup save to raise exception to exercise the save-failure branch
        mock_image.save.side_effect = Exception("Save failed")

        # Execute function
        result = setup_avatar()

        # Verify fallback image was saved (attempted)
        mock_image.save.assert_called_once_with("assets/bartender_avatar.jpg")

        # Verify return value is fallback path
        assert result == "assets/bartender_avatar.jpg"

        # Verify error logging calls were made
        mock_logger.warning.assert_any_call("Failed to download avatar. Status code: 500")
        mock_logger.error.assert_any_call("Error saving avatar: Save failed")
