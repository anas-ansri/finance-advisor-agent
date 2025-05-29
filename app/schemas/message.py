from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """
    Schema for creating a new message in a conversation.
    """
    role: str = Field(..., description="Role of the message sender (user, assistant, system)")
    content: str = Field(..., description="Content of the message")


class ChatMessage(BaseModel):
    """
    Chat message schema for AI interactions.
    """
    role: str = Field(..., description="Role of the message sender (user, assistant, system)")
    content: str = Field(..., description="Content of the message")


class ChatRequest(BaseModel):
    """
    Chat request schema for AI interactions.
    """
    conversation_id: Optional[UUID] = Field(None, description="ID of the existing conversation")
    messages: List[ChatMessage] = Field(..., description="Messages in the conversation")
    model_id: Optional[int] = Field(None, description="ID of the AI model to use")
    temperature: Optional[float] = Field(None, description="Temperature parameter for generation")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")
    stream: bool = Field(False, description="Whether to stream the response")


class ChatResponse(BaseModel):
    """
    Chat response schema for AI interactions.
    """
    conversation_id: UUID
    message: ChatMessage
