from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


async def get_user(db: AsyncSession, user_id: UUID) -> Optional[User]:
    """
    Get a user by ID.
    """
    try:
        result = await db.execute(select(User).filter(User.id == user_id))
        return result.scalars().first()
    except Exception as e:
        await db.rollback()
        raise e


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Get a user by email.
    """
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    """
    Create a new user.
    """
    try:
        db_user = User(
            email=user_in.email,
            first_name=user_in.first_name,
            last_name=user_in.last_name,
            date_of_birth=user_in.date_of_birth,
            monthly_income=user_in.monthly_income,
            employment_status=user_in.employment_status,
            monthly_expenses=user_in.monthly_expenses,
            primary_financial_goal=user_in.primary_financial_goal,
            financial_goal_timeline=user_in.financial_goal_timeline,
            risk_tolerance=user_in.risk_tolerance,
            bio=user_in.bio,
            language=user_in.language,
            timezone=user_in.timezone,
            currency=user_in.currency
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user
    except Exception as e:
        await db.rollback()
        raise e


async def update_user(db: AsyncSession, user_id: UUID, user_in: dict) -> Optional[User]:
    """
    Update a user.
    """
    try:
        user = await get_user(db, user_id)
        if not user:
            return None
        
        for field, value in user_in.items():
            setattr(user, field, value)
        
        await db.commit()
        await db.refresh(user)
        return user
    except Exception as e:
        await db.rollback()
        raise e


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user.
    """
    user = await get_user_by_email(db, email=email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def delete_user(db: AsyncSession, user_id: UUID) -> bool:
    """Delete a user."""
    try:
        user = await get_user(db, user_id)
        if not user:
            return False
        
        await db.delete(user)
        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        raise e
