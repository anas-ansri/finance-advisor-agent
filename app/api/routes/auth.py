from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client, Client

from app.core.config import settings
from app.core.security import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, User as UserSchema
from app.services.user import create_user, get_user_by_email, update_user

router = APIRouter()

def get_supabase_client() -> Client:
    """
    Get Supabase client instance.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

@router.post("/login", response_model=dict)
async def login(
    email: str,
    password: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Login with email and password using Supabase authentication.
    """
    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
            
        # Get or create user in our database
        user = await get_user_by_email(db, email=email)
        if not user:
            user = await create_user(db, UserCreate(
                email=email,
                is_active=True,
                is_superuser=False
            ))
            
        # Convert SQLAlchemy model to Pydantic model
        user_schema = UserSchema.from_orm(user)
            
        return {
            "access_token": response.session.access_token,
            "token_type": "bearer",
            "user": user_schema.dict()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@router.get("/me", response_model=UserSchema)
async def read_users_me(
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get current user.
    """
    return current_user

@router.put("/me", response_model=UserSchema)
async def update_user_me(
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update current user.
    """
    user = await update_user(db, user_id=current_user.id, user_in=user_in)
    return user
