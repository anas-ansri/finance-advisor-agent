from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class AIModelBase(BaseModel):
    """
    Base AI model schema.
    """
    name: str = Field(..., description="Name of the AI model")
    provider: str = Field(..., description="Provider of the AI model (e.g., openai, anthropic)")
    model_id: str = Field(..., description="ID of the model as used by the provider")
    description: Optional[str] = Field(None, description="Description of the AI model")
    is_active: bool = Field(True, description="Whether the model is active and available for use")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens the model can process")
    temperature: float = Field(0.7, description="Temperature parameter for generation")
    
    @validator("temperature")
    def validate_temperature(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Temperature must be between 0 and 1")
        return v


class AIModelCreate(AIModelBase):
    """
    AI model creation schema.
    """
    pass


class AIModelUpdate(BaseModel):
    """
    AI model update schema.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    
    @validator("temperature")
    def validate_temperature(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError("Temperature must be between 0 and 1")
        return v


class AIModel(AIModelBase):
    """
    AI model schema for API responses.
    """
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
