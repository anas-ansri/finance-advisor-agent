from datetime import datetime, date
from typing import Optional
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """
    Base user schema with common attributes.
    """
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    monthly_income: Optional[Decimal] = None
    employment_status: Optional[str] = None
    monthly_expenses: Optional[Decimal] = None
    primary_financial_goal: Optional[str] = None
    financial_goal_timeline: Optional[str] = None
    risk_tolerance: Optional[str] = None
    bio: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None


class UserCreate(UserBase):
    """
    User creation schema.
    """
    email: EmailStr


class UserUpdate(UserBase):
    """
    User update schema.
    """
    pass


class UserSettingsUpdate(BaseModel):
    """
    User settings update schema.
    """
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    ollama_host: Optional[str] = None
    ollama_model: Optional[str] = None
    preferred_ai_advisor: Optional[str] = None
    preferred_categorization_model: Optional[str] = None


class UserInDBBase(UserBase):
    """
    Base schema for users in database.
    """
    id: UUID
    created_at: datetime
    updated_at: datetime
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    ollama_host: Optional[str] = None
    ollama_model: Optional[str] = None
    preferred_ai_advisor: Optional[str] = None
    preferred_categorization_model: Optional[str] = None
    is_onboarding_done: bool = False
    
    class Config:
        from_attributes = True


class User(UserInDBBase):
    """
    User schema for API responses.
    """
    pass


class UserInDB(UserInDBBase):
    """
    User schema with hashed password for internal use.
    """
    hashed_password: str
