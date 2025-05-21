from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.ai_model import AIModel, AIModelCreate, AIModelUpdate
from app.services.ai_model import (
    create_ai_model,
    delete_ai_model,
    get_ai_model,
    get_ai_models,
    update_ai_model,
)

router = APIRouter()


@router.post("", response_model=AIModel)
async def create_model(
    model_in: AIModelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create a new AI model.
    
    Only superusers can create models.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    model = await create_ai_model(db, model_in=model_in)
    return model


@router.get("", response_model=List[AIModel])
async def read_models(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Retrieve AI models.
    """
    models = await get_ai_models(db, skip=skip, limit=limit)
    return models


@router.get("/{model_id}", response_model=AIModel)
async def read_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get a specific AI model by id.
    """
    model = await get_ai_model(db, model_id=model_id)
    if not model:
        raise HTTPException(status_code=404, detail="AI model not found")
    return model


@router.put("/{model_id}", response_model=AIModel)
async def update_model(
    model_id: int,
    model_in: AIModelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update an AI model.
    
    Only superusers can update models.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    model = await get_ai_model(db, model_id=model_id)
    if not model:
        raise HTTPException(status_code=404, detail="AI model not found")
    
    model = await update_ai_model(db, model_id=model_id, model_in=model_in)
    return model


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Delete an AI model.
    
    Only superusers can delete models.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    model = await get_ai_model(db, model_id=model_id)
    if not model:
        raise HTTPException(status_code=404, detail="AI model not found")
    
    await delete_ai_model(db, model_id=model_id)
    return None
