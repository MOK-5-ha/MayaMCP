"""
Global test configuration and shims for optional third-party SDKs.
This ensures tests run even if google-generativeai or google-genai are not installed locally.
"""

import sys
from types import ModuleType, SimpleNamespace as NS
import pytest

# Create 'google' package if missing
if 'google' not in sys.modules:
    google_module = ModuleType('google')
    google_module.__path__ = []  # Required for importlib.util.find_spec
    sys.modules['google'] = google_module

# Stub google.generativeai (AI Studio free-tier SDK) only if the real package is not available
import importlib.util as _importlib_util
if _importlib_util.find_spec('google.generativeai') is None:
    genai = ModuleType('google.generativeai')

    # Minimal surface used by the code
    def _configure(api_key: str | None = None, **kwargs):
        setattr(genai, '_last_config', {'api_key': api_key, **kwargs})

    class _Response:
        def __init__(self, text: str = ""):
            self.text = text

    class _GenerativeModel:
        def __init__(self, model: str):
            self._model = model
        def generate_content(self, contents=None, generation_config=None):
            return _Response(text="")

    def _embed_content(model: str, content: str, **kwargs):
        # Default embedding response shape: dict with embedding.values
        return {"embedding": {"values": [0.0]}}

    def _batch_embed_contents(model: str, requests: list[dict], **kwargs):
        # Return list-like embeddings matching requests length
        return {"embeddings": [{"values": [0.0]} for _ in requests]}

    genai.configure = _configure
    genai.GenerativeModel = _GenerativeModel
    genai.embed_content = _embed_content
    genai.batch_embed_contents = _batch_embed_contents

    sys.modules['google.generativeai'] = genai

# Keep legacy google.genai stubs for any tests that still import it
if 'google.genai' not in sys.modules:
    genai_mod = ModuleType('google.genai')
    types_mod = ModuleType('google.genai.types')

    class GenerateContentConfig:
        def __init__(self, temperature=None, top_p=None, top_k=None, max_output_tokens=None):
            self.temperature = temperature
            self.top_p = top_p
            self.top_k = top_k
            self.max_output_tokens = max_output_tokens

    class GenerateContentResponse:
        def __init__(self, text: str = ""):
            self.text = text

    class _Models:
        def generate_content(self, model: str, contents=None, config=None):
            return NS(text="")
        def embed_content(self, model: str, input=None, task_type=None):
            return NS(embedding=NS(values=[0.0]))

    class Client:
        def __init__(self, *args, **kwargs):
            self.models = _Models()

    genai_mod.Client = Client
    types_mod.GenerateContentConfig = GenerateContentConfig
    types_mod.GenerateContentResponse = GenerateContentResponse

    sys.modules['google.genai'] = genai_mod
    sys.modules['google.genai.types'] = types_mod
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


@pytest.fixture(autouse=True, scope="session")
def setup_src_path():
    """
    Automatically add the src directory to sys.path for all tests.
    This ensures that imports like 'src.llm.client' work correctly.
    """
    import sys
    from pathlib import Path

    # Get the repository root directory (parent of tests directory)
    repo_root = Path(__file__).parent.parent
    src_path = repo_root / "src"

    # Convert to absolute path string
    src_path_str = str(src_path.resolve())

    # Only add to sys.path if not already present
    if src_path_str not in sys.path:
        sys.path.insert(0, src_path_str)
