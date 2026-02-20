#!/usr/bin/env python3
"""
Test script to verify Maya's functionality. Used by Claude.
"""

import sys
import os
import pytest
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Tuple, Any, Generator

# Compute absolute path to src directory based on this test file's location
test_file_dir = Path(__file__).resolve().parent
repo_root_dir = test_file_dir.parent

from src.config import get_api_keys, setup_logging
from src.llm import initialize_llm, get_all_tools

from src.voice import initialize_cartesia_client
from src.conversation.processor import process_order
from src.utils.state_manager import initialize_state


class MayaTestComponents:
    """Container for Maya test components with proper cleanup."""

    def __init__(self):
        self.logger = None
        self.llm = None

        self.cartesia_client = None
        self.api_keys = None


@contextmanager
def maya_test_environment() -> Generator[MayaTestComponents, None, None]:
    """
    Context manager for Maya test environment setup and cleanup.

    Yields:
        MayaTestComponents: Initialized components for testing
    """
    components = MayaTestComponents()

    try:
        # Setup logging
        components.logger = setup_logging()
        components.logger.info("Starting Maya test environment setup")

        # Get API keys
        components.api_keys = get_api_keys()
        _validate_api_keys(components.api_keys, components.logger)

        # Initialize components
        _initialize_components(components)

        components.logger.info("✅ Maya test environment ready")
        yield components

    except Exception as e:
        if components.logger:
            components.logger.error(f"Test environment setup failed: {e}")
        raise
    finally:
        # Cleanup in reverse order of initialization
        _cleanup_components(components)


def _validate_api_keys(api_keys: dict, logger) -> None:
    """Validate required API keys are present."""
    required_keys = ["google_api_key", "cartesia_api_key"]
    missing_keys = [key for key in required_keys if not api_keys.get(key)]

    if missing_keys:
        error_msg = f"Missing required API keys: {', '.join(missing_keys)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info("API keys validated successfully")


def _initialize_components(components: MayaTestComponents) -> None:
    """Initialize all Maya components."""
    logger = components.logger

    # State manager
    logger.info("Initializing state manager...")
    initialize_state()
    logger.info("✅ State manager initialized")

    # LLM tools and client
    logger.info("Getting LLM tools...")
    tools = get_all_tools()
    logger.info(f"✅ Retrieved {len(tools)} LLM tools")

    logger.info("Initializing LLM client...")
    components.llm = initialize_llm(
        api_key=components.api_keys["google_api_key"],
        tools=tools
    )
    logger.info("✅ LLM client initialized")



    # Cartesia client
    logger.info("Initializing Cartesia TTS client...")
    components.cartesia_client = initialize_cartesia_client(
        components.api_keys["cartesia_api_key"]
    )
    logger.info("✅ Cartesia TTS client initialized")


def _cleanup_components(components: MayaTestComponents) -> None:
    """Clean up Maya components."""
    if not components.logger:
        return

    components.logger.info("Starting cleanup...")

    # Cleanup clients with close methods
    for client_name, client in [
        ("Cartesia client", components.cartesia_client),
        ("LLM client", components.llm)
    ]:
        if client and hasattr(client, 'close'):
            try:
                client.close()
                components.logger.info(f"✅ {client_name} closed")
            except Exception as e:
                components.logger.error(f"Failed to close {client_name}: {e}")

    # State manager cleanup
    try:
        # Import state cleanup functions if they exist
        from src.utils.state_manager import reset_state
        reset_state()
        components.logger.info("✅ State manager reset")
    except (ImportError, AttributeError):
        # Functions don't exist, skip silently
        pass
    except Exception as e:
        components.logger.error(f"Failed to reset state manager: {e}")

    components.logger.info("✅ Cleanup completed")


def _validate_response(response: str, description: str) -> None:
    """Validate a response from Maya."""
    if not isinstance(response, str) or not response.strip():
        raise AssertionError(f"{description} response is empty or not a string")


def _validate_history(history: list, description: str, min_length: int = 1) -> None:
    """Validate conversation history."""
    if not isinstance(history, list) or len(history) < min_length:
        raise AssertionError(f"{description} history is invalid or too short")

    last_entry = history[-1]
    if not isinstance(last_entry, dict):
        raise AssertionError(f"{description} history last entry is not a dict")

    required_keys = ['role', 'content']
    for key in required_keys:
        if key not in last_entry or not last_entry[key]:
            raise AssertionError(
                f"{description} history last entry missing or empty '{key}'"
            )


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("RUN_E2E") != "1", reason="E2E tests disabled")
def test_maya_interaction() -> bool:
    """Test Maya's full interaction workflow."""

    with maya_test_environment() as components:
        logger = components.logger
        logger.info("Starting Maya interaction test")

        # Test conversation flow
        session_history = []

        # First interaction: Order a drink
        response1, history1, _, order1, _ = process_order(
            user_input_text="I would like a whiskey on the rocks please",
            current_session_history=session_history,
            llm=components.llm,
            api_key=components.api_keys["google_api_key"]
        )

        # Validate first response
        _validate_response(response1, "First interaction")
        _validate_history(history1, "First interaction", min_length=2)

        if not isinstance(order1, list):
            raise AssertionError("Updated order after first interaction is not a list")

        # Second interaction: Check order
        response2, history2, _, _, _ = process_order(
            user_input_text="What's in my order?",
            current_session_history=history1,
            llm=components.llm,
            api_key=components.api_keys["google_api_key"]
        )

        # Validate second response
        _validate_response(response2, "Second interaction")
        _validate_history(history2, "Second interaction")

        # Third interaction: Get bill
        response3, _, _, _, _ = process_order(
            user_input_text="What's my bill?",
            current_session_history=history2,
            llm=components.llm,
            api_key=components.api_keys["google_api_key"]
        )

        # Validate third response
        _validate_response(response3, "Third interaction (bill)")

        logger.info("✅ Maya interaction test completed successfully")
        return True


if __name__ == "__main__":
    try:
        success = test_maya_interaction()
        if success:
            print("✅ Test completed successfully!")
            sys.exit(0)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
