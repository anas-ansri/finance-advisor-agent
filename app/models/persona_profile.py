import uuid
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class PersonaProfile(Base):
    __tablename__ = "persona_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    
    persona_name = Column(String, nullable=False)
    persona_description = Column(String, nullable=False)
    key_traits = Column(JSON, nullable=True) # Will store a list of strings
    lifestyle_summary = Column(String, nullable=True)
    financial_tendencies = Column(String, nullable=True)
    
    # New fields for enhanced cultural persona
    cultural_profile = Column(JSON, nullable=True)  # Store music, film, fashion, dining preferences
    financial_advice_style = Column(String, nullable=True)  # How they prefer to receive advice
    
    # Store the raw JSON from Qloo for debugging and potential future use
    source_qloo_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="persona_profile")