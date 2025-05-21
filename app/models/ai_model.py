from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, func

from app.db.database import Base


class AIModel(Base):
    """
    AI model configuration.
    """
    __tablename__ = "ai_models"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    provider = Column(String, nullable=False)  # e.g., 'openai', 'anthropic', 'local'
    model_id = Column(String, nullable=False)  # e.g., 'gpt-4o', 'claude-3-opus'
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    max_tokens = Column(Integer, nullable=True)
    temperature = Column(Float, default=0.7)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
