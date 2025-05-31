from sqlalchemy import Boolean, Column, ForeignKey, String, Float, DateTime, Text, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from app.db.database import Base



class TransactionCategoryEnum(enum.Enum):
    """Enhanced enumeration of valid transaction categories."""
    HOUSING = "Housing"
    TRANSPORTATION = "Transportation"
    FOOD_DINING = "Food & Dining"
    ENTERTAINMENT = "Entertainment"
    SHOPPING = "Shopping"
    UTILITIES = "Utilities"
    HEALTH_MEDICAL = "Health & Medical"
    PERSONAL_CARE = "Personal Care"
    EDUCATION = "Education"
    TRAVEL = "Travel"
    GIFTS_DONATIONS = "Gifts & Donations"
    INCOME = "Income"
    INVESTMENTS = "Investments"
    SAVINGS = "Savings"
    FEES_CHARGES = "Fees & Charges"
    ATM_CASH = "ATM & Cash"
    TRANSFERS = "Transfers"
    INSURANCE = "Insurance"
    TAXES = "Taxes"
    OTHER = "Other"



class BankTransaction(Base):
    """Transaction model."""
    
    __tablename__ = "bank_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    statement_id = Column(UUID(as_uuid=True), ForeignKey("bank_statements.id"))
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    description = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)
    balance = Column(Float, nullable=True)
    transaction_type = Column(String, nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("bank_categories.id"), nullable=True)
    reference_number = Column(String, nullable=True)
    evidence = Column(Text, nullable=False)
    is_recurring = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    statement = relationship("BankStatement", back_populates="bank_transactions")
    category = relationship("BankCategory", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")
    user = relationship("User", back_populates="transactions")