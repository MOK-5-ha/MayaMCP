# Design Document: Suggestion Chips Feature

## Introduction

This document specifies the technical design for dynamic suggestion chips in MayaMCP. Suggestion chips are contextual, clickable UI elements that guide users toward relevant next actions or dialogue turns, generated in parallel with Maya's responses using a separate LLM call.

## Architecture Overview

### High-Level Component Structure

```
┌─────────────────────────────────────────────────────────────┐
│                        Gradio UI Layer                       │
│  ┌────────────────┐  ┌──────────────────────────────────┐  │
│  │  Chat Display  │  │  Suggestion Chips Component      │  │
│  │  (Textbox)     │  │  - ChipRow (scrollable)          │  │
│  │                │  │  - DialogueChip (neutral style)  │  │
│  │                │  │  - ActionChip (accent style)     │  │
│  └────────────────┘  └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   Conversation Manager                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Response Flow (Primary Thread)                      │  │
│  │  1. Receive user message                             │  │
│  │  2. Stream Maya response (non-blocking)              │  │
│  │  3. Trigger chip generation (parallel, non-blocking) │  │
│  │  4. Update UI with response + chips                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
┌───────────────────────────┐  ┌─────────────────────────────┐
│   Response Generator      │  │   Chip Generator            │
│   (Primary LLM)           │  │   (Parallel LLM)            │
│   - Full conversation     │  │   - Context extraction      │
│   - Streaming enabled     │  │   - Structured output       │
│   - Tools available       │  │   - 3s timeout              │
└───────────────────────────┘  └─────────────────────────────┘
                                            │
                                            ▼
                                ┌──────────────────────────┐
                                │  Chip Validation        │
                                │  (Pydantic v2 Schema)   │
                                │  - Type checking        │
                                │  - Length validation    │
                                │  - Action ID validation │
                                └──────────────────────────┘
                                            │
                                            ▼
                                ┌──────────────────────────┐
                                │  Session State Manager  │
                                │  (Thread-safe storage)  │
                                │  - Latest chip set      │
                                │  - Generation metadata  │
                                └──────────────────────────┘
```

### Execution Flow

1. **User Message Submission**: User sends message via Gradio UI, chips hide immediately
2. **Parallel Processing**:
   - **Primary Thread**: Maya's response generation streams to UI (blocking for user visibility)
   - **Background Thread**: Chip generation starts in parallel (non-blocking)
3. **Chip Generation**: 
   - Extract last 4 conversation turns + payment state
   - Call Gemini with structured output schema
   - Validate with Pydantic v2
   - Store in session state or return empty set on failure
4. **UI Update**: When both response and chips complete, update UI atomically

### Key Design Principles

- **Parallel Non-Blocking**: Chip generation never delays response stream
- **Graceful Degradation**: All failures result in empty chips, never error messages
- **Thread Safety**: Session state uses RLock for chip storage/retrieval
- **Timeout Enforcement**: 3-second hard timeout with ThreadPoolExecutor
- **Validation First**: Pydantic validates before storage, logging errors

## Data Models

### Pydantic v2 Schemas

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from enum import Enum

class ChipType(str, Enum):
    """Chip type enumeration."""
    DIALOGUE = "dialogue"
    ACTION = "action"

class ActionID(str, Enum):
    """Valid action identifiers for action chips."""
    PAYMENT = "payment"
    TIP = "tip"
    MENU = "menu"
    CANCEL = "cancel"
    ORDER_ANOTHER = "order_another"

class SuggestionChip(BaseModel):
    """Single suggestion chip model."""
    text: str = Field(
        ...,
        min_length=2,
        max_length=40,
        description="Chip display text"
    )
    type: ChipType = Field(
        ...,
        description="Chip type: dialogue or action"
    )
    action_id: Optional[ActionID] = Field(
        None,
        description="Action identifier for action chips"
    )
    
    @field_validator("action_id")
    @classmethod
    def validate_action_id(cls, v, info):
        """Ensure action_id is present for action chips."""
        chip_type = info.data.get("type")
        if chip_type == ChipType.ACTION and v is None:
            raise ValueError("action_id required for action chips")
        if chip_type == ChipType.DIALOGUE and v is not None:
            raise ValueError("action_id not allowed for dialogue chips")
        return v

class SuggestionChipSet(BaseModel):
    """Collection of suggestion chips returned by LLM."""
    chips: list[SuggestionChip] = Field(
        ...,
        min_length=3,
        max_length=6,
        description="List of 3-6 suggestion chips"
    )
    
    @field_validator("chips")
    @classmethod
    def validate_unique_text(cls, v):
        """Ensure chip texts are unique within set."""
        texts = [chip.text.lower() for chip in v]
        if len(texts) != len(set(texts)):
            raise ValueError("Chip texts must be unique")
        return v

class ChipGenerationContext(BaseModel):
    """Context passed to chip generator."""
    conversation_turns: list[dict[str, str]] = Field(
        ...,
        max_length=4,
        description="Last 4 conversation turns"
    )
    payment_status: Optional[str] = Field(
        None,
        description="Current payment status: pending, completed, failed, none"
    )
    conversation_phase: str = Field(
        ...,
        description="Current phase: greeting, ordering, describing, payment, complete"
    )
    recent_user_messages: list[str] = Field(
        default_factory=list,
        max_length=2,
        description="Last 2 user messages for deduplication"
    )
```

### Session State Schema

```python
@dataclass
class ChipState:
    """Per-session chip state stored in session manager."""
    current_chips: Optional[SuggestionChipSet] = None
    last_generation_time: Optional[float] = None
    generation_count: int = 0
    failure_count: int = 0
    pending_task: Optional[Future] = None
    
    def to_dict(self) -> dict:
        """Serialize for session storage."""
        return {
            "chips": [chip.model_dump() for chip in self.current_chips.chips] if self.current_chips else [],
            "last_generation_time": self.last_generation_time,
            "generation_count": self.generation_count,
            "failure_count": self.failure_count,
        }
```

## Component Implementation

### 1. Chip Generator (`src/conversation/chip_generator.py`)

```python
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Optional
import google.generativeai as genai
from pydantic import ValidationError

from src.llm.client import get_genai_client
from src.schemas.chips import SuggestionChipSet, ChipGenerationContext
from src.utils.state_manager import get_session_state

logger = logging.getLogger(__name__)

# Global thread pool for chip generation (max 10 concurrent per instance)
_chip_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="chip_gen")

