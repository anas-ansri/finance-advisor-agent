from typing import Optional

from pydantic import BaseModel, Field


class AIPreferenceBase(BaseModel):
    """
    Base AI preference schema.
    """
    preferred_model_id: Optional[int] = Field(None, description="ID of the preferred AI model")
    system_prompt: Optional[str] = Field(None, description="Default system prompt for conversations")
    temperature: Optional[float] = Field(None, description="Temperature parameter for generation")


class AIPreferenceCreate(AIPreferenceBase):
    """
    AI preference creation schema.
    """
    pass


class AIPreferenceUpdate(AIPreferenceBase):
    """
    AI preference update schema.
    """
    pass


class AIPreference(AIPreferenceBase):
    """
    AI preference schema for API responses.
    """
    id: int
    user_id: int
    
    class Config:
        orm_mode = True
