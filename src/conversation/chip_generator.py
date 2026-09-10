"""Chip generation for contextual suggestion chips."""

import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any

from google import genai
from pydantic import ValidationError

from ..config.logging_config import get_logger
from ..config.model_config import get_model_config
from ..llm.client import build_generate_config, call_gemini_api, get_genai_client
from ..schemas.chips import (
    ActionID,
    ChipGenerationContext,
    ChipType,
    SuggestionChip,
    SuggestionChipSet,
)

logger = get_logger(__name__)

# Global thread pool for chip generation (max 10 concurrent per instance)
_chip_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="chip_gen")


class ChipGenerator:
    """Generates contextual suggestion chips using LLM structured output."""

    TIMEOUT_SECONDS = 3.0
    RATE_LIMIT_SECONDS = 2.0
    MAX_PROMPT_TOKENS = 512
    MAX_OUTPUT_TOKENS = 200

    def __init__(
        self, session_id: str, llm_client: genai.Client | None = None
    ):
        """
        Initialize chip generator.

        Args:
            session_id: Current session identifier
            llm_client: Optional LLM client for dependency injection (testing)
        """
        self.session_id = session_id
        self.llm_client = llm_client or get_genai_client()
        self._cache: dict[str, Any] = {}  # Context representation cache

    def generate_chips_async(
        self, context: ChipGenerationContext
    ) -> SuggestionChipSet | None:
        """
        Generate chips asynchronously with timeout.

        This method submits chip generation to a background thread pool
        and enforces a 3-second timeout. If generation exceeds timeout
        or fails, returns None (empty chip set).

        Args:
            context: Chip generation context with conversation history

        Returns:
            SuggestionChipSet or None on timeout/failure
        """
        # Import here to avoid circular dependency
        from ..utils.state_manager import (
            _get_session_data,
            _get_store_and_session,
            _save_session_data,
            get_session_lock,
        )

        session_id, store = _get_store_and_session(self.session_id, None)
        lock = get_session_lock(session_id)

        current_time = time.time()
        future = None

        # Atomically check rate limit, cancel pending task, and submit new task
        with lock:
            data = _get_session_data(session_id, store)
            chip_state = data.get("chip_state", {})
            last_gen_time = chip_state.get("last_generation_time", 0)

            if current_time - last_gen_time < self.RATE_LIMIT_SECONDS:
                logger.warning(
                    f"Rate limit exceeded for session {self.session_id}, "
                    f"skipping chip generation"
                )
                return None

            # Cancel pending task if exists
            pending_task = chip_state.get("pending_task")
            if pending_task and not pending_task.done():
                logger.info(
                    f"Cancelling pending chip generation for {self.session_id}"
                )
                pending_task.cancel()

            # Submit generation task and store it atomically
            future = _chip_executor.submit(self._generate_chips_sync, context)
            chip_state["pending_task"] = future
            data["chip_state"] = chip_state
            _save_session_data(session_id, store, data)

        # Wait with timeout
        try:
            result = future.result(timeout=self.TIMEOUT_SECONDS)

            # Update metadata
            with lock:
                data = _get_session_data(session_id, store)
                chip_state = data.get("chip_state", {})
                chip_state["last_generation_time"] = current_time
                chip_state["generation_count"] = (
                    chip_state.get("generation_count", 0) + 1
                )
                data["chip_state"] = chip_state
                _save_session_data(session_id, store, data)

            return result

        except FutureTimeoutError:
            # Cancel the timed-out task to free worker
            if future and not future.done():
                future.cancel()
            
            logger.warning(
                f"Chip generation timeout ({self.TIMEOUT_SECONDS}s) "
                f"for session {self.session_id}"
            )
            with lock:
                data = _get_session_data(session_id, store)
                chip_state = data.get("chip_state", {})
                chip_state["failure_count"] = chip_state.get("failure_count", 0) + 1
                data["chip_state"] = chip_state
                _save_session_data(session_id, store, data)
            return None

        except Exception as e:
            logger.error(
                f"Chip generation failed for session {self.session_id}: {e}",
                exc_info=True,
            )
            with lock:
                data = _get_session_data(session_id, store)
                chip_state = data.get("chip_state", {})
                chip_state["failure_count"] = chip_state.get("failure_count", 0) + 1
                data["chip_state"] = chip_state
                _save_session_data(session_id, store, data)
            return None

    def _generate_chips_sync(
        self, context: ChipGenerationContext
    ) -> SuggestionChipSet | None:
        """
        Synchronous chip generation (runs in thread pool).

        Args:
            context: Generation context

        Returns:
            SuggestionChipSet or None on failure
        """
        try:
            # Build prompt
            prompt = self._build_chip_prompt(context)

            # Get model configuration
            model_config = get_model_config()
            model_version = model_config["model_version"]

            # Build the generation config for structured output
            generation_config = {
                "max_output_tokens": self.MAX_OUTPUT_TOKENS,
                "temperature": 0.7,
                "response_mime_type": "application/json",
                "response_schema": SuggestionChipSet.model_json_schema(),
            }

            # Call LLM with retry logic via centralized client
            response = call_gemini_api(
                prompt_content=[{"role": "user", "parts": [{"text": prompt}]}],
                config=generation_config,
            )

            # Parse and validate response
            response_text = response.text
            chip_set = SuggestionChipSet.model_validate_json(response_text)

            logger.info(
                f"Generated {len(chip_set.chips)} chips for session {self.session_id}"
            )
            return chip_set

        except ValidationError as e:
            logger.error(
                f"Chip validation failed for session {self.session_id}: {e}",
                exc_info=True,
            )
            return None

        except Exception as e:
            logger.error(
                f"LLM call failed for chip generation {self.session_id}: {e}",
                exc_info=True,
            )
            return None

    def _build_chip_prompt(self, context: ChipGenerationContext) -> str:
        """
        Build chip generation prompt from context.

        This prompt is designed for prefix invariant caching (static instructions
        at the beginning, dynamic context at the end). Enforces MAX_PROMPT_TOKENS
        by truncating conversation turns and recent messages.

        Args:
            context: Generation context

        Returns:
            Formatted prompt string
        """
        # Static instruction prefix (cacheable) - approximately 300 tokens
        system_instructions = """You are a suggestion chip generator for Maya, an AI bartending agent.

Your task is to generate 3-6 contextual suggestion chips that help users continue the conversation naturally.

**Chip Types:**
- **dialogue**: Conversational responses or questions (neutral color)
- **action**: System actions like payment, tips, menu (accent color)

**Guidelines:**
1. Keep text between 2-40 characters
2. Make chips relevant to the current conversation phase
3. Prioritize action chips when payment/order actions are pending
4. Avoid repeating recent user messages
5. Use natural, conversational language
6. Ensure diversity: mix of questions, statements, and actions

**Action IDs** (required for action chips):
- payment: Complete payment for current order
- tip: Add a tip
- menu: View drink menu
- cancel: Cancel current order
- order_another: Order another drink

**Example Output:**
{
  "chips": [
    {"text": "Tell me more", "type": "dialogue"},
    {"text": "Make it stronger", "type": "dialogue"},
    {"text": "Complete payment", "type": "action", "action_id": "payment"},
    {"text": "See menu", "type": "action", "action_id": "menu"}
  ]
}
"""

        # Estimate remaining token budget (MAX_PROMPT_TOKENS - static prefix)
        # Using rough estimate: 1 token ≈ 4 characters
        static_prefix_chars = len(system_instructions)
        static_prefix_tokens = static_prefix_chars // 4
        remaining_tokens = max(0, self.MAX_PROMPT_TOKENS - static_prefix_tokens)
        remaining_chars = remaining_tokens * 4

        # Build dynamic context with budget enforcement
        conversation_lines = []
        for turn in context.conversation_turns:
            line = f"{turn['role']}: {turn['content']}"
            conversation_lines.append(line)
        
        conversation_context = "\n".join(conversation_lines)
        
        # Truncate conversation context if needed
        if len(conversation_context) > remaining_chars * 0.7:  # Reserve 30% for other fields
            max_conv_chars = int(remaining_chars * 0.7)
            conversation_context = conversation_context[:max_conv_chars] + "..."

        recent_messages = (
            "\n".join(context.recent_user_messages)
            if context.recent_user_messages
            else "None"
        )
        
        # Truncate recent messages if needed
        max_recent_chars = int(remaining_chars * 0.2)
        if len(recent_messages) > max_recent_chars:
            recent_messages = recent_messages[:max_recent_chars] + "..."

        context_section = f"""
**Current Conversation:**
{conversation_context}

**Conversation Phase:** {context.conversation_phase}
**Payment Status:** {context.payment_status or "none"}
**Recent User Messages (do not repeat):**
{recent_messages}

Generate 3-6 suggestion chips now:"""

        return system_instructions + context_section

    def generate_fallback_chips(self) -> SuggestionChipSet:
        """
        Generate generic greeting chips when context is unavailable.

        Returns:
            Generic greeting chip set
        """
        return SuggestionChipSet(
            chips=[
                SuggestionChip(
                    text="Show me the menu",
                    type=ChipType.ACTION,
                    action_id=ActionID.MENU,
                ),
                SuggestionChip(
                    text="Surprise me", type=ChipType.DIALOGUE, action_id=None
                ),
                SuggestionChip(
                    text="What's popular?", type=ChipType.DIALOGUE, action_id=None
                ),
                SuggestionChip(
                    text="Something refreshing",
                    type=ChipType.DIALOGUE,
                    action_id=None,
                ),
            ]
        )
