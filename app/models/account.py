from sqlalchemy import Boolean, Column, DateTime, String, Numeric, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.database import Base


class Account(Base):
    """
    Account model for storing user's financial accounts.
    """
    __tablename__ = "accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    balance = Column(Numeric, server_default="0", nullable=False)
    currency = Column(String, server_default="USD", nullable=False)
    is_active = Column(Boolean, server_default="true", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="accounts")
    bank_transactions = relationship("BankTransaction", back_populates="account", cascade="all, delete-orphan")


# Import at the bottom to avoid circular imports
from app.models.bank_statement import BankTransaction