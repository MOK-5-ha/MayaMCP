"""Chip generation for contextual suggestion chips.

Thread Pool Cancellation Limitation:
    ChipGenerator uses ThreadPoolExecutor for parallel chip generation. Python's
    ThreadPoolExecutor does not support canceling running threads. When a timeout
    occurs (3s), Future.cancel() prevents the caller from waiting further, but the
    background thread continues executing until the LLM call completes or retry
    logic exhausts (~30s with tenacity). This is acceptable because:

    1. Most timeouts are due to slow network/API, not aggressive timeout
    2. Worker pool is sized (10 threads) to handle occasional slow requests
    3. True cancellation would require asyncio (breaking change) or cooperative
       cancellation (requires modifying google-genai SDK)

    Session-Scoped Clients:
    ChipGenerator accepts an optional llm_client in __init__ for dependency
    injection (primarily for testing). When None, it uses get_genai_client()
    which returns the global Vertex AI client. The system does NOT pass
    per-session clients to ChipGenerator; all sessions share the global client.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any

from google import genai
from pydantic import ValidationError

from ..config.logging_config import get_logger
from ..llm.client import call_gemini_api, get_genai_client
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


def create_mock_chip_context(
    phase: str = "greeting",
    payment_status: str | None = None,
    turns: list[dict[str, str]] | None = None,
    recent_user_messages: list[str] | None = None,
) -> ChipGenerationContext:
    """
    Factory creating a valid ChipGenerationContext for testing and validation (Requirement 12.1, 12.5).

    Args:
        phase: Current conversation phase
        payment_status: Optional payment status
        turns: Optional list of turn dictionaries (max 4)
        recent_user_messages: Optional list of recent user message strings (max 2)

    Returns:
        Validated ChipGenerationContext instance
    """
    if turns is None:
        turns = [
            {"role": "user", "content": "Hello Maya!"},
            {"role": "assistant", "content": "Welcome to the bar! What can I get for you?"},
        ]
    if recent_user_messages is None:
        recent_user_messages = ["Hello Maya!"]

    return ChipGenerationContext(
        conversation_turns=turns[:4],
        payment_status=payment_status,
        conversation_phase=phase,
        recent_user_messages=recent_user_messages[:2],
    )


class ChipGenerator:
    """Generates contextual suggestion chips using LLM structured output."""

    TIMEOUT_SECONDS = 3.0
    RATE_LIMIT_SECONDS = 2.0
    MAX_PROMPT_TOKENS = 512
    MAX_OUTPUT_TOKENS = 200

    def __init__(
        self,
        session_id: str,
        llm_client: genai.Client | None = None,
        test_mode: bool = False,
    ):
        """
        Initialize chip generator.

        Args:
            session_id: Current session identifier
            llm_client: Optional LLM client for dependency injection (testing)
            test_mode: Optional boolean flag to enable deterministic test generation
        """
        self.session_id = session_id
        self.llm_client = llm_client or get_genai_client()
        self.test_mode = test_mode
        self._cache: dict[Any, Any] = {}  # Context representation cache

    def generate_chips_async(
        self,
        context: ChipGenerationContext,
        generation_seq: int | None = None,
    ) -> SuggestionChipSet | None:
        """
        Generate chips asynchronously with timeout.

        This method submits chip generation to a background thread pool
        and enforces a 3-second timeout. If generation exceeds timeout
        or fails, returns None (empty chip set).

        Args:
            context: Chip generation context with conversation history
            generation_seq: Optional sequence token to prevent superseded tasks from
                           cancelling or rate-limiting newer generations.

        Returns:
            SuggestionChipSet or None on timeout/failure
        """
        # Import here to avoid circular dependency
        from ..utils.state_manager import (
            _get_session_data,
            _get_store_and_session,
            _save_session_data,
            get_chip_generation_seq,
            get_session_lock,
        )

        session_id, store = _get_store_and_session(self.session_id, None)
        lock = get_session_lock(session_id)

        current_time = time.time()
        future = None

        # Atomically check freshness, rate limit, cancel pending task, and submit new task
        with lock:
            data = _get_session_data(session_id, store)
            chip_state = data.get("chip_state", {})

            # Snapshot or verify generation sequence token
            latest_seq = get_chip_generation_seq(session_id, store)
            if generation_seq is None:
                generation_seq = latest_seq
            elif generation_seq < latest_seq:
                logger.info(
                    f"Skipping superseded chip generation for session {session_id} "
                    f"(task seq {generation_seq} < latest seq {latest_seq})"
                )
                return None

            last_gen_time = chip_state.get("last_generation_time") or 0.0
            if current_time - last_gen_time < self.RATE_LIMIT_SECONDS:
                logger.warning(
                    f"Rate limit exceeded for session {self.session_id}, "
                    f"skipping chip generation"
                )
                return None

            # Cancel pending task if exists (only if pending task is not newer)
            pending_task = chip_state.get("pending_task")
            if pending_task and not pending_task.done():
                pending_seq = chip_state.get("pending_task_seq")
                if generation_seq is not None and pending_seq is not None and pending_seq > generation_seq:
                    logger.info(
                        f"Not cancelling pending task with newer seq {pending_seq} > {generation_seq}"
                    )
                    return None
                logger.info(
                    f"Cancelling pending chip generation for {self.session_id}"
                )
                pending_task.cancel()

            # Submit generation task and store it atomically
            future = _chip_executor.submit(self._generate_chips_sync, context)
            chip_state["pending_task"] = future
            chip_state["pending_task_seq"] = generation_seq
            data["chip_state"] = chip_state
            _save_session_data(session_id, store, data)

        start_time = time.time()
        # Wait with timeout
        try:
            result = future.result(timeout=self.TIMEOUT_SECONDS)
            end_time = time.time()
            duration = end_time - start_time

            # Update metadata
            with lock:
                latest_seq = get_chip_generation_seq(session_id, store)
                if generation_seq is not None and generation_seq < latest_seq:
                    logger.info(
                        f"Discarding stale completion metadata for session {self.session_id} "
                        f"(seq {generation_seq} < latest seq {latest_seq})"
                    )
                    return None

                data = _get_session_data(session_id, store)
                chip_state = data.get("chip_state", {})
                chip_state["last_generation_time"] = current_time
                if result is not None:
                    chip_state["generation_count"] = (
                        chip_state.get("generation_count", 0) + 1
                    )
                    logger.info(
                        f"Chip generation succeeded for session {self.session_id} in {duration:.3f}s "
                        f"(start={start_time:.3f}, end={end_time:.3f}, chips={len(result.chips)})"
                    )
                else:
                    chip_state["failure_count"] = (
                        chip_state.get("failure_count", 0) + 1
                    )
                    logger.warning(
                        f"Chip generation returned empty/None for session {self.session_id} in {duration:.3f}s "
                        f"(start={start_time:.3f}, end={end_time:.3f})"
                    )
                chip_state["pending_task"] = None
                data["chip_state"] = chip_state
                _save_session_data(session_id, store, data)

            return result

        except FutureTimeoutError:
            end_time = time.time()
            duration = end_time - start_time
            # Note: Future.cancel() only prevents awaiting the result; it cannot
            # stop a running thread. The background thread continues executing until
            # the LLM call completes or the retry logic exhausts (up to ~30s with
            # tenacity's 3 retries + exponential backoff). This is a limitation of
            # Python's ThreadPoolExecutor.
            #
            # In practice, most timeouts occur due to slow network/API, not the 3s
            # timeout being too aggressive. The worker pool (10 threads) is sized to
            # handle occasional slow requests without exhaustion.
            if future and not future.done():
                future.cancel()  # Prevents awaiting, but thread continues

            logger.warning(
                f"Chip generation timeout ({self.TIMEOUT_SECONDS}s) "
                f"for session {self.session_id} in {duration:.3f}s "
                f"(start={start_time:.3f}, end={end_time:.3f})"
            )
            with lock:
                latest_seq = get_chip_generation_seq(session_id, store)
                if generation_seq is not None and generation_seq < latest_seq:
                    logger.info(
                        f"Discarding stale timeout metadata for session {self.session_id} "
                        f"(seq {generation_seq} < latest seq {latest_seq})"
                    )
                    return None

                data = _get_session_data(session_id, store)
                chip_state = data.get("chip_state", {})
                chip_state["last_generation_time"] = current_time
                chip_state["failure_count"] = chip_state.get("failure_count", 0) + 1
                chip_state["pending_task"] = None
                data["chip_state"] = chip_state
                _save_session_data(session_id, store, data)
            return None

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            logger.error(
                f"Chip generation failed for session {self.session_id} in {duration:.3f}s "
                f"(start={start_time:.3f}, end={end_time:.3f}): {e}",
                exc_info=True,
            )
            with lock:
                latest_seq = get_chip_generation_seq(session_id, store)
                if generation_seq is not None and generation_seq < latest_seq:
                    logger.info(
                        f"Discarding stale error metadata for session {self.session_id} "
                        f"(seq {generation_seq} < latest seq {latest_seq})"
                    )
                    return None

                data = _get_session_data(session_id, store)
                chip_state = data.get("chip_state", {})
                chip_state["last_generation_time"] = current_time
                chip_state["failure_count"] = chip_state.get("failure_count", 0) + 1
                chip_state["pending_task"] = None
                data["chip_state"] = chip_state
                _save_session_data(session_id, store, data)
            return None

    def _generate_deterministic_chips(
        self, context: ChipGenerationContext
    ) -> SuggestionChipSet:
        """
        Generate deterministic chips for test mode (Requirement 12.3, Property 45).

        Args:
            context: Generation context

        Returns:
            Deterministic SuggestionChipSet tailored to phase and status
        """
        phase = context.conversation_phase
        status = context.payment_status

        if status == "pending" or phase == "payment":
            if status == "pending":
                return SuggestionChipSet(
                    chips=[
                        SuggestionChip(text="Complete payment", type=ChipType.ACTION, action_id=ActionID.PAYMENT),
                        SuggestionChip(text="Cancel order", type=ChipType.ACTION, action_id=ActionID.CANCEL),
                        SuggestionChip(text="Add a tip", type=ChipType.ACTION, action_id=ActionID.TIP),
                    ]
                )
            return SuggestionChipSet(
                chips=[
                    SuggestionChip(text="Add a tip", type=ChipType.ACTION, action_id=ActionID.TIP),
                    SuggestionChip(text="Order another drink", type=ChipType.ACTION, action_id=ActionID.ORDER_ANOTHER),
                    SuggestionChip(text="Show me the menu", type=ChipType.ACTION, action_id=ActionID.MENU),
                ]
            )

        if phase == "ordering":
            return SuggestionChipSet(
                chips=[
                    SuggestionChip(text="Complete payment", type=ChipType.ACTION, action_id=ActionID.PAYMENT),
                    SuggestionChip(text="Order another drink", type=ChipType.ACTION, action_id=ActionID.ORDER_ANOTHER),
                    SuggestionChip(text="Make it stronger", type=ChipType.DIALOGUE, action_id=None),
                    SuggestionChip(text="Extra ice please", type=ChipType.DIALOGUE, action_id=None),
                ]
            )

        if phase == "describing":
            return SuggestionChipSet(
                chips=[
                    SuggestionChip(text="What's in it?", type=ChipType.DIALOGUE, action_id=None),
                    SuggestionChip(text="Can I substitute bourbon?", type=ChipType.DIALOGUE, action_id=None),
                    SuggestionChip(text="How sweet is it?", type=ChipType.DIALOGUE, action_id=None),
                    SuggestionChip(text="I'll take one", type=ChipType.DIALOGUE, action_id=None),
                ]
            )

        if phase == "complete":
            return SuggestionChipSet(
                chips=[
                    SuggestionChip(text="Order another drink", type=ChipType.ACTION, action_id=ActionID.ORDER_ANOTHER),
                    SuggestionChip(text="Thank you!", type=ChipType.DIALOGUE, action_id=None),
                    SuggestionChip(text="Show me the menu", type=ChipType.ACTION, action_id=ActionID.MENU),
                ]
            )

        # Default / greeting phase
        return SuggestionChipSet(
            chips=[
                SuggestionChip(text="Show me the menu", type=ChipType.ACTION, action_id=ActionID.MENU),
                SuggestionChip(text="Surprise me", type=ChipType.DIALOGUE, action_id=None),
                SuggestionChip(text="What's popular?", type=ChipType.DIALOGUE, action_id=None),
                SuggestionChip(text="Something refreshing", type=ChipType.DIALOGUE, action_id=None),
            ]
        )

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
            logger.debug(
                f"Chip generation starting for session {self.session_id}: "
                f"phase={context.conversation_phase}, payment_status={context.payment_status}, "
                f"turns={len(context.conversation_turns)}, recent_msgs={len(context.recent_user_messages)}"
            )
            logger.debug(f"Chip generation context: {context.model_dump()}")

            if self.test_mode:
                deterministic_chips = self._generate_deterministic_chips(context)
                logger.debug(
                    f"[TEST MODE] Generated deterministic chips for session {self.session_id}: "
                    f"{deterministic_chips.model_dump()}"
                )
                return deterministic_chips

            # Build prompt
            prompt = self._build_chip_prompt(context)

            # Build the generation config for structured output
            generation_config = {
                "max_output_tokens": self.MAX_OUTPUT_TOKENS,
                "temperature": 0.7,
                "response_mime_type": "application/json",
                "response_schema": SuggestionChipSet.model_json_schema(),
            }

            # Call LLM via centralized client wrapper
            response = call_gemini_api(
                prompt_content=[{"role": "user", "parts": [{"text": prompt}]}],
                config=generation_config,
                client=self.llm_client,
            )

            # Parse and validate response
            response_text = getattr(response, "text", "")
            try:
                chip_set = SuggestionChipSet.model_validate_json(response_text)
            except ValidationError as val_err:
                is_json_parse_err = any(
                    "json_invalid" in str(err.get("type", ""))
                    for err in val_err.errors()
                )
                if is_json_parse_err:
                    logger.error(
                        f"Chip JSON parsing error for session {self.session_id}: {val_err}",
                        exc_info=True,
                    )
                else:
                    logger.error(
                        f"Chip validation failed for session {self.session_id}: {val_err}",
                        exc_info=True,
                    )
                return None
            except Exception as parse_err:
                logger.error(
                    f"Chip JSON parsing error for session {self.session_id}: {parse_err}",
                    exc_info=True,
                )
                return None

            logger.debug(
                f"Chip generation result for session {self.session_id}: "
                f"{chip_set.model_dump() if chip_set else None}"
            )
            logger.info(
                f"Generated {len(chip_set.chips)} chips for session {self.session_id}"
            )
            return chip_set

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

        Includes context-aware phase-specific instructions to prioritize relevant
        chips based on conversation phase and payment status.

        Args:
            context: Generation context

        Returns:
            Formatted prompt string
        """
        # Context representation caching (Requirement 10.3)
        cache_key = (
            context.conversation_phase,
            context.payment_status,
            tuple(
                (t.get("role", ""), t.get("content", ""))
                for t in context.conversation_turns
            ),
            tuple(context.recent_user_messages),
        )
        if cache_key in self._cache:
            logger.debug(f"Context cache hit for session {self.session_id}")
            return self._cache[cache_key]

        # Static instruction prefix (cacheable) - approximately 270 tokens
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

        # Add phase-specific guidance to dynamic context
        phase_guidance = self._get_phase_specific_guidance(
            context.conversation_phase, context.payment_status
        )

        context_section = f"""
**Current Conversation:**
{conversation_context}

**Conversation Phase:** {context.conversation_phase}
**Payment Status:** {context.payment_status or "none"}
**Recent User Messages (do not repeat):**
{recent_messages}

**Current Phase Guidance:**
{phase_guidance}

Generate 3-6 suggestion chips now:"""

        full_prompt = system_instructions + context_section
        max_allowed_chars = self.MAX_PROMPT_TOKENS * 4
        if len(full_prompt) > max_allowed_chars:
            full_prompt = full_prompt[:max_allowed_chars]

        if len(self._cache) >= 50:
            self._cache.pop(next(iter(self._cache)))
        self._cache[cache_key] = full_prompt

        return full_prompt

    def _get_phase_specific_guidance(
        self, phase: str, payment_status: str | None
    ) -> str:
        """
        Get phase-specific guidance for chip generation.

        Args:
            phase: Current conversation phase
            payment_status: Current payment status

        Returns:
            Phase-specific guidance string
        """
        guidance_map = {
            "greeting": "Focus on menu exploration and drink preferences. Include at least one menu-related option.",
            "ordering": "After order completion, prioritize payment and order_another action chips. Include customization options.",
            "describing": "Generate follow-up dialogue chips for drink details. Include at least 2 dialogue chips with questions about ingredients or taste.",
            "payment": "Prioritize payment action chip as first option when payment is pending. Include cancel option.",
            "complete": "Offer order_another action chip and thank-you dialogue options.",
        }

        base_guidance = guidance_map.get(
            phase, "Generate contextually relevant chips for current conversation."
        )

        # Add payment-specific guidance if payment is pending
        if payment_status == "pending":
            base_guidance += " URGENT: Payment is pending - place payment action chip first."

        return base_guidance

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
