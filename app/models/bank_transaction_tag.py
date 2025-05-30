
# app/models/bank_statement.py
from sqlalchemy import Boolean, Column, ForeignKey, String, Float, DateTime, Text, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from app.db.database import Base



class BankTransactionTag(Base):
    """Association table for Transaction-Tag many-to-many relationship."""
    
    __tablename__ = "bank_transaction_tags"
    
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("bank_transactions.id"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("bank_tags.id"), primary_key=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
