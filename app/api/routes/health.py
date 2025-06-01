from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging
import asyncio
from typing import Optional

from app.db.database import get_db
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


async def check_database_connection(db: AsyncSession) -> tuple[str, dict]:
    """
    Check database connection with timeout handling.
    """
    try:
        # Set a timeout for the database query
        async with asyncio.timeout(10):  # 10 second timeout
            result = await db.execute(text("SELECT 1"))
            row = result.scalar_one()
            if row == 1:
                return "connected", {
                    "status": "connected",
                    "url": settings.DATABASE_URL.split("@")[1] if "@" in settings.DATABASE_URL else "unknown"
                }
            else:
                return "disconnected", {
                    "status": "disconnected",
                    "error": "Unexpected database response"
                }
    except asyncio.TimeoutError:
        logger.error("Database connection timeout")
        return "disconnected", {
            "status": "disconnected",
            "error": "Database connection timeout"
        }
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return "disconnected", {
            "status": "disconnected",
            "error": str(e)
        }


@router.get("")
async def health_check(db: Optional[AsyncSession] = Depends(get_db)):
    """
    Health check endpoint to verify the service is running.
    
    This endpoint also checks the database connection.
    """
    # Check database connection
    if db is None:
        db_status = "disconnected"
        db_details = {
            "status": "disconnected",
            "error": "Database session not available"
        }
    else:
        db_status, db_details = await check_database_connection(db)
    
    return {
        "status": "healthy",
        "database": db_status,
        "details": db_details
    }
