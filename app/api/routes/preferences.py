from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.ai_preference import AIPreference, AIPreferenceCreate, AIPreferenceUpdate
from app.services.ai_preference import (
    create_ai_preference,
    get_ai_preference_by_user_id,
    update_ai_preference,
)

router = APIRouter()


@router.get("", response_model=AIPreference)
async def read_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get current user's AI preferences.
    """
    preferences = await get_ai_preference_by_user_id(db, user_id=current_user.id)
    if not preferences:
        raise HTTPException(status_code=404, detail="AI preferences not found")
    return preferences


@router.post("", response_model=AIPreference)
async def create_preferences(
    preferences_in: AIPreferenceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create AI preferences for current user.
    """
    existing_preferences = await get_ai_preference_by_user_id(db, user_id=current_user.id)
    if existing_preferences:
        raise HTTPException(
            status_code=400,
            detail="AI preferences already exist. Use PUT to update.",
        )
    
    preferences = await create_ai_preference(db, user_id=current_user.id, preferences_in=preferences_in)
    return preferences


@router.put("", response_model=AIPreference)
async def update_preferences(
    preferences_in: AIPreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update current user's AI preferences.
    """
    preferences = await get_ai_preference_by_user_id(db, user_id=current_user.id)
    if not preferences:
        raise HTTPException(status_code=404, detail="AI preferences not found")
    
    preferences = await update_ai_preference(db, preferences_id=preferences.id, preferences_in=preferences_in)
    return preferences
