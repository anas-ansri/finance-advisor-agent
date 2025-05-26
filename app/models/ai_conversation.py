from sqlalchemy import Column, DateTime, String, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base


class AIConversation(Base):
    """
    AI Conversation model for storing user's conversations with AI.
    """
    __tablename__ = "ai_conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    conversation_type = Column(String, nullable=False)
    title = Column(String)
    
    # Relationships
    user = relationship("User", back_populates="ai_conversations")
    messages = relationship("AIMessage", back_populates="conversation", cascade="all, delete-orphan")


# Import at the bottom to avoid circular imports
from app.models.ai_message import AIMessage 