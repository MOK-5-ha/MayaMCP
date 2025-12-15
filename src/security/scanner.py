import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from .config import ScanConfig

logger = logging.getLogger(__name__)

# Constants for rejection messages
INPUT_BLOCKED_INJECTION = "I can't process that request. Could you rephrase?"
INPUT_BLOCKED_TOXIC = "Let's keep things friendly! How can I help with drinks?"
OUTPUT_FALLBACK = "I'm not sure how to respond to that. What drink can I get you?"

@dataclass
class ScanResult:
    is_valid: bool
    sanitized_text: str
    blocked_reason: str = ""
    scanner_scores: Dict[str, float] = field(default_factory=dict)

def is_available() -> bool:
    """Check if llm-guard is installed and functional."""
    try:
        import llm_guard
        return True
    except ImportError:
        logger.warning("llm-guard not installed. Security scanning is disabled.")
        return False
    except Exception as e:
        logger.warning(f"Error checking llm-guard availability: {e}")
        return False

def scan_input(text: str, config: Optional[ScanConfig] = None) -> ScanResult:
    """
    Scan user input for prompt injection and toxicity.
    Returns ScanResult with is_valid=False if blocked.
    Fails open on errors.
    """
    if config is None:
        config = ScanConfig()

    if not is_available():
        return ScanResult(is_valid=True, sanitized_text=text)

    try:
        from llm_guard.input_scanners import PromptInjection, Toxicity
    except ImportError:
        logger.warning("Failed to import llm-guard scanners. Passing through.")
        return ScanResult(is_valid=True, sanitized_text=text)

    scanner_scores = {}
    
    # 1. Prompt Injection
    if config.prompt_injection_enabled:
        try:
            # Note: In a real app we might cache these scanners
            scanner = PromptInjection(threshold=config.prompt_injection_threshold)
            sanitized, is_valid, score = scanner.scan(text)
            
            # llm-guard returns score: float or list/dict depending on version/scanner
            # Assuming float for simple case, or we grab the relevant value
            # Usually scan returns (sanitized_prompt, results_valid, results_score)
            
            # Note: scanner.scan signature in llm-guard:
            # scan(prompt: str) -> (str, bool, float)
            
            scanner_scores["prompt_injection"] = score
            
            if not is_valid:
                return ScanResult(
                    is_valid=False,
                    sanitized_text=sanitized,
                    blocked_reason=INPUT_BLOCKED_INJECTION,
                    scanner_scores=scanner_scores
                )
        except Exception as e:
            logger.error(f"Error in prompt injection scanner: {e}")
            # Fail open for this scanner, continue to next

    # 2. Toxicity
    if config.toxicity_enabled:
        try:
            scanner = Toxicity(threshold=config.toxicity_threshold)
            sanitized, is_valid, score = scanner.scan(text)
            scanner_scores["toxicity"] = score
            
            if not is_valid:
                return ScanResult(
                    is_valid=False,
                    sanitized_text=sanitized,
                    blocked_reason=INPUT_BLOCKED_TOXIC,
                    scanner_scores=scanner_scores
                )
        except Exception as e:
            logger.error(f"Error in toxicity scanner: {e}")

    return ScanResult(is_valid=True, sanitized_text=text, scanner_scores=scanner_scores)

def scan_output(text: str, prompt: str = "", config: Optional[ScanConfig] = None) -> ScanResult:
    """
    Scan LLM output for toxicity.
    Returns ScanResult with fallback message if toxic.
    Fails open on errors.
    """
    if config is None:
        config = ScanConfig()

    if not is_available():
        return ScanResult(is_valid=True, sanitized_text=text)

    try:
        from llm_guard.output_scanners import Toxicity
    except ImportError:
        logger.warning("Failed to import llm-guard output scanners. Passing through.")
        return ScanResult(is_valid=True, sanitized_text=text)

    scanner_scores = {}

    if config.toxicity_enabled:
        try:
            # Output scanner signature usually: scan(prompt, output) -> (sanitized_output, is_valid, score)
            scanner = Toxicity(threshold=config.toxicity_threshold)
            sanitized, is_valid, score = scanner.scan(prompt, text)
            scanner_scores["toxicity"] = score

            if not is_valid:
                return ScanResult(
                    is_valid=False,
                    sanitized_text=OUTPUT_FALLBACK,
                    blocked_reason="Toxicity limit exceeded",
                    scanner_scores=scanner_scores
                )
        except Exception as e:
            logger.error(f"Error in output toxicity scanner: {e}")
            # Fail open

    return ScanResult(is_valid=True, sanitized_text=text, scanner_scores=scanner_scores)
