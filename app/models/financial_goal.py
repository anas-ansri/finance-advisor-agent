from sqlalchemy import Column, DateTime, String, Numeric, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base


class FinancialGoal(Base):
    """
    Financial Goal model for storing user's financial goals.
    """
    __tablename__ = "financial_goals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    target = Column(Numeric, nullable=False)
    current = Column(Numeric, server_default="0", nullable=False)
    color = Column(String, server_default="bg-primary", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="financial_goals") 