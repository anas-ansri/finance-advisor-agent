
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.db.database import get_db
from app.core.auth import get_current_user
from app.models.user import User as UserModel
from app.schemas.persona import PersonaResponse, PersonaProfileOut
from app.services.persona_engine import PersonaEngineService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=PersonaResponse)
async def get_user_persona(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Generate and retrieve the Persona for the current authenticated user.

    This endpoint orchestrates the process:
    1. Fetches user's transaction entities.
    2. Calls Qloo API for taste analysis.
    3. Calls Gemini API to generate a narrative persona.
    4. Caches the result and returns it.
    """
    logger.info(f"Received request to generate Persona for user: {current_user.email}")
    
    persona_service = PersonaEngineService(db)
    
    try:
        persona_profile = await persona_service.generate_persona_for_user(current_user)
        
        if not persona_profile:
            raise HTTPException(
                status_code=404,
                detail="Could not generate a Persona Profile for this user. Ensure there are enough transactions.",
            )
            
        profile_out = PersonaProfileOut.from_orm(persona_profile)
        
        return PersonaResponse(profile=profile_out)

    except Exception as e:
        logger.error(f"An unexpected error occurred in get_user_persona for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while generating the Persona Profile."
        )