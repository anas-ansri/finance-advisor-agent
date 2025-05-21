from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MessageBase(BaseModel):
    """
    Base message schema.
    """
    role: str = Field(..., description="Role of the message sender (user, assistant, system)")
    content: str = Field(..., description="Content of the message")


class MessageCreate(MessageBase):
    """
    Message creation schema.
    """
    pass


class Message(MessageBase):
    """
    Message schema for API responses.
    """
    id: int
    conversation_id: int
    created_at: datetime
    
    class Config:
        orm_mode = True


class ConversationBase(BaseModel):
    """
    Base conversation schema.
    """
    title: str = Field(..., description="Title of the conversation")


class ConversationCreate(ConversationBase):
    """
    Conversation creation schema.
    """
    messages: Optional[List[MessageCreate]] = Field(None, description="Initial messages in the conversation")


class ConversationUpdate(BaseModel):
    """
    Conversation update schema.
    """
    title: Optional[str] = Field(None, description="New title for the conversation")


class Conversation(ConversationBase):
    """
    Conversation schema for API responses.
    """
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    messages: List[Message] = []
    
    class Config:
        orm_mode = True


class ConversationList(BaseModel):
    """
    Schema for listing conversations.
    """
    conversations: List[Conversation]
    total: int
