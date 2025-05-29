from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserSettingsUpdate
from app.services.user import update_user

router = APIRouter()

@router.put("/settings", response_model=dict)
async def update_user_settings(
    settings: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update user settings.
    """
    try:
        user = await update_user(db, current_user.id, settings.dict(exclude_unset=True))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 