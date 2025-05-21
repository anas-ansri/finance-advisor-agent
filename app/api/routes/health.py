from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db

router = APIRouter()


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint to verify the service is running.
    
    This endpoint also checks the database connection.
    """
    # Check database connection
    try:
        # Execute a simple query to check database connection
        await db.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return {
        "status": "healthy",
        "database": db_status,
    }
