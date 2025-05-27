# app/schemas/bank_statement.py
from typing import List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID

from app.schemas.user import User, UserInDBBase


class TransactionCategoryEnum(str, Enum):
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
    FEES_CHARGES = "Fees & Charges"
    ATM_CASH = "ATM & Cash"
    TRANSFERS = "Transfers"
    INSURANCE = "Insurance"
    TAXES = "Taxes"
    OTHER = "Other"


class BankTransaction(BaseModel):
    """Information about a single bank transaction."""
    
    date: datetime = Field(
        ..., description="The date when the transaction occurred."
    )
    description: str = Field(
        ..., description="Description of the transaction."
    )
    amount: float = Field(
        ..., description="The transaction amount (positive for deposits, negative for withdrawals)."
    )
    balance: Optional[float] = Field(
        None, description="The account balance after this transaction."
    )
    transaction_type: Optional[str] = Field(
        None, description="The type of transaction (e.g., 'deposit', 'withdrawal', 'payment')."
    )
    category: Optional[TransactionCategoryEnum] = Field(
        None, description="The spending category of the transaction."
    )
    reference_number: Optional[str] = Field(
        None, description="Any reference or transaction ID associated with this transaction."
    )
    is_recurring: Optional[bool] = Field(
        False, description="Whether this transaction is recurring."
    )
    evidence: str = Field(
        ...,
        description="The exact text from which this transaction information was extracted."
    )


class StatementMetadata(BaseModel):
    """Metadata about the bank statement."""
    
    account_number: Optional[str] = Field(
        None, description="The account number associated with this statement."
    )
    account_holder: Optional[str] = Field(
        None, description="The name of the account holder."
    )
    bank_name: Optional[str] = Field(
        None, description="The name of the bank."
    )
    statement_period: Optional[str] = Field(
        None, description="The period covered by this statement."
    )
    opening_balance: Optional[float] = Field(
        None, description="The opening balance for this statement period."
    )
    closing_balance: Optional[float] = Field(
        None, description="The closing balance for this statement period."
    )


class TagBase(BaseModel):
    """Base schema for transaction tags."""
    name: str = Field(..., description="Tag name")


class TagCreate(TagBase):
    """Schema for creating a tag."""
    pass


class TagInDBBase(TagBase):
    """Base schema for tags in database."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class Tag(TagInDBBase):
    """Tag schema for API responses."""
    pass


class BankStatementBase(BaseModel):
    """Base class for bank statement schemas."""
    
    title: str = Field(..., description="Title of the bank statement")
    description: Optional[str] = Field(None, description="Description of the bank statement")
    is_active: Optional[bool] = True


class BankStatementCreate(BankStatementBase):
    """Schema for creating a bank statement."""
    
    user_id: UUID = Field(..., description="ID of the user who owns this statement")  


class BankStatementUpdate(BankStatementBase):
    """Schema for updating a bank statement."""
    
    title: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class BankStatementInDBBase(BankStatementBase):
    """Base schema for bank statements in database."""
    
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class BankStatementWithData(BankStatementInDBBase):
    """Bank statement with extracted data."""
    
    metadata: StatementMetadata
    transactions: List[BankTransaction]
    user: Optional[User] = None


class BankStatementInDB(BankStatementInDBBase):
    """Bank statement schema for database operations."""
    
    pass


class BankStatement(BankStatementInDBBase):
    """Bank statement schema for API responses."""
    
    pass
