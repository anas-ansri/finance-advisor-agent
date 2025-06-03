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
    Check database connection with timeout handling and retries.
    """
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            # Set a timeout for the database query
            async with asyncio.timeout(5):  # Reduced from 10 to 5 seconds
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
            logger.warning(f"Database connection timeout (attempt {attempt + 1}/{max_retries})")
            if attempt == max_retries - 1:
                return "disconnected", {
                    "status": "disconnected",
                    "error": "Database connection timeout after multiple attempts"
                }
            await asyncio.sleep(retry_delay)
            retry_delay *= 2
        except Exception as e:
            logger.error(f"Database connection error (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                return "disconnected", {
                    "status": "disconnected",
                    "error": str(e)
                }
            await asyncio.sleep(retry_delay)
            retry_delay *= 2


@router.get("")
async def health_check(db: Optional[AsyncSession] = Depends(get_db)):
    """
    Health check endpoint to verify the service is running.
    
    This endpoint also checks the database connection with retries.
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
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "details": db_details
    }