class ChipGenerator:
    """Generates contextual suggestion chips using LLM structured output."""
    
    TIMEOUT_SECONDS = 3.0
    RATE_LIMIT_SECONDS = 2.0
    MAX_PROMPT_TOKENS = 512
    MAX_OUTPUT_TOKENS = 200
    
    def __init__(self, session_id: str, llm_client: Optional[genai.Client] = None):
        """
        Initialize chip generator.
        
        Args:
            session_id: Current session identifier
            llm_client: Optional LLM client for dependency injection (testing)
        """
        self.session_id = session_id
        self.llm_client = llm_client or get_genai_client(session_id)
        self._cache = {}  # Context representation cache
    
    def generate_chips_async(self, context: ChipGenerationContext) -> Optional[SuggestionChipSet]:
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
        # Check rate limit
        session_state = get_session_state(self.session_id)
        chip_state = session_state.get("chip_state", {})
        last_gen_time = chip_state.get("last_generation_time", 0)
        
        import time
        current_time = time.time()
        if current_time - last_gen_time < self.RATE_LIMIT_SECONDS:
            logger.warning(
                f"Rate limit exceeded for session {self.session_id}, "
                f"skipping chip generation"
            )
            return None
        
        # Cancel pending task if exists
        pending_task = chip_state.get("pending_task")
        if pending_task and not pending_task.done():
            logger.info(f"Cancelling pending chip generation for {self.session_id}")
            pending_task.cancel()
        
        # Submit generation task
        try:
            future = _chip_executor.submit(self._generate_chips_sync, context)
            
            # Store pending task
            chip_state["pending_task"] = future
            session_state["chip_state"] = chip_state
            
            # Wait with timeout
            result = future.result(timeout=self.TIMEOUT_SECONDS)
            
            # Update metadata
            chip_state["last_generation_time"] = current_time
            chip_state["generation_count"] = chip_state.get("generation_count", 0) + 1
            session_state["chip_state"] = chip_state
            
            return result
            
        except FutureTimeoutError:
            logger.warning(
                f"Chip generation timeout ({self.TIMEOUT_SECONDS}s) "
                f"for session {self.session_id}"
            )
            chip_state["failure_count"] = chip_state.get("failure_count", 0) + 1
            session_state["chip_state"] = chip_state
            return None
            
        except Exception as e:
            logger.error(
                f"Chip generation failed for session {self.session_id}: {e}",
                exc_info=True
            )
            chip_state["failure_count"] = chip_state.get("failure_count", 0) + 1
            session_state["chip_state"] = chip_state
            return None
    
    def _generate_chips_sync(self, context: ChipGenerationContext) -> Optional[SuggestionChipSet]:
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
            
            # Call LLM with structured output
            model = self.llm_client.models.generate_content(
                model=get_model_config()["model_version"],
                contents=prompt,
                config={
                    "max_output_tokens": self.MAX_OUTPUT_TOKENS,
                    "temperature": 0.7,
                    "response_mime_type": "application/json",
                    "response_schema": SuggestionChipSet.model_json_schema(),
                }
            )
            
            # Parse and validate response
            response_text = model.text
            chip_set = SuggestionChipSet.model_validate_json(response_text)
            
            logger.info(
                f"Generated {len(chip_set.chips)} chips for session {self.session_id}"
            )
            return chip_set
            
        except ValidationError as e:
            logger.error(
                f"Chip validation failed for session {self.session_id}: {e}",
                exc_info=True
            )
            return None
            
        except Exception as e:
            logger.error(
                f"LLM call failed for chip generation {self.session_id}: {e}",
                exc_info=True
            )
            return None
    
    def _build_chip_prompt(self, context: ChipGenerationContext) -> str:
        """
        Build chip generation prompt from context.
        
        This prompt is designed for prefix invariant caching (static instructions
        at the beginning, dynamic context at the end).
        
        Args:
            context: Generation context
            
        Returns:
            Formatted prompt string
        """
        # Static instruction prefix (cacheable)
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
        
        # Dynamic context (not cacheable, but small)
        conversation_context = "\n".join([
            f"{turn['role']}: {turn['content']}"
            for turn in context.conversation_turns
        ])
        
        recent_messages = "\n".join(context.recent_user_messages) if context.recent_user_messages else "None"
        
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
                SuggestionChip(text="Show me the menu", type=ChipType.ACTION, action_id=ActionID.MENU),
                SuggestionChip(text="Surprise me", type=ChipType.DIALOGUE),
                SuggestionChip(text="What's popular?", type=ChipType.DIALOGUE),
                SuggestionChip(text="Something refreshing", type=ChipType.DIALOGUE),
            ]
        )
```

### 2. Conversation Manager Integration (`src/conversation/processor.py`)

```python
def process_user_message(session_id: str, user_message: str) -> Iterator[str]:
    """
    Process user message and stream Maya's response with parallel chip generation.
    
    Args:
        session_id: Current session ID
        user_message: User's input message
        
    Yields:
        Response text chunks (streaming)
    """
    from src.conversation.chip_generator import ChipGenerator
    from src.schemas.chips import ChipGenerationContext
    
    # 1. Stream Maya's response (primary thread, blocking for user)
    response_chunks = []
    for chunk in generate_maya_response_stream(session_id, user_message):
        response_chunks.append(chunk)
        yield chunk
    
    # 2. After response completes, trigger chip generation (non-blocking)
    full_response = "".join(response_chunks)
    
    # Extract context for chip generation
    session_state = get_session_state(session_id)
    conversation_history = session_state.get("conversation_history", [])
    
    # Get last 4 turns
    last_turns = conversation_history[-4:] if len(conversation_history) >= 4 else conversation_history
    
    # Determine conversation phase
    phase = determine_conversation_phase(session_state, full_response)
    
    # Get payment status
    payment_status = session_state.get("payment", {}).get("status", "none")
    
    # Get recent user messages for deduplication
    recent_user_messages = [
        turn["content"] for turn in conversation_history[-2:]
        if turn["role"] == "user"
    ]
    
    context = ChipGenerationContext(
        conversation_turns=last_turns,
        payment_status=payment_status,
        conversation_phase=phase,
        recent_user_messages=recent_user_messages
    )
    
    # Generate chips asynchronously (non-blocking)
    chip_gen = ChipGenerator(session_id)
    
    # If no conversation history, use fallback
    if not conversation_history:
        chip_set = chip_gen.generate_fallback_chips()
    else:
        chip_set = chip_gen.generate_chips_async(context)
    
    # Store chips in session state
    if chip_set:
        chip_state = session_state.get("chip_state", {})
        chip_state["current_chips"] = chip_set
        session_state["chip_state"] = chip_state
        logger.info(f"Stored {len(chip_set.chips)} chips for session {session_id}")
    else:
        logger.info(f"No chips generated for session {session_id}")


def determine_conversation_phase(session_state: dict, latest_response: str) -> str:
    """
    Determine current conversation phase from state and response.
    
    Args:
        session_state: Current session state
        latest_response: Maya's latest response
        
    Returns:
        Phase identifier: greeting, ordering, describing, payment, complete
    """
    conversation_history = session_state.get("conversation_history", [])
    payment_status = session_state.get("payment", {}).get("status", "none")
    
    # Payment phase
    if payment_status in ["pending", "processing"]:
        return "payment"
    if payment_status == "completed":
        return "complete"
    
    # Check response content for phase indicators
    latest_lower = latest_response.lower()
    
    if any(greeting in latest_lower for greeting in ["hello", "hi", "welcome", "good to see you"]):
        return "greeting"
    
    if any(desc in latest_lower for desc in ["recipe", "ingredients", "made with", "contains"]):
        return "describing"
    
    if any(order in latest_lower for order in ["order", "prepare", "make you", "coming right up"]):
        return "ordering"
    
    # Default to greeting if early in conversation
    if len(conversation_history) < 3:
        return "greeting"
    
    return "ordering"
```

### 3. Gradio UI Components (`src/ui/chips.py`)

```python
import gradio as gr
from typing import Optional, Callable
from src.schemas.chips import SuggestionChipSet, ChipType, ActionID
from src.utils.state_manager import get_session_state

# Chip styling constants
DIALOGUE_CHIP_STYLE = """
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 20px;
    padding: 10px 20px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
    min-height: 44px;
    min-width: 44px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
"""

ACTION_CHIP_STYLE = """
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    color: white;
    border: none;
    border-radius: 20px;
    padding: 10px 20px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
    min-height: 44px;
    min-width: 44px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    font-weight: 600;
"""

CHIP_HOVER_STYLE = """
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
"""

CHIP_FOCUS_STYLE = """
    outline: 2px solid #4299e1;
    outline-offset: 2px;
"""

# Action icons (emoji prefixes)
ACTION_ICONS = {
    ActionID.PAYMENT: "💳 ",
    ActionID.TIP: "💰 ",
    ActionID.MENU: "📋 ",
    ActionID.CANCEL: "❌ ",
    ActionID.ORDER_ANOTHER: "🍹 ",
}


def create_chip_row(session_id: str) -> gr.Row:
    """
    Create suggestion chips row component.
    
    Args:
        session_id: Current session ID
        
    Returns:
        Gradio Row component with chip buttons
    """
    with gr.Row(
        visible=False,
        elem_id="suggestion-chips-row",
        elem_classes=["chip-container"]
    ) as chip_row:
        # Placeholder for dynamic chip buttons
        chip_buttons = []
        for i in range(6):  # Max 6 chips
            btn = gr.Button(
                "",
                visible=False,
                elem_id=f"chip-{i}",
                elem_classes=["suggestion-chip"],
                size="sm",
            )
            chip_buttons.append(btn)
    
    return chip_row, chip_buttons


def update_chips(session_id: str, chip_buttons: list[gr.Button]) -> list[gr.Button]:
    """
    Update chip buttons with latest chip set from session state.
    
    Args:
        session_id: Current session ID
        chip_buttons: List of Gradio button components
        
    Returns:
        Updated button components
    """
    session_state = get_session_state(session_id)
    chip_state = session_state.get("chip_state", {})
    chip_set = chip_state.get("current_chips")
    
    if not chip_set or not chip_set.chips:
        # Hide all chips
        return [gr.Button(visible=False) for _ in chip_buttons]
    
    updates = []
    for i, chip_btn in enumerate(chip_buttons):
        if i < len(chip_set.chips):
            chip = chip_set.chips[i]
            
            # Add icon for action chips
            display_text = chip.text
            if chip.type == ChipType.ACTION and chip.action_id:
                icon = ACTION_ICONS.get(chip.action_id, "")
                display_text = f"{icon}{chip.text}"
            
            # Select style based on type
            style = ACTION_CHIP_STYLE if chip.type == ChipType.ACTION else DIALOGUE_CHIP_STYLE
            
            # ARIA label for accessibility
            aria_label = f"{chip.type.value} chip: {chip.text}"
            
            updates.append(
                gr.Button(
                    value=display_text,
                    visible=True,
                    elem_classes=[
                        "suggestion-chip",
                        f"chip-{chip.type.value}"
                    ],
                    variant="primary" if chip.type == ChipType.ACTION else "secondary",
                    # Store chip data in elem_id for click handler
                    elem_id=f"chip-{i}-{chip.type.value}-{chip.action_id if chip.action_id else 'none'}"
                )
            )
        else:
            updates.append(gr.Button(visible=False))
    
    return updates


def handle_chip_click(
    chip_text: str,
    chip_type: str,
    action_id: Optional[str],
    session_id: str,
    textbox: gr.Textbox
) -> tuple[str, Optional[str]]:
    """
    Handle chip button click.
    
    Args:
        chip_text: Clicked chip text
        chip_type: Chip type (dialogue or action)
        action_id: Action ID if action chip
        session_id: Current session ID
        textbox: Gradio textbox component
        
    Returns:
        Tuple of (textbox_value, submit_trigger)
            - textbox_value: Text to populate in input
            - submit_trigger: "submit" if auto-submit, None otherwise
    """
    # Remove icon prefix if present
    clean_text = chip_text
    for icon in ACTION_ICONS.values():
        if chip_text.startswith(icon):
            clean_text = chip_text[len(icon):]
            break
    
    # Validate action_id if action chip
    if chip_type == ChipType.ACTION:
        if action_id and action_id not in [a.value for a in ActionID]:
            # Unrecognized action_id, treat as dialogue
            logger.warning(f"Unrecognized action_id '{action_id}', treating as dialogue")
            return clean_text, None
        
        # Auto-submit for valid action chips
        return clean_text, "submit"
    
    # Dialogue chip: populate but don't submit
    return clean_text, None


