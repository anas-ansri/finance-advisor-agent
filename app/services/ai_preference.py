from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_preference import AIPreference
from app.schemas.ai_preference import AIPreferenceCreate, AIPreferenceUpdate


async def create_ai_preference(
    db: AsyncSession, user_id: int, preferences_in: AIPreferenceCreate
) -> AIPreference:
    """
    Create AI preferences for a user.
    """
    db_preferences = AIPreference(
        user_id=user_id,
        preferred_model_id=preferences_in.preferred_model_id,
        system_prompt=preferences_in.system_prompt,
        temperature=preferences_in.temperature,
    )
    db.add(db_preferences)
    await db.commit()
    await db.refresh(db_preferences)
    return db_preferences


async def get_ai_preference(db: AsyncSession, preferences_id: int) -> Optional[AIPreference]:
    """
    Get AI preferences by ID.
    """
    result = await db.execute(select(AIPreference).filter(AIPreference.id == preferences_id))
    return result.scalars().first()


async def get_ai_preference_by_user_id(db: AsyncSession, user_id: int) -> Optional[AIPreference]:
    """
    Get AI preferences by user ID.
    """
    result = await db.execute(select(AIPreference).filter(AIPreference.user_id == user_id))
    return result.scalars().first()


async def update_ai_preference(
    db: AsyncSession, preferences_id: int, preferences_in: AIPreferenceUpdate
) -> Optional[AIPreference]:
    """
    Update AI preferences.
    """
    preferences = await get_ai_preference(db, preferences_id)
    if not preferences:
        return None
    
    update_data = preferences_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(preferences, field, value)
    
    await db.commit()
    await db.refresh(preferences)
    return preferences
