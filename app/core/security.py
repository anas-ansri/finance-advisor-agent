from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client, Client

from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.services.user import get_user_by_email

# HTTP Bearer scheme for token authentication
security = HTTPBearer()

def get_supabase_client() -> Client:
    """
    Get Supabase client instance.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current user from Supabase JWT token.
    """
    try:
        supabase = get_supabase_client()
        user = supabase.auth.get_user(credentials.credentials)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        db_user = await get_user_by_email(db, email=user.user.email)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return db_user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) 