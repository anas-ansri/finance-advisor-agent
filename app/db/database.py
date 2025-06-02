import logging
from typing import AsyncGenerator
import os
import ssl
from urllib.parse import urlparse
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import text
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.core.config import settings

logger = logging.getLogger(__name__)

def get_ssl_args():
    """
    Get SSL arguments based on the database URL.
    """
    try:
        parsed_url = urlparse(settings.DATABASE_URL)
        logger.info(f"Database host: {parsed_url.hostname}")
        
        if "supabase" in settings.DATABASE_URL:
            # For Supabase, use SSL with proper configuration
            return {
                "ssl": "require",
                "server_settings": {
                    "application_name": "finance_advisor_agent",
                    "statement_timeout": "60000",  # 60 seconds
                    "idle_in_transaction_session_timeout": "60000"  # 60 seconds
                }
            }
        elif "heroku" in settings.DATABASE_URL or os.getenv("DYNO"):
            # Running on Heroku - use SSL
            return {
                "ssl": "require",
                "server_settings": {
                    "application_name": "finance_advisor_agent",
                    "statement_timeout": "60000",
                    "idle_in_transaction_session_timeout": "60000"
                }
            }
        else:
            # Local development
            return {
                "ssl": False,
                "server_settings": {
                    "application_name": "finance_advisor_agent",
                    "statement_timeout": "60000",
                    "idle_in_transaction_session_timeout": "60000"
                }
            }
    except Exception as e:
        logger.error(f"Error parsing database URL: {str(e)}")
        raise

# Create async engine for main database
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Disable SQL echo in production
    poolclass=AsyncAdaptedQueuePool,
    pool_size=3,  # Reduced for Heroku (limited connections)
    max_overflow=5,  # Reduced for Heroku
    pool_timeout=30,  # Seconds to wait before giving up on getting a connection from the pool
    pool_recycle=1800,  # Recycle connections after 30 minutes
    connect_args=get_ssl_args(),
    pool_pre_ping=True,  # Enable connection health checks
    # Disable statement caching and prepared statements for PgBouncer compatibility
    execution_options={
        "compiled_cache": None
    },
    # Add connection retry logic
    pool_reset_on_return='commit',
    # Disable prepared statements for PgBouncer compatibility
    prepare_statement=False
)

# Create async engine for test database
test_engine = create_async_engine(
    settings.TEST_DATABASE_URL,
    echo=True,  # Enable SQL echo in test environment
    poolclass=AsyncAdaptedQueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    connect_args={"ssl": False},  # Disable SSL for local development
    pool_pre_ping=True,
    execution_options={
        "compiled_cache": None
    }
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
