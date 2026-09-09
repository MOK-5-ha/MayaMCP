"""Pydantic v2 models for suggestion chips."""

from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


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

    text: str = Field(..., min_length=2, max_length=40, description="Chip display text")
    type: ChipType = Field(..., description="Chip type: dialogue or action")
    action_id: ActionID | None = Field(
        None, description="Action identifier for action chips"
    )

    @model_validator(mode="after")
    def validate_action_id(self):
        """Ensure action_id is present for action chips and absent for dialogue chips."""
        if self.type == ChipType.ACTION and self.action_id is None:
            raise ValueError("action_id required for action chips")
        if self.type == ChipType.DIALOGUE and self.action_id is not None:
            raise ValueError("action_id not allowed for dialogue chips")
        return self


class SuggestionChipSet(BaseModel):
    """Collection of suggestion chips returned by LLM."""

    chips: list[SuggestionChip] = Field(
        ..., min_length=3, max_length=6, description="List of 3-6 suggestion chips"
    )

    @field_validator("chips")
    @classmethod
    def validate_unique_text(cls, v):
        """Ensure chip texts are unique within set (case-insensitive)."""
        texts = [chip.text.lower() for chip in v]
        if len(texts) != len(set(texts)):
            raise ValueError("Chip texts must be unique")
        return v


class ChipGenerationContext(BaseModel):
    """Context passed to chip generator."""

    conversation_turns: list[dict[str, str]] = Field(
        ..., max_length=4, description="Last 4 conversation turns"
    )
    payment_status: str | None = Field(
        None,
        description="Current payment status: pending, completed, failed, none",
    )
    conversation_phase: str = Field(
        ...,
        description="Current phase: greeting, ordering, describing, payment, complete",
    )
    recent_user_messages: list[str] = Field(
        default_factory=list,
        max_length=2,
        description="Last 2 user messages for deduplication",
    )
