"""Pydantic models for payment requests and responses."""

from typing import Optional
from pydantic import BaseModel, Field


class TipRequest(BaseModel):
    tip_percentage: Optional[int] = Field(None, description="Tip percentage (e.g. 15, 20, 25)")
    tip_amount: Optional[float] = Field(None, description="Explicit tip amount in dollars", ge=0.0)


class PaymentStateResponse(BaseModel):
    tab_amount: float = Field(0.0, description="Current accumulated tab amount")
    balance: float = Field(0.0, description="Remaining customer balance")
    tip_percentage: Optional[int] = Field(None, description="Selected tip percentage")
    tip_amount: float = Field(0.0, description="Applied tip amount")
    status: str = Field("active", description="Payment tab status")
