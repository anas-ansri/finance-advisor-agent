from sqlalchemy import Boolean, Column, DateTime, String, func, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base


class AIInsight(Base):
    """
    AI Insight model for storing AI-generated insights for users.
    """
    __tablename__ = "ai_insights"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False)
    is_read = Column(Boolean, server_default="false")
    is_active = Column(Boolean, server_default="true", nullable=False)
    priority = Column(Integer, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="insights") 