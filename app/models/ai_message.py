from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base


class AIMessage(Base):
    """
    AI Message model for storing messages in AI conversations.
    """
    __tablename__ = "ai_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    content = Column(String, nullable=False)
    sender = Column(String, nullable=False)
    ai_metadata = Column(JSONB)
    
    # Relationships
    conversation = relationship("AIConversation", back_populates="messages") 