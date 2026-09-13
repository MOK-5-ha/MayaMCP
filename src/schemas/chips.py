"""Pydantic v2 models for suggestion chips."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ChipType(StrEnum):
    """Chip type enumeration."""

    DIALOGUE = "dialogue"
    ACTION = "action"


class ActionID(StrEnum):
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


@dataclass
class ChipState:
    """Per-session chip state stored in session manager."""

    current_chips: SuggestionChipSet | None = None
    last_generation_time: float | None = None
    generation_count: int = 0
    failure_count: int = 0
    pending_task: Any | None = None
    generation_seq: int = 0
    pending_task_seq: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for session storage."""
        return {
            "chips": (
                [chip.model_dump() for chip in self.current_chips.chips]
                if self.current_chips and hasattr(self.current_chips, "chips")
                else []
            ),
            "last_generation_time": self.last_generation_time,
            "generation_count": self.generation_count,
            "failure_count": self.failure_count,
            "generation_seq": self.generation_seq,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChipState":
        """Deserialize from dictionary."""
        current_chips = None
        if "chips" in data and data["chips"]:
            current_chips = SuggestionChipSet(
                chips=[SuggestionChip(**c) for c in data["chips"]]
            )
        elif "current_chips" in data and data["current_chips"]:
            val = data["current_chips"]
            if isinstance(val, SuggestionChipSet):
                current_chips = val
            elif isinstance(val, dict):
                current_chips = SuggestionChipSet(**val)

        return cls(
            current_chips=current_chips,
            last_generation_time=data.get("last_generation_time"),
            generation_count=data.get("generation_count", 0),
            failure_count=data.get("failure_count", 0),
            pending_task=data.get("pending_task"),
            generation_seq=data.get("generation_seq", 0),
            pending_task_seq=data.get("pending_task_seq"),
        )

    @property
    def failure_rate(self) -> float:
        """Calculate chip generation failure rate (Requirement 8.6)."""
        total = self.generation_count + self.failure_count
        return (self.failure_count / total) if total > 0 else 0.0

