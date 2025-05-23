# app/models/bank_statement.py
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime, Text, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db.database import Base


class TransactionCategoryEnum(enum.Enum):
    """Enumeration of valid transaction categories."""
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
    OTHER = "Other"


class BankStatement(Base):
    """Bank statement model."""
    
    __tablename__ = "statements"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="statements")
    transactions = relationship("Transaction", back_populates="statement", cascade="all, delete-orphan")
    statement_metadata  = relationship("StatementMetadata", back_populates="statement", uselist=False, cascade="all, delete-orphan")


class StatementMetadata(Base):
    """Statement metadata model."""
    
    __tablename__ = "statement_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    statement_id = Column(Integer, ForeignKey("statements.id"), unique=True)
    account_number = Column(String, nullable=True)
    account_holder = Column(String, nullable=True)
    bank_name = Column(String, nullable=True)
    statement_period = Column(String, nullable=True)
    opening_balance = Column(Float, nullable=True)
    closing_balance = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    statement = relationship("BankStatement", back_populates="statement_metadata")



class Category(Base):
    """Transaction category model."""
    
    __tablename__ = "category"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(Enum(TransactionCategoryEnum), nullable=False)
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    transactions = relationship("Transaction", back_populates="category")


class Tag(Base):
    """Tag model for transactions."""
    
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    transactions = relationship("Transaction", secondary="transaction_tags", back_populates="tags")


class Transaction(Base):
    """Transaction model."""
    
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    statement_id = Column(Integer, ForeignKey("statements.id"))
    date = Column(DateTime, nullable=False)
    description = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)
    balance = Column(Float, nullable=True)
    transaction_type = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=True)
    reference_number = Column(String, nullable=True)
    evidence = Column(Text, nullable=False)
    is_recurring = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    statement = relationship("BankStatement", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    tags = relationship("Tag", secondary="transaction_tags", back_populates="transactions")


class TransactionTag(Base):
    """Association table for Transaction-Tag many-to-many relationship."""
    
    __tablename__ = "transaction_tags"
    
    transaction_id = Column(Integer, ForeignKey("transactions.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
