from sqlalchemy import Boolean, Column, DateTime, String, Numeric, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base


class Transaction(Base):
    """
    Transaction model for storing user's financial transactions.
    """
    __tablename__ = "transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))
    description = Column(String, nullable=False)
    amount = Column(Numeric, nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    is_recurring = Column(Boolean, server_default="false", nullable=False)
    notes = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    tags = relationship("Tag", secondary="transaction_tags", back_populates="transactions")


class TransactionTag(Base):
    """
    Association table for many-to-many relationship between transactions and tags.
    """
    __tablename__ = "transaction_tags"
    
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True) 