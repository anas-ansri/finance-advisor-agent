from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class AIPreference(Base):
    """
    User preferences for AI interactions.
    """
    __tablename__ = "ai_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    preferred_model_id = Column(Integer, ForeignKey("ai_models.id"), nullable=True)
    system_prompt = Column(Text, nullable=True)
    temperature = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="ai_preferences")
    preferred_model = relationship("AIModel")
