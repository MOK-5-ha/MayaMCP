"""Pydantic models for payment requests and responses."""


from pydantic import BaseModel, Field


class TipRequest(BaseModel):
    tip_percentage: int | None = Field(None, description="Tip percentage (e.g. 15, 20, 25)")
    tip_amount: float | None = Field(None, description="Explicit tip amount in dollars", ge=0.0)


class PaymentStateResponse(BaseModel):
    tab_amount: float = Field(0.0, description="Current accumulated tab amount")
    balance: float = Field(0.0, description="Remaining customer balance")
    tip_percentage: int | None = Field(None, description="Selected tip percentage")
    tip_amount: float = Field(0.0, description="Applied tip amount")
    status: str = Field("active", description="Payment tab status")
