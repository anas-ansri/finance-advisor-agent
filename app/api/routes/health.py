from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from app.db.database import get_db
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint to verify the service is running.
    
    This endpoint also checks the database connection.
    """
    # Check database connection
    try:
        # Execute a simple query to check database connection
        result = await db.execute(text("SELECT 1"))
        await result.fetchone()
        db_status = "connected"
        db_details = {
            "status": "connected",
            "url": settings.DATABASE_URL.split("@")[1] if "@" in settings.DATABASE_URL else "unknown"
        }
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        db_status = "disconnected"
        db_details = {
            "status": "disconnected",
            "error": str(e)
        }
    
    return {
        "status": "healthy",
        "database": db_status,
        "details": db_details
    }
