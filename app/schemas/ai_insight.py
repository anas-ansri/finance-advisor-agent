from pydantic import BaseModel
from typing import Optional
from uuid import UUID
import datetime

class AIInsightBase(BaseModel):
    title: str
    description: str
    category: str # e.g., "spending", "recommendation"

class AIInsightCreate(AIInsightBase):
    pass

class AIInsight(AIInsightBase):
    id: UUID
    user_id: UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True