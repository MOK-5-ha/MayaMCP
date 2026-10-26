"""Pydantic models for session management requests and responses."""


from pydantic import BaseModel, Field


class KeySubmissionRequest(BaseModel):
    gcp_project: str = Field(..., description="GCP project ID accessible to server ADC")
    cartesia_key: str | None = Field(None, description="Optional Cartesia TTS API key")


class SessionStatusResponse(BaseModel):
    session_id: str = Field(..., description="Current session identifier")
    has_valid_keys: bool = Field(False, description="Whether Vertex AI configuration is validated")
    is_active: bool = Field(True, description="Session activity state")
