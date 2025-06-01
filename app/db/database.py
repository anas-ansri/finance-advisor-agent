import logging
from typing import AsyncGenerator
import os
import ssl

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import text
from sqlalchemy.pool import NullPool

from app.core.config import settings

logger = logging.getLogger(__name__)

def get_ssl_args():
    """
    Get SSL arguments based on the database URL.
    """
    if "supabase" in settings.DATABASE_URL:
        # For Supabase, we need to handle self-signed certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return {
            "ssl": ssl_context,
            "statement_cache_size": 0,  # Disable statement cache for PgBouncer
            "prepared_statement_cache_size": 0  # Disable prepared statement cache
        }
    elif "heroku" in settings.DATABASE_URL:
        return {"ssl": True}
    else:
        return {"ssl": False}

# Create async engine for main database
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Disable SQL echo in production
    poolclass=NullPool,
    connect_args=get_ssl_args(),
    # Disable statement caching at the engine level
    execution_options={
        "compiled_cache": None
    }
)

# Create async engine for test database
test_engine = create_async_engine(
    settings.TEST_DATABASE_URL,
    echo=True,  # Enable SQL echo in test environment
    poolclass=NullPool,
    connect_args={"ssl": False}  # Disable SSL for local development
)

# Create async session factories
async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

test_async_session_factory = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create declarative base for models
Base = declarative_base()


async def init_db():
    """
    Initialize database with required extensions.
    """
    try:
        async with engine.begin() as conn:
            # Enable UUID extension
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise


async def init_test_db():
    """
    Initialize test database with required extensions.
    """
    try:
        async with test_engine.begin() as conn:
            # Enable UUID extension
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            # Drop all tables and recreate them
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Test database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize test database: {str(e)}")
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
