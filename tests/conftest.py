"""
Global test configuration and shims for optional third-party SDKs.
This ensures tests run even if google-genai is not installed locally.
"""

import importlib.util as _importlib_util
import sys
from types import ModuleType
from types import SimpleNamespace as NS

import pytest

# Create 'google' package if missing
if 'google' not in sys.modules:
    google_module = ModuleType('google')
    google_module.__path__ = []  # Required for importlib.util.find_spec
    sys.modules['google'] = google_module

# Stub google.genai SDK only if the real package is NOT installed
if _importlib_util.find_spec('google.genai') is None:
    genai_mod = ModuleType('google.genai')
    types_mod = ModuleType('google.genai.types')
    errors_mod = ModuleType('google.genai.errors')

    # Exception class stubs for google.genai.errors
    # Allow imports like "from google.genai.errors import APIError"
    # These match the real google.genai.errors structure plus common aliases
    class APIError(Exception):
        """Base class for Google GenAI API errors."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args)
            # Store keyword args as attributes for SDK compatibility
            for key, value in kwargs.items():
                setattr(self, key, value)

    class ClientError(APIError):
        """Client-side error."""
        pass

    class ServerError(APIError):
        """Server-side error."""
        pass

    class FunctionInvocationError(APIError):
        """Error during function invocation."""
        pass

    # Common aliases/expected names that code may check via getattr
    class NotFoundError(APIError):
        """Resource not found error."""
        pass

    class InvalidArgumentError(APIError):
        """Invalid argument error."""
        pass

    class PermissionDenied(APIError):
        """Permission denied error."""
        pass

    class PermissionDeniedError(PermissionDenied):
        """Alias for PermissionDenied for SDK compatibility."""
        pass

    class AuthenticationError(APIError):
        """Authentication error."""
        pass

    class UnauthenticatedError(APIError):
        """Unauthenticated error."""
        pass

    class RateLimitError(APIError):
        """Rate limit exceeded error."""
        pass

    class GenAITimeoutError(APIError):
        """Request timeout error for GenAI operations."""
        pass

    # Alias for SDK compatibility; shadows built-in intentionally
    TimeoutError = GenAITimeoutError

    # Assign exception classes to the errors module before sys.modules
    errors_mod.APIError = APIError
    errors_mod.ClientError = ClientError
    errors_mod.ServerError = ServerError
    errors_mod.FunctionInvocationError = FunctionInvocationError
    errors_mod.NotFoundError = NotFoundError
    errors_mod.InvalidArgumentError = InvalidArgumentError
    errors_mod.PermissionDenied = PermissionDenied
    errors_mod.PermissionDeniedError = PermissionDeniedError
    errors_mod.AuthenticationError = AuthenticationError
    errors_mod.UnauthenticatedError = UnauthenticatedError
    errors_mod.RateLimitError = RateLimitError
    errors_mod.GenAITimeoutError = GenAITimeoutError
    errors_mod.TimeoutError = TimeoutError

    class GenerateContentConfig:
        def __init__(self, temperature=None, top_p=None, top_k=None, max_output_tokens=None, **kwargs):
            self.temperature = temperature
            self.top_p = top_p
            self.top_k = top_k
            self.max_output_tokens = max_output_tokens

    class EmbedContentConfig:
        def __init__(self, task_type=None, output_dimensionality=None, **kwargs):
            self.task_type = task_type
            self.output_dimensionality = output_dimensionality

    class GenerateContentResponse:
        def __init__(self, text: str = ""):
            self.text = text

    class _Models:
        def generate_content(self, model: str, contents=None, config=None):
            return NS(text="")
        def embed_content(self, model: str, contents=None, config=None):
            # Handle both single and batch (list input)
            if isinstance(contents, list):
                return NS(embeddings=[NS(values=[0.0]) for _ in contents])
            return NS(embeddings=[NS(values=[0.0])])

    class Client:
        def __init__(self, *args, **kwargs):
            self.models = _Models()

    genai_mod.Client = Client
    types_mod.GenerateContentConfig = GenerateContentConfig
    types_mod.EmbedContentConfig = EmbedContentConfig
    types_mod.GenerateContentResponse = GenerateContentResponse

    sys.modules['google.genai'] = genai_mod
    sys.modules['google.genai.types'] = types_mod
    sys.modules['google.genai.errors'] = errors_mod
    sys.modules['google'].genai = genai_mod

# Autouse fixture: no-op (kept for compatibility).
@pytest.fixture(autouse=True)
def _compat_fixture():
    yield


def pytest_addoption(parser):
    """Add command-line options for test configuration."""
    parser.addoption(
        "--force-rebuild",
        action="store_true",
        default=False,
        help="Force rebuild of expensive test resources like Memvid store (default: False for CI efficiency)"
    )


@pytest.fixture(scope="session")
def force_rebuild_flag(request):
    """
    Fixture to determine if expensive rebuilds should be performed.

    Priority (highest to lowest):
    1. Command-line flag: pytest --force-rebuild
    2. Environment variable: TEST_FORCE_REBUILD=1
    3. Default: False (for CI efficiency)

    Usage in tests:
    - def test_something(force_rebuild_flag): initialize_store(force_rebuild=force_rebuild_flag)
    - Environment: TEST_FORCE_REBUILD=1 pytest tests/test_memvid.py
    - CLI: pytest --force-rebuild tests/test_memvid.py
    """
    import os

    # Check command-line option first
    if request.config.getoption("--force-rebuild"):
        return True

    # Check environment variable
    if os.getenv("TEST_FORCE_REBUILD", "0") == "1":
        return True

    # Default to False for CI efficiency
    return False
