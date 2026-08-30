"""Pydantic models for session management requests and responses."""


from pydantic import BaseModel, Field


class KeySubmissionRequest(BaseModel):
    gemini_key: str | None = Field(None, description="Optional GCP Project ID or session key override")
    cartesia_key: str | None = Field(None, description="Optional Cartesia TTS API key")


class SessionStatusResponse(BaseModel):
    session_id: str = Field(..., description="Current session identifier")
    has_valid_keys: bool = Field(False, description="Whether valid Gemini API keys are configured")
    is_active: bool = Field(True, description="Session activity state")
