from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """
    Base user schema with common attributes.
    """
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False


class UserCreate(UserBase):
    """
    User creation schema.
    """
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserUpdate(UserBase):
    """
    User update schema.
    """
    password: Optional[str] = Field(None, min_length=8)


class UserInDBBase(UserBase):
    """
    Base schema for users in database.
    """
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


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
