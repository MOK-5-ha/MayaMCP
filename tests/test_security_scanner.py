import pytest
from unittest.mock import MagicMock, patch
from src.security.scanner import scan_output, scan_input, is_available, ScanResult, INPUT_BLOCKED_INJECTION, INPUT_BLOCKED_TOXIC, OUTPUT_FALLBACK
from src.security.config import ScanConfig
from hypothesis import given, strategies as st

# Return the input_scanners mock
@pytest.fixture
def mock_defenses():
    scanners_mock = MagicMock()
    output_scanners_mock = MagicMock()
    
    # We create a mock for the module
    llm_guard_mock = MagicMock()
    llm_guard_mock.input_scanners = scanners_mock
    llm_guard_mock.output_scanners = output_scanners_mock
    
    with patch.dict("sys.modules", {
        "llm_guard": llm_guard_mock, 
        "llm_guard.input_scanners": scanners_mock,
        "llm_guard.output_scanners": output_scanners_mock
    }):
        yield (scanners_mock, output_scanners_mock)

def test_is_available_defaults_true(mock_defenses):
    assert is_available() is True


def test_is_available_when_unavailable():
    # Override the fixture or just patch here. 
    # Since fixture patch is active, we patch over it.
    with patch.dict("sys.modules", {"llm_guard": None}):
        # Force reload or re-check? is_available does import inside.
        assert is_available() is False

def test_scan_input_unavailable():
    with patch("src.security.scanner.is_available", return_value=False):
        result = scan_input("bad input")
        assert result.is_valid
        assert result.sanitized_text == "bad input"

@patch("src.security.scanner.is_available", return_value=True)
def test_scan_input_valid(mock_avail, mock_defenses):
    scanners, _ = mock_defenses
    
    # Configure PI
    scanners.PromptInjection.return_value.scan.return_value = ("clean input", True, 0.1)
    # Configure Toxicity
    scanners.Toxicity.return_value.scan.return_value = ("clean input", True, 0.1)
    
    result = scan_input("clean input")
    assert result.is_valid
    assert result.sanitized_text == "clean input"

@patch("src.security.scanner.is_available", return_value=True)
def test_scan_input_injection(mock_avail, mock_defenses):
    scanners, _ = mock_defenses
    
    scanners.PromptInjection.return_value.scan.return_value = ("injection attempt", False, 0.9)
    # Toxicity valid
    scanners.Toxicity.return_value.scan.return_value = ("injection attempt", True, 0.1)

    result = scan_input("injection attempt")
    assert not result.is_valid
    assert result.blocked_reason == INPUT_BLOCKED_INJECTION
    assert result.scanner_scores["prompt_injection"] == 0.9

@patch("src.security.scanner.is_available", return_value=True)
def test_scan_input_toxic(mock_avail, mock_defenses):
    scanners, _ = mock_defenses
    
    # PI valid
    scanners.PromptInjection.return_value.scan.return_value = ("toxic input", True, 0.1)
    # Toxicity invalid
    scanners.Toxicity.return_value.scan.return_value = ("toxic input", False, 0.9)
    
    result = scan_input("toxic input")
    assert not result.is_valid
    assert result.blocked_reason == INPUT_BLOCKED_TOXIC
    assert result.scanner_scores["toxicity"] == 0.9
    
@given(st.floats(min_value=0.6, max_value=1.0))
def test_property_prompt_injection_blocked(score):
    """
    Property 1: Prompt injection inputs are blocked
    Validates: Requirements 1.2
    """
    input_scanners_mock = MagicMock()
    output_scanners_mock = MagicMock()
    with patch.dict("sys.modules", {"llm_guard": MagicMock(), "llm_guard.input_scanners": input_scanners_mock, "llm_guard.output_scanners": output_scanners_mock}), \
         patch("src.security.scanner.is_available", return_value=True):
         
        scanners = input_scanners_mock
        scanners.PromptInjection.return_value.scan.return_value = ("input", False, score)
        scanners.Toxicity.return_value.scan.return_value = ("input", True, 0.0)
        
        result = scan_input("some input")
        assert not result.is_valid
        assert result.blocked_reason == INPUT_BLOCKED_INJECTION

@given(st.floats(min_value=0.6, max_value=1.0))
def test_property_toxic_input_blocked(score):
    """
    Property 2: Toxic inputs are blocked
    Validates: Requirements 2.1
    """
    input_scanners_mock = MagicMock()
    output_scanners_mock = MagicMock()
    with patch.dict("sys.modules", {"llm_guard": MagicMock(), "llm_guard.input_scanners": input_scanners_mock, "llm_guard.output_scanners": output_scanners_mock}), \
         patch("src.security.scanner.is_available", return_value=True):

        scanners = input_scanners_mock
        scanners.PromptInjection.return_value.scan.return_value = ("input", True, 0.0)
        scanners.Toxicity.return_value.scan.return_value = ("input", False, score)
        
        result = scan_input("some input")
        assert not result.is_valid
        assert result.blocked_reason == INPUT_BLOCKED_TOXIC

@patch("src.security.scanner.is_available", return_value=True)
def test_scan_output_valid(mock_avail, mock_defenses):
    _, output_scanners = mock_defenses
    output_scanners.Toxicity.return_value.scan.return_value = ("clean output", True, 0.1)
    
    result = scan_output("clean output")
    assert result.is_valid
    assert result.sanitized_text == "clean output"

@patch("src.security.scanner.is_available", return_value=True)
def test_scan_output_toxic(mock_avail, mock_defenses):
    _, output_scanners = mock_defenses
    output_scanners.Toxicity.return_value.scan.return_value = ("toxic output", False, 0.9)
    
    result = scan_output("toxic output")
    assert not result.is_valid
    assert result.sanitized_text == OUTPUT_FALLBACK
    assert result.scanner_scores["toxicity"] == 0.9

@given(st.floats(min_value=0.6, max_value=1.0))
def test_property_toxic_output_replaced(score):
    """
    Property 3: Toxic outputs are replaced with fallback
    Validates: Requirements 3.2
    """
    input_scanners_mock = MagicMock()
    output_scanners_mock = MagicMock()
    with patch.dict("sys.modules", {"llm_guard": MagicMock(), "llm_guard.input_scanners": input_scanners_mock, "llm_guard.output_scanners": output_scanners_mock}), \
         patch("src.security.scanner.is_available", return_value=True):

        scanners = output_scanners_mock
        scanners.Toxicity.return_value.scan.return_value = ("toxic output", False, score)
        
        result = scan_output("toxic output")
        assert not result.is_valid
        assert result.sanitized_text == OUTPUT_FALLBACK
