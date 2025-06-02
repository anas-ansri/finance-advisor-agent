import logging
from typing import AsyncGenerator

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Database connection pool settings
POOL_SIZE = 5
MAX_OVERFLOW = 10
POOL_TIMEOUT = 30
POOL_RECYCLE = 1800

# Create async engine for main database
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    # Disable statement cache for PgBouncer compatibility
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }
)

# Create async engine for test database
test_engine = create_async_engine(
    settings.TEST_DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    # Disable statement cache for PgBouncer compatibility
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }
)

# Create async session factories
async_session_factory = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

test_async_session_factory = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)

# Create declarative base for models
Base = declarative_base()


async def init_db():
    """
    Initialize database with required extensions.
    """
    async with engine.begin() as conn:
        # Enable UUID extension
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))


async def init_test_db():
    """
    Initialize test database with required extensions.
    """
    async with test_engine.begin() as conn:
        # Enable UUID extension
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        # Drop all tables and recreate them
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session.
    """
    async with async_session_factory() as session:
        logger.debug("Database session started")
        try:
            yield session
            await session.commit()
            logger.debug("Database session committed")
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Database error occurred: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service is currently unavailable. Please try again later."
            )
        except Exception as e:
            await session.rollback()
            logger.exception("Database session rolled back due to exception")
            raise
        finally:
            await session.close()
            logger.debug("Database session closed")


async def get_test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async test database session.
    """
    async with test_async_session_factory() as session:
        logger.debug("Test database session started")
        try:
            yield session
            await session.commit()
            logger.debug("Test database session committed")
        except Exception as e:
            await session.rollback()
            logger.exception("Test database session rolled back due to exception")
            raise
        finally:
            await session.close()
            logger.debug("Test database session closed")
