# app/models/bank_statement.py
from sqlalchemy import Boolean, Column, ForeignKey, String, Float, DateTime, Text, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.database import Base
from app.models.bank_transaction import BankTransaction

class BankStatement(Base):
    """Bank statement model."""
    
    __tablename__ = "bank_statements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="statements")
    bank_transactions = relationship("BankTransaction", back_populates="statement", cascade="all, delete-orphan")
    statement_metadata = relationship("BankStatementMetadata", back_populates="statement", uselist=False, cascade="all, delete-orphan")

