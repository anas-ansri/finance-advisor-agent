from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

# User preferences for persona customization
class UserPreferences(BaseModel):
    favorite_brands: Optional[List[str]] = []
    favorite_music_genres: Optional[List[str]] = []
    favorite_movies: Optional[List[str]] = []
    favorite_cuisines: Optional[List[str]] = []
    lifestyle_preferences: Optional[List[str]] = []
    financial_goals: Optional[List[str]] = []
    additional_notes: Optional[str] = None

# Schema for persona generation request
class PersonaGenerationRequest(BaseModel):
    user_preferences: Optional[UserPreferences] = None

# Cultural profile sub-schema
class CulturalProfile(BaseModel):
    music_taste: str
    entertainment_style: str
    fashion_sensibility: str
    dining_philosophy: str

# Base schema for Persona Profile
class PersonaProfileBase(BaseModel):
    persona_name: str
    persona_description: str
    key_traits: List[str]
    lifestyle_summary: str
    financial_tendencies: str
    cultural_profile: Optional[CulturalProfile] = None
    financial_advice_style: Optional[str] = None

# Schema for creating a Persona Profile (used internally)
class PersonaProfileCreate(PersonaProfileBase):
    user_id: uuid.UUID
    source_qloo_data: Optional[Dict[str, Any]] = None

# Schema for reading/returning a Persona Profile from the API
class PersonaProfileOut(PersonaProfileBase):
    id: uuid.UUID
    user_id: uuid.UUID
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

# Schema for the final response from the /persona endpoint
class PersonaResponse(BaseModel):
    profile: PersonaProfileOut
    # You can add sidegrade recommendations here later
    # recommendations: List[Any] = []