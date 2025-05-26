from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base


class AIPreference(Base):
    """
    User preferences for AI interactions.
    """
    __tablename__ = "ai_preferences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    preferred_model_id = Column(Integer, ForeignKey("ai_models.id"), nullable=True)
    system_prompt = Column(Text, nullable=True)
    temperature = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="ai_preferences")
    preferred_model = relationship("AIModel")


# Import at the bottom to avoid circular imports
from app.models.ai_model import AIModel
