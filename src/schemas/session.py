"""Pydantic models for session management requests and responses."""

from typing import Optional
from pydantic import BaseModel, Field


class KeySubmissionRequest(BaseModel):
    gemini_key: str = Field(..., description="Google Gemini AI Studio API key")
    cartesia_key: Optional[str] = Field(None, description="Optional Cartesia TTS API key")


class SessionStatusResponse(BaseModel):
    session_id: str = Field(..., description="Current session identifier")
    has_valid_keys: bool = Field(False, description="Whether valid Gemini API keys are configured")
    is_active: bool = Field(True, description="Session activity state")
