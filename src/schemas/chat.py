"""Pydantic models for chat requests and responses."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_input: str = Field(..., description="User input string sent to Maya")
    streaming: bool = Field(False, description="Whether to request SSE streaming response")
    avatar_path: str = Field("assets/bartender_avatar.jpg", description="Path to bartender avatar image")


class ChatResponse(BaseModel):
    response_text: str = Field(..., description="LLM response text")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Conversation history list")
    current_order: List[Dict[str, Any]] = Field(default_factory=list, description="Current drink order list")
    audio_base64: Optional[str] = Field(None, description="Optional base64 encoded audio string from TTS")
    payment_summary: Dict[str, Any] = Field(default_factory=dict, description="Current tab, balance, tip info")
    quota_error_html: Optional[str] = Field(None, description="HTML error message if quota exceeded")


class ChatStreamEvent(BaseModel):
    event_type: str = Field(..., description="Type of stream event: text_chunk, sentence, audio_chunk, complete, error")
    content: str = Field("", description="Text content or message")
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional payload metadata")
