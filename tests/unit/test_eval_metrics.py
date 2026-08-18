"""Unit tests for tests/eval/metrics.py evaluation function."""

from unittest.mock import MagicMock, patch

from tests.eval.metrics import _Verdict, evaluate


def test_evaluate_success():
    """Test evaluate calls get_genai_client and correctly parses the returned verdict."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed = _Verdict(score=4, explanation="Good response.")
    mock_client.models.generate_content.return_value = mock_response

    with patch("tests.eval.metrics.get_genai_client", return_value=mock_client) as mock_get_client:
        instance = {
            "prompt": "Make me a drink",
            "response": "Here is a nice martini.",
            "reference": "Serve a martini",
            "agent_data": "Trace data",
        }
        result = evaluate(instance)

        assert result == {"score": 4, "explanation": "Good response."}
        mock_get_client.assert_called_once()
        mock_client.models.generate_content.assert_called_once()


def test_evaluate_none_verdict_fallback():
    """Test evaluate falls back gracefully when model returns unparseable output."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.parsed = None
    mock_response.text = "Unparseable error"
    mock_client.models.generate_content.return_value = mock_response

    with patch("tests.eval.metrics.get_genai_client", return_value=mock_client):
        instance = {"prompt": "Hello", "response": "Hi"}
        result = evaluate(instance)

        assert result == {"score": 0, "explanation": "Unparseable error"}