def register_chip_handlers(
    chip_buttons: list[gr.Button],
    textbox: gr.Textbox,
    submit_btn: gr.Button,
    session_id: str
) -> None:
    """
    Register click handlers for chip buttons.
    
    Args:
        chip_buttons: List of chip button components
        textbox: Input textbox component
        submit_btn: Submit button component
        session_id: Current session ID
    """
    for i, chip_btn in enumerate(chip_buttons):
        chip_btn.click(
            fn=lambda text, elem_id, sid=session_id: handle_chip_click(
                chip_text=text,
                chip_type=elem_id.split("-")[2],  # Extract from elem_id
                action_id=elem_id.split("-")[3] if elem_id.split("-")[3] != "none" else None,
                session_id=sid,
                textbox=textbox
            ),
            inputs=[chip_btn, chip_btn],  # value and elem_id
            outputs=[textbox, submit_btn],
            show_progress=False,
        )


# CSS for chip styling and accessibility
CHIP_CSS = """
.chip-container {
    display: flex;
    flex-direction: row;
    gap: 8px;
    overflow-x: auto;
    overflow-y: hidden;
    padding: 12px 0;
    scroll-behavior: smooth;
    -webkit-overflow-scrolling: touch;
}

.chip-container::-webkit-scrollbar {
    height: 6px;
}

.chip-container::-webkit-scrollbar-track {
    background: rgba(0,0,0,0.05);
    border-radius: 3px;
}

.chip-container::-webkit-scrollbar-thumb {
    background: rgba(0,0,0,0.2);
    border-radius: 3px;
}

.chip-container::-webkit-scrollbar-thumb:hover {
    background: rgba(0,0,0,0.3);
}

.suggestion-chip {
    flex-shrink: 0;
    white-space: nowrap;
    transition: all 0.2s ease;
}

.suggestion-chip:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
}

.suggestion-chip:focus {
    outline: 2px solid #4299e1 !important;
    outline-offset: 2px;
}

.chip-dialogue {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
}

.chip-action {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
    font-weight: 600 !important;
}

/* Mobile responsive */
@media (max-width: 768px) {
    .chip-container {
        padding: 8px 0;
    }
    
    .suggestion-chip {
        min-height: 44px;
        min-width: 44px;
        font-size: 13px;
    }
}

/* Accessibility - high contrast mode */
@media (prefers-contrast: high) {
    .suggestion-chip {
        border: 2px solid currentColor !important;
    }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
    .suggestion-chip {
        transition: none !important;
    }
    
    .suggestion-chip:hover {
        transform: none !important;
    }
}

/* ARIA live region for screen readers */
.chip-updates[aria-live="polite"] {
    position: absolute;
    left: -10000px;
    width: 1px;
    height: 1px;
    overflow: hidden;
}
```

## LLM Prompt Engineering

### Chip Generation Prompt Structure

The chip generation prompt is designed with **prefix invariant caching** in mind for GCP Context Caching:

1. **Static Prefix** (cacheable, ~300 tokens):
   - System role definition
   - Chip type explanations
   - Guidelines and constraints
   - Action ID registry
   - Example output format

2. **Dynamic Suffix** (not cached, ~100-200 tokens):
   - Last 4 conversation turns
   - Current conversation phase
   - Payment status
   - Recent user messages for deduplication

This structure allows Google's LLM to cache the instruction portion across requests, significantly reducing latency and token costs.

### Prompt Optimization Strategies

- **Token Budget**: Max 512 tokens input (instruction + context)
- **Output Constraint**: Max 200 tokens (5-6 chips with metadata)
- **Temperature**: 0.7 for balanced creativity and consistency
- **Structured Output**: JSON schema validation via `response_schema` parameter
- **Deduplication**: Explicit instruction to avoid recent user messages

### Example Prompt

```
You are a suggestion chip generator for Maya, an AI bartending agent.

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

**Current Conversation:**
user: Hey Maya, what do you recommend?
assistant: I'd recommend our signature Old Fashioned! It's a classic with bourbon, bitters, sugar, and a twist of orange.
user: That sounds good. I'll take one.
assistant: Great choice! I'll prepare your Old Fashioned right away. That'll be $12.

**Conversation Phase:** payment
**Payment Status:** pending
**Recent User Messages (do not repeat):**
That sounds good. I'll take one.

Generate 3-6 suggestion chips now:
```

## Integration Points

### 1. Conversation Manager

**File**: `src/conversation/processor.py`

**Integration**:
- Import `ChipGenerator` and `ChipGenerationContext`
- After response stream completes, extract context and trigger chip generation
- Store result in session state under `chip_state` key
- Handle empty results gracefully (no user-facing errors)

### 2. Session State Manager

**File**: `src/utils/state_manager.py`

**New State Fields**:
```python
{
    "chip_state": {
        "current_chips": SuggestionChipSet | None,
        "last_generation_time": float | None,
        "generation_count": int,
        "failure_count": int,
        "pending_task": Future | None
    }
}
```

**Thread Safety**: All chip state updates must acquire session RLock before modification.

### 3. Gradio UI

**File**: `src/ui/chat_interface.py`

**Integration**:
- Import `create_chip_row`, `update_chips`, `register_chip_handlers`
- Add chip row component below chat display
- Register chip click handlers with textbox and submit button
- Update chips after each Maya response completes
- Hide chips when user submits new message

### 4. LLM Client

**File**: `src/llm/client.py`

**Usage**: ChipGenerator reuses existing `get_genai_client(session_id)` to obtain Gemini client from session registry. No new client instances are created.

## Error Handling and Fallback Strategies

### Error Categories

1. **Timeout (3s exceeded)**:
   - Log warning with session ID
   - Return empty chip set
   - Increment failure counter
   - Continue conversation normally

2. **Validation Error (Pydantic)**:
   - Log validation errors with full context
   - Return empty chip set
   - Increment failure counter
   - Track validation failure metrics

3. **LLM Call Error (API failure)**:
   - Log exception with stack trace
   - Return empty chip set
   - Increment failure counter
   - Track API failure metrics

4. **Missing Context (no conversation history)**:
   - Generate fallback greeting chips
   - Log fallback usage
   - Do not increment failure counter

5. **Rate Limit Exceeded**:
   - Skip generation silently
   - Log rate limit hit
   - Do not increment failure counter

### Graceful Degradation Principles

- **Never Block**: Chip generation failures never prevent response delivery
- **Silent Failures**: No user-facing error messages for chip issues
- **Metrics Tracking**: Log all failure modes for monitoring
- **Fallback Content**: Provide generic greeting chips when context unavailable
- **Resource Protection**: Rate limiting and concurrency limits prevent resource exhaustion

## Performance Considerations

### Optimization Strategies

1. **Parallel Execution**: Chip generation runs in background thread pool, never blocks response stream
2. **Timeout Enforcement**: Hard 3-second timeout prevents hanging
3. **Context Caching**: Conversation context representation cached to reduce memory allocations
4. **Token Budget**: Strict 512-token input limit prevents excessive prompt costs
5. **Output Limit**: 200-token maximum output reduces generation time
6. **Rate Limiting**: 1 request per 2 seconds per session prevents spam
7. **Concurrency Limit**: Max 10 concurrent chip generations across all sessions
8. **Client Reuse**: Existing Gemini client from session state (no new connections)
9. **Prefix Caching**: Static instruction prefix cacheable for reduced latency

### Performance Targets

- **Chip Generation Latency**: <2 seconds (p95), <3 seconds (max)
- **Response Stream Impact**: 0ms blocking time
- **Memory Overhead**: <1MB per session for chip state
- **Token Usage**: <512 input tokens, <200 output tokens per generation
- **Failure Rate**: <5% under normal load

## Testing Strategy

### Unit Tests

- **Schema Validation**: Test Pydantic models with valid/invalid inputs
- **Chip Generator**: Mock LLM client, test prompt building and response parsing
- **Context Extraction**: Test conversation phase detection and context building
- **Error Handling**: Inject failures and verify graceful degradation
- **Fallback Chips**: Test generation when context unavailable

### Integration Tests

- **End-to-End Flow**: Test complete user message → response → chips flow
- **Session State**: Test chip storage/retrieval with thread safety
- **UI Updates**: Test chip button creation and click handling
- **Parallel Execution**: Verify chip generation doesn't block response
- **Rate Limiting**: Test enforcement of 1 per 2s limit
- **Timeout**: Test 3-second timeout enforcement

### Property-Based Tests

See **Correctness Properties** section below for universal properties to validate.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Non-blocking Parallel Execution

*For any* conversation context, chip generation SHALL complete independently of the response stream, such that measuring response completion time with and without chip generation shows no significant difference (within measurement error tolerance).

**Validates: Requirements 1.1, 7.4**

### Property 2: Timeout Enforcement

*For any* chip generation request, the result SHALL arrive within 3 seconds or return an empty chip set, ensuring no chip generation blocks indefinitely.

**Validates: Requirements 1.4**

### Property 3: Schema Conformance

*For any* successful chip generation output, the returned data SHALL conform to the SuggestionChipSet Pydantic schema, with all validation constraints satisfied (3-6 chips, 2-40 character text, valid types and action_ids).

**Validates: Requirements 1.3, 2.1, 2.2, 2.3, 2.4, 2.6**

### Property 4: Graceful Failure Degradation

*For any* chip generation failure (timeout, validation error, LLM error), the system SHALL log the error and return an empty chip set without displaying user-facing error messages or blocking the conversation flow.

**Validates: Requirements 1.5, 2.5, 8.1, 8.2, 8.3, 8.5**

### Property 5: Context Acceptance

*For any* valid ChipGenerationContext with conversation history, the ChipGenerator SHALL accept it without errors and attempt generation.

**Validates: Requirements 1.2**

### Property 6: Model Configuration Compliance

*For any* session state with a configured Gemini model, the ChipGenerator SHALL use that exact model instance for chip generation without creating new client connections.

**Validates: Requirements 1.6, 10.4**

### Property 7: Action ID Validation

*For any* action chip with an action_id field, the value SHALL be present in the ActionID enum registry, and validation SHALL reject unrecognized values.

**Validates: Requirements 11.5**

### Property 8: Action ID Fallback Behavior

*For any* action chip with an unrecognized action_id, the system SHALL treat it as a dialogue chip (populate input without auto-submit) rather than failing.

**Validates: Requirements 11.6**

### Property 9: Chip Text Uniqueness

*For any* generated chip set, all chip texts SHALL be unique (case-insensitive comparison) within that set.

**Validates: Requirements 2.1** (implicit uniqueness constraint)

### Property 10: Deduplication of Recent Messages

*For any* chip generation with recent user messages in context, the generated chips SHALL not match (case-insensitive) any of the last 2 user messages.

**Validates: Requirements 3.5**

### Property 11: Conversation Phase Context Inclusion

*For any* chip generation request from the Conversation Manager, the context SHALL include the current conversation phase and payment status.

**Validates: Requirements 7.2, 7.3**

### Property 12: Last 4 Turns Context Window

*For any* chip generation with conversation history, the context SHALL include exactly the last 4 conversation turns (or all turns if fewer than 4 exist).

**Validates: Requirements 7.2**

### Property 13: State Storage Atomicity

*For any* successful chip generation, the chip set SHALL be stored in session state under the `chip_state` key, and retrieval SHALL return the most recently stored set.

**Validates: Requirements 6.3**

### Property 14: Empty Set Display Suppression

*For any* empty chip set (None or zero chips), the UI SHALL not display any chip buttons, ensuring visual cleanliness.

**Validates: Requirements 6.4**

### Property 15: Session Cleanup

*For any* session reset or termination event, the chip state SHALL be cleared from session storage.

**Validates: Requirements 6.5**

### Property 16: Chip Visibility Lifecycle

*For any* user message submission, the current chip set SHALL hide immediately, and new chips SHALL only display after Maya's response completes.

**Validates: Requirements 6.2, 6.1**

### Property 17: Click Handler Input Population

*For any* chip button click (dialogue or action), the input textbox SHALL be cleared first, then populated with the chip text (without icon prefix).

**Validates: Requirements 5.1, 5.4**

### Property 18: Dialogue Chip Focus Behavior

*For any* dialogue chip click, the input textbox SHALL receive focus after population, allowing immediate user editing.

**Validates: Requirements 5.2**

### Property 19: Action Chip Auto-Submit

*For any* action chip click with a valid action_id, the system SHALL auto-submit the populated text without requiring additional user action.

**Validates: Requirements 5.3**

### Property 20: Visual Style Differentiation

*For any* rendered chip, dialogue chips SHALL apply neutral gradient styling and action chips SHALL apply accent gradient styling, ensuring visual distinction.

**Validates: Requirements 4.1, 4.2**

### Property 21: Icon Prefix for Action Chips

*For any* rendered action chip with a recognized action_id, the display text SHALL include the corresponding icon prefix from the ACTION_ICONS registry.

**Validates: Requirements 4.5**

### Property 22: Minimum Contrast Ratio

*For any* chip color scheme (dialogue or action), the contrast ratio between text and background SHALL be at least 4.5:1 for WCAG AA accessibility compliance.

**Validates: Requirements 4.6**

### Property 23: ARIA Label Presence

*For any* rendered chip button, an ARIA label SHALL be present indicating chip type and text for screen reader accessibility.

**Validates: Requirements 9.1**

### Property 24: Keyboard Navigation Support

*For any* chip button, keyboard focus SHALL be supported, and Enter or Space keys SHALL activate the chip (equivalent to click).

**Validates: Requirements 9.2, 5.6**

### Property 25: ARIA Live Region Announcements

*For any* chip set update, the change SHALL be announced to screen readers via an ARIA live region.

**Validates: Requirements 9.3**

### Property 26: Responsive Scaling

*For any* viewport width (mobile or desktop), chip buttons SHALL scale appropriately and maintain horizontal scrollability without vertical overflow.

**Validates: Requirements 9.4**

### Property 27: Minimum Touch Target Size

*For any* rendered chip button on mobile viewports, the touch target SHALL be at least 44x44 pixels for accessibility.

**Validates: Requirements 9.5**

### Property 28: Focus Indicator Visibility

*For any* focused chip button, a visual focus indicator with minimum 2px outline SHALL be displayed.

**Validates: Requirements 9.6**

### Property 29: Token Budget Compliance

*For any* chip generation prompt, the total token count SHALL not exceed 512 tokens, and the LLM output request SHALL not exceed 200 tokens.

**Validates: Requirements 10.1, 10.2**

### Property 30: Rate Limit Enforcement

*For any* session, chip generation requests SHALL be rate-limited to at most 1 request per 2 seconds, with violations resulting in skipped generation.

**Validates: Requirements 10.6**

### Property 31: Concurrency Limit Enforcement

*For any* time window across all sessions, at most 10 chip generation tasks SHALL execute concurrently in the thread pool.

**Validates: Requirements 10.5**

### Property 32: Pending Task Cancellation

*For any* session with a pending chip generation task, if a new user message arrives, the pending task SHALL be cancelled before starting new chip generation.

**Validates: Requirements 7.5**

### Property 33: Timing Metrics Logging

*For any* chip generation attempt, timing metrics (start time, end time, duration) SHALL be logged for performance monitoring.

**Validates: Requirements 7.6**

### Property 34: Failure Rate Tracking

*For any* chip generation attempt, success or failure SHALL be tracked, and the failure rate SHALL be exposed as a system health metric.

**Validates: Requirements 8.6**

### Property 35: Fallback Greeting Chips

*For any* chip generation request with missing or empty conversation history, the system SHALL generate and return a predefined set of generic greeting chips.

**Validates: Requirements 8.4**

### Property 36: Context-Aware Chip Content (Order Completion)

*For any* conversation context where Maya completes a drink order, the generated chip set SHALL include at least one action chip with action_id "payment" or "order_another".

**Validates: Requirements 3.1**

### Property 37: Context-Aware Chip Content (Drink Description)

*For any* conversation context where Maya describes a drink, the generated chip set SHALL include at least two dialogue chips suitable for follow-up questions.

**Validates: Requirements 3.2**

### Property 38: Context-Aware Chip Content (Greeting Phase)

*For any* conversation context in the greeting phase, the generated chip set SHALL include at least one dialogue chip related to menu inquiries or drink preferences.

**Validates: Requirements 3.3**

### Property 39: Context-Aware Chip Content (Payment Pending)

*For any* conversation context with payment status "pending", the generated chip set SHALL include at least one action chip with action_id "payment" or "cancel".

**Validates: Requirements 3.4**

### Property 40: Action Routing (Payment)

*For any* action chip click with action_id "payment", the system SHALL route to the payment flow.

**Validates: Requirements 11.1**

### Property 41: Action Routing (Tip)

*For any* action chip click with action_id "tip", the system SHALL route to the tip selection interface.

**Validates: Requirements 11.2**

### Property 42: Action Routing (Menu)

*For any* action chip click with action_id "menu", the system SHALL display the drink menu.

**Validates: Requirements 11.3**

### Property 43: Action Routing (Cancel)

*For any* action chip click with action_id "cancel", the system SHALL cancel the current order and reset session payment state.

**Validates: Requirements 11.4**

### Property 44: Dependency Injection Support

*For any* ChipGenerator instantiation with a mock LLM client parameter, the generator SHALL use the provided client instead of creating a new one.

**Validates: Requirements 12.2**

### Property 45: Test Mode Determinism

*For any* chip generation in test mode, the output SHALL be deterministic and reproducible for the same input context.

**Validates: Requirements 12.3**

### Property 46: Hover State Visual Feedback

*For any* chip button hover event, the chip SHALL apply hover styling (elevation, shadow) as visual feedback.

**Validates: Requirements 5.5**

### Property 47: Persistence Across UI Refreshes

*For any* UI component refresh within the same conversation turn, the current chip set SHALL persist and remain displayed.

**Validates: Requirements 6.6**

## Deployment Considerations

### Environment Variables

No new environment variables required. ChipGenerator uses existing configuration:
- `GCP_PROJECT`: Google Cloud project for Vertex AI
- `GCP_LOCATION`: Vertex AI location
- `GEMINI_MODEL_VERSION`: Model version for chip generation

### Resource Requirements

- **Thread Pool**: 10 worker threads for chip generation (shared across all sessions)
- **Memory**: ~1MB per active session for chip state
- **CPU**: Minimal impact (parallel execution, short-lived tasks)
- **Network**: Reuses existing Gemini client connections

### Monitoring Metrics

- `chip_generation_total`: Total chip generation attempts
- `chip_generation_success`: Successful generations
- `chip_generation_timeout`: Timeout failures
- `chip_generation_validation_error`: Validation failures
- `chip_generation_llm_error`: LLM call failures
- `chip_generation_latency_ms`: Generation latency histogram
- `chip_failure_rate`: Rolling failure rate percentage

### Logging

All chip generation events logged at appropriate levels:
- `INFO`: Successful generation with chip count
- `WARNING`: Timeout, rate limit exceeded
- `ERROR`: Validation errors, LLM errors (with stack trace)

## Security Considerations

### Input Validation

- **Context Sanitization**: Conversation turns validated by Pydantic before passing to LLM
- **Token Limits**: Strict input token budget (512) prevents prompt injection via context overflow
- **Schema Enforcement**: Pydantic v2 validates all outputs before storage

### Output Sanitization

- **Text Length**: 2-40 character limit prevents UI overflow
- **Type Validation**: Only "dialogue" or "action" types allowed
- **Action ID Registry**: Closed set of valid action_ids prevents injection

### Privacy

- **No Data Persistence**: Chips stored only in ephemeral session state
- **Context Window**: Only last 4 turns sent to LLM (minimal conversation exposure)
- **Session Isolation**: Chip state isolated per session (no cross-contamination)

## Future Enhancements

### Phase 2 Considerations

1. **Personalization**: User preference learning for chip content
2. **A/B Testing**: Experiment with chip generation prompt variations
3. **Analytics**: Click-through rates and chip effectiveness metrics
4. **Multi-language**: Localized chip text for international users
5. **Adaptive Chip Count**: Dynamic 3-6 range based on viewport width
6. **Custom Actions**: Developer-defined action registry via configuration
7. **Chip Animations**: Smooth transitions when chips update

## Conclusion

This design provides a comprehensive, production-ready architecture for dynamic suggestion chips in MayaMCP. The parallel execution model ensures zero latency impact on response streaming, while Pydantic v2 validation guarantees type-safe, well-formed chip data. Graceful degradation and thread-safe state management ensure robustness in production environments.

The correctness properties defined above provide a complete specification for property-based testing, ensuring comprehensive coverage of all functional requirements and edge cases.

## BDD Acceptance Testing

### Overview

This specification includes comprehensive Behavior-Driven Development (BDD) acceptance tests using pytest-bdd with Gherkin scenarios. BDD tests provide executable acceptance criteria that bridge the gap between requirements, design, and implementation, allowing product stakeholders and developers to validate system behavior using natural language scenarios.

### Purpose

- **Traceability**: Each scenario maps directly to specific requirements for full requirements coverage
- **Executable Documentation**: Gherkin scenarios serve as living documentation that stays synchronized with the codebase
- **Stakeholder Communication**: Non-technical stakeholders can read and validate scenarios
- **Regression Prevention**: Comprehensive scenario coverage prevents behavioral regressions during refactoring

### Test File Location

- **Feature File**: `tests/behavior/features/suggestion_chips.feature`
- **Step Definitions**: `tests/behavior/test_suggestion_chips.py`
- **Execution**: Run with `pytest -m bdd` or alongside full test suite with `pytest`

### Scenario Coverage

The BDD test suite covers the following user-facing behaviors:

1. **Greeting Phase Chip Generation**
   - Verifies menu inquiry chips appear in greeting phase
   - Validates chip text contains menu-related suggestions
   - Ensures fallback chips render when conversation history is empty

2. **Ordering Phase Chip Generation**
   - Validates payment and order_another action chips after order completion
   - Ensures chip set prioritizes payment action when order is pending

3. **Payment Pending Phase**
   - Verifies payment action chip appears with high priority
   - Validates cancel action chip availability
   - Ensures chip text reflects payment context

4. **Drink Description Phase**
   - Validates follow-up dialogue chips after drink description
   - Ensures chip text prompts additional questions or clarifications

5. **Chip Deduplication**
   - Validates generated chips do not match recent user messages (last 2)
   - Tests case-insensitive deduplication

6. **Action Chip Auto-Submit**
   - Verifies action chips populate textbox and auto-submit
   - Validates routing to payment, tip, menu, cancel, order_another flows

7. **Dialogue Chip Focus Behavior**
   - Verifies dialogue chips populate textbox without auto-submit
   - Validates input receives focus after click for immediate editing

8. **Graceful Degradation on LLM Timeout/Failure**
   - Validates empty chip set renders when generation times out (>3s)
   - Ensures conversation continues normally without user-visible errors
   - Verifies fallback chips render when LLM validation fails

9. **Keyboard Navigation and Accessibility**
   - Validates Tab key navigation through chips
   - Verifies Enter and Space keys activate chips
   - Ensures focus indicators are visible (2px outline)
   - Validates ARIA labels for screen readers

10. **Session Reset Clears Chips**
    - Verifies chip state is cleared on session reset
    - Ensures no stale chips persist across sessions

### Sample Gherkin Scenarios

Below are representative examples from the full feature file. See `tests/behavior/features/suggestion_chips.feature` for the complete scenario suite.

```gherkin
Feature: Suggestion Chips for Contextual User Guidance

  As a MayaMCP user
  I want to see contextual suggestion chips after Maya's responses
  So that I can continue the conversation naturally with one-click actions

  Background:
    Given a new Maya session is created
    And the chip generator is initialized

  Scenario: Greeting phase generates menu inquiry chips
    Given the conversation is in the "greeting" phase
    When Maya responds with a greeting message
    And chip generation completes successfully
    Then suggestion chips should be visible
    And at least one chip should contain "menu" related text
    And chip count should be between 3 and 6

  Scenario: Order completion generates payment action chip
    Given the conversation is in the "ordering" phase
    And Maya completes a drink order with price "$12"
    When chip generation completes successfully
    Then suggestion chips should be visible
    And at least one chip should be an action chip with action_id "payment"
    And the payment chip text should contain "payment" or "pay"

  Scenario: Payment pending prioritizes payment action chip
    Given the conversation is in the "payment" phase
    And payment status is "pending"
    When chip generation completes successfully
    Then suggestion chips should be visible
    And the first chip should be an action chip with action_id "payment"
    And at least one chip should be an action chip with action_id "cancel"

  Scenario: Drink description generates follow-up dialogue chips
    Given the conversation is in the "describing" phase
    And Maya describes a drink with ingredients
    When chip generation completes successfully
    Then suggestion chips should be visible
    And at least 2 chips should be dialogue chips
    And dialogue chip text should prompt follow-up questions

  Scenario: Chips are deduplicated against recent user messages
    Given the user has sent messages: "Tell me more", "What's in it?"
    When chip generation completes successfully
    Then suggestion chips should be visible
    And no chip text should match "Tell me more" (case-insensitive)
    And no chip text should match "What's in it?" (case-insensitive)

  Scenario: Action chip auto-submits on click
    Given suggestion chips are visible
    And a chip with action_id "payment" is present
    When the user clicks the payment action chip
    Then the textbox should contain the chip text (without icon prefix)
    And the message should be auto-submitted
    And the conversation should route to payment flow

  Scenario: Dialogue chip populates textbox without auto-submit
    Given suggestion chips are visible
    And a dialogue chip with text "Tell me more" is present
    When the user clicks the dialogue chip
    Then the textbox should contain "Tell me more"
    And the textbox should have focus
    And the message should NOT be auto-submitted

  Scenario: Graceful degradation when LLM generation times out
    Given the LLM call will exceed 3 seconds
    When chip generation is triggered
    Then chip generation should timeout after 3 seconds
    And an empty chip set should be returned
    And no chips should be visible in the UI
    And the conversation should continue normally
    And a timeout warning should be logged

  Scenario: Graceful degradation when LLM validation fails
    Given the LLM returns invalid JSON for chip generation
    When chip generation is triggered
    Then Pydantic validation should fail
    And an empty chip set should be returned
    And no chips should be visible in the UI
    And a validation error should be logged

  Scenario: Keyboard navigation through chips
    Given suggestion chips are visible with 5 chips
    When the user presses Tab repeatedly
    Then focus should cycle through all 5 chips
    And each focused chip should display a focus indicator (2px outline)

  Scenario: Enter key activates focused chip
    Given suggestion chips are visible
    And the first chip (dialogue) is focused
    When the user presses Enter
    Then the chip should activate (populate textbox)
    And the behavior should match a click event

  Scenario: Space key activates focused chip
    Given suggestion chips are visible
    And the second chip (action) is focused
    When the user presses Space
    Then the chip should activate (populate and auto-submit)
    And the behavior should match a click event

  Scenario: ARIA labels announce chip type and text
    Given suggestion chips are visible
    And a dialogue chip with text "Surprise me" is present
    When a screen reader queries the chip
    Then the ARIA label should be "dialogue chip: Surprise me"

  Scenario: Session reset clears chip state
    Given suggestion chips are visible with 4 chips
    And chip_state contains current_chips data
    When the user resets the session
    Then chip_state should be empty
    And no chips should be visible in the UI

  Scenario: Chips persist across UI refreshes within same turn
    Given suggestion chips are visible with 6 chips
    When the UI component refreshes (without new user message)
    Then the same 6 chips should remain visible
    And chip content should be unchanged

  Scenario: Chips hide when user submits new message
    Given suggestion chips are visible with 5 chips
    When the user submits a new message
    Then chips should hide immediately
    And chips should remain hidden until Maya responds

  Scenario: Empty conversation history generates fallback chips
    Given the conversation history is empty
    When chip generation is triggered
    Then fallback greeting chips should be returned
    And fallback chips should include "Show me the menu" action chip
    And fallback chips should include "Surprise me" dialogue chip

  Scenario: Rate limit prevents rapid chip generation
    Given chip generation completed 1 second ago
    When chip generation is triggered again
    Then generation should be skipped (rate limit)
    And a rate limit warning should be logged
    And no new chips should be generated

  Scenario: Pending task cancellation when new message arrives
    Given chip generation is in progress (pending)
    When the user submits a new message
    Then the pending chip generation task should be cancelled
    And new chip generation should start for the new turn
```

### Implementation Notes

#### Step Definitions

Step definitions in `tests/behavior/test_suggestion_chips.py` will:

1. **Reuse Existing Fixtures**: Leverage `conftest.py` fixtures for session state, mock LLM client, and chip generator instances
2. **Mock External Dependencies**: Use standard mocking patterns from unit tests for Gemini API calls
3. **Shared State Management**: Use pytest-bdd context sharing to pass data between Given/When/Then steps
4. **Assertion Helpers**: Import assertion utilities from existing test modules for DRY principles

Example step definition structure:

```python
import pytest
from pytest_bdd import given, when, then, scenario, parsers

from src.conversation.chip_generator import ChipGenerator
from src.schemas.chips import ChipGenerationContext, SuggestionChipSet

# Scenario registration
@scenario('../features/suggestion_chips.feature', 'Greeting phase generates menu inquiry chips')
def test_greeting_phase_chips():
    pass

# Step definitions
@given('a new Maya session is created')
def create_session(mock_session_state):
    """Set up clean session state for BDD test."""
    mock_session_state.clear()
    return "test_session_123"

@given('the conversation is in the "greeting" phase')
def set_greeting_phase(mock_session_state):
    """Configure session state for greeting phase."""
    mock_session_state["conversation_history"] = []
    mock_session_state["payment"] = {"status": "none"}

@when('Maya responds with a greeting message')
def maya_greeting_response(mock_session_state):
    """Simulate Maya greeting response."""
    mock_session_state["conversation_history"].append({
        "role": "assistant",
        "content": "Hello! Welcome to Maya's Bar. What can I get you?"
    })

@when('chip generation completes successfully')
def generate_chips(mock_chip_generator, mock_session_state):
    """Trigger chip generation with mocked LLM."""
    context = ChipGenerationContext(
        conversation_turns=mock_session_state["conversation_history"],
        payment_status="none",
        conversation_phase="greeting",
        recent_user_messages=[]
    )
    chip_set = mock_chip_generator.generate_chips_async(context)
    mock_session_state["chip_state"] = {"current_chips": chip_set}

@then('suggestion chips should be visible')
def assert_chips_visible(mock_session_state):
    """Verify chips are present in session state."""
    chip_set = mock_session_state["chip_state"]["current_chips"]
    assert chip_set is not None
    assert len(chip_set.chips) > 0

@then(parsers.parse('chip count should be between {min:d} and {max:d}'))
def assert_chip_count_range(mock_session_state, min, max):
    """Verify chip count falls within valid range."""
    chip_set = mock_session_state["chip_state"]["current_chips"]
    assert min <= len(chip_set.chips) <= max
```

#### Integration with CI/CD

BDD tests run alongside the standard pytest suite:

```bash
# Run all tests (including BDD)
pytest

# Run only BDD tests
pytest -m bdd

# Run BDD with coverage
pytest -m bdd --cov=src/conversation --cov=src/schemas --cov=src/ui

# Generate BDD report
pytest --gherkin-terminal-reporter
```

#### Traceability Matrix

Each scenario includes inline requirement references via comments:

```gherkin
# Requirements: 3.3, 3.6, 8.4
Scenario: Greeting phase generates menu inquiry chips
  ...
```

This ensures full traceability from requirements → design → implementation → acceptance tests.

### Benefits

1. **Living Documentation**: Scenarios stay synchronized with codebase, never going stale
2. **Stakeholder Validation**: Product owners can review and approve scenarios before implementation
3. **Regression Safety**: Comprehensive coverage prevents behavioral regressions during refactoring
4. **Onboarding**: New developers understand feature behavior through natural language scenarios
5. **Requirements Validation**: Ensures all requirements have corresponding acceptance tests

### Maintenance

- **Update scenarios when requirements change**: Treat Gherkin as first-class specification artifact
- **Keep step definitions DRY**: Reuse fixtures and assertion helpers across scenarios
- **Run BDD tests in CI**: Ensure no PR merges without passing acceptance tests
- **Review scenario coverage during design reviews**: Validate completeness before implementation

