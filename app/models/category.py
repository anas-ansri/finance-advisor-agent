from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base


class Category(Base):
    """
    Category model for storing transaction and expense categories.
    """
    __tablename__ = "categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    color = Column(String, nullable=False)
    icon = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    expenses = relationship("Expense", back_populates="category")
    transactions = relationship("Transaction", back_populates="category")


# Import at the bottom to avoid circular imports
from app.models.expense import Expense
from app.models.transaction import Transaction 