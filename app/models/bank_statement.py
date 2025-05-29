# app/models/bank_statement.py
from sqlalchemy import Boolean, Column, ForeignKey, String, Float, DateTime, Text, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from app.db.database import Base


# app/models/bank_statement.py (Updated TransactionCategoryEnum)

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
    transactions = relationship("BankTransaction", back_populates="statement", cascade="all, delete-orphan")
    statement_metadata = relationship("BankStatementMetadata", back_populates="statement", uselist=False, cascade="all, delete-orphan")


class BankStatementMetadata(Base):
    """Statement metadata model."""
    
    __tablename__ = "bank_statement_metadata"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    statement_id = Column(UUID(as_uuid=True), ForeignKey("bank_statements.id"), unique=True)
    account_number = Column(String, nullable=True)
    account_holder = Column(String, nullable=True)
    bank_name = Column(String, nullable=True)
    statement_period = Column(String, nullable=True)
    opening_balance = Column(Float, nullable=True)
    closing_balance = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    statement = relationship("BankStatement", back_populates="statement_metadata")


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


class BankTag(Base):
    """Tag model for bank transactions."""
    
    __tablename__ = "bank_tags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    transactions = relationship("BankTransaction", secondary="bank_transaction_tags", back_populates="tags")


class BankTransaction(Base):
    """Transaction model."""
    
    __tablename__ = "bank_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    statement_id = Column(UUID(as_uuid=True), ForeignKey("bank_statements.id"))
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
    statement = relationship("BankStatement", back_populates="transactions")
    category = relationship("BankCategory", back_populates="transactions")
    tags = relationship("BankTag", secondary="bank_transaction_tags", back_populates="transactions")


class BankTransactionTag(Base):
    """Association table for Transaction-Tag many-to-many relationship."""
    
    __tablename__ = "bank_transaction_tags"
    
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("bank_transactions.id"), primary_key=True)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("bank_tags.id"), primary_key=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
