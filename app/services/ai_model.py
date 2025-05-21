from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_model import AIModel
from app.schemas.ai_model import AIModelCreate, AIModelUpdate


async def create_ai_model(db: AsyncSession, model_in: AIModelCreate) -> AIModel:
    """
    Create a new AI model.
    """
    db_model = AIModel(
        name=model_in.name,
        provider=model_in.provider,
        model_id=model_in.model_id,
        description=model_in.description,
        is_active=model_in.is_active,
        max_tokens=model_in.max_tokens,
        temperature=model_in.temperature,
    )
    db.add(db_model)
    await db.commit()
    await db.refresh(db_model)
    return db_model


async def get_ai_model(db: AsyncSession, model_id: int) -> Optional[AIModel]:
    """
    Get an AI model by ID.
    """
    result = await db.execute(select(AIModel).filter(AIModel.id == model_id))
    return result.scalars().first()


async def get_ai_models(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[AIModel]:
    """
    Get AI models.
    """
    result = await db.execute(
        select(AIModel)
        .filter(AIModel.is_active == True)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def update_ai_model(db: AsyncSession, model_id: int, model_in: AIModelUpdate) -> Optional[AIModel]:
    """
    Update an AI model.
    """
    model = await get_ai_model(db, model_id)
    if not model:
        return None
    
    update_data = model_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(model, field, value)
    
    await db.commit()
    await db.refresh(model)
    return model


async def delete_ai_model(db: AsyncSession, model_id: int) -> bool:
    """
    Delete an AI model.
    """
    await db.execute(delete(AIModel).where(AIModel.id == model_id))
    await db.commit()
    return True
