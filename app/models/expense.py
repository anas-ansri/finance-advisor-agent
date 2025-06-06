from sqlalchemy import Boolean, Column, DateTime, String, Numeric, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base


class Expense(Base):
    """
    Expense model for storing user's expenses.
    """
    __tablename__ = "expenses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("bank_categories.id"))
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("bank_transactions.id"), nullable=True)
    description = Column(String, nullable=False)
    amount = Column(Numeric, nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    is_recurring = Column(Boolean, server_default="false", nullable=False)
    recurrence_period = Column(String, nullable=True)  # e.g., 'daily', 'weekly', 'monthly'
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="expenses")
    category = relationship("BankCategory", back_populates="expenses")
    expenses = relationship("BankTransaction", back_populates="transactions")


# Import at the bottom to avoid circular imports
from app.models.bank_category import BankCategory 