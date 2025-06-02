import logging
from typing import AsyncGenerator
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create async engine for main database
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,  # Enable connection health checks
    pool_size=5,  # Limit pool size
    max_overflow=10,  # Allow some overflow connections
    pool_timeout=30,  # Connection timeout
    pool_recycle=1800,  # Recycle connections every 30 minutes
    connect_args={
        "server_settings": {
            "application_name": "finance_advisor",
            "statement_timeout": "30000",  # 30 seconds
            "lock_timeout": "30000",  # 30 seconds
        },
        "timeout": 30,  # Connection timeout in seconds
        "command_timeout": 30,  # Command timeout in seconds
    }
)

# Create async engine for test database
test_engine = create_async_engine(
    settings.TEST_DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    connect_args={
        "server_settings": {
            "application_name": "finance_advisor_test",
            "statement_timeout": "30000",
            "lock_timeout": "30000",
        },
        "timeout": 30,
        "command_timeout": 30,
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
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                # Enable UUID extension
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                logger.info("Database initialized successfully")
                return
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database initialization attempt {attempt + 1} failed: {str(e)}. Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Database initialization failed after {max_retries} attempts: {str(e)}")
                raise


async def init_test_db():
    """
    Initialize test database with required extensions.
    """
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            async with test_engine.begin() as conn:
                # Enable UUID extension
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                # Drop all tables and recreate them
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Test database initialized successfully")
                return
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Test database initialization attempt {attempt + 1} failed: {str(e)}. Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Test database initialization failed after {max_retries} attempts: {str(e)}")
                raise


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
