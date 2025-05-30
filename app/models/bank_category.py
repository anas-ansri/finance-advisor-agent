from sqlalchemy import Boolean, Column, ForeignKey, String, Float, DateTime, Text, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from app.db.database import Base
from app.models.bank_transaction import TransactionCategoryEnum



class BankCategory(Base):
    """Transaction category model."""
    
    __tablename__ = "bank_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Enum(TransactionCategoryEnum), nullable=False)
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    transactions = relationship("BankTransaction", back_populates="category")
    expenses = relationship("Expense", back_populates="category")
