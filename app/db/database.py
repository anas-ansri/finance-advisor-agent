import logging
from typing import AsyncGenerator
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.config import settings

logger = logging.getLogger(__name__)

# asyncpg-optimized engine configuration for Supabase
engine_config = {
    "echo": settings.DEBUG,
    "future": True,
    # More conservative pool settings
    "pool_size": 3,  # Reduced from 5
    "max_overflow": 5,  # Reduced from 10
    "pool_timeout": 60,  # Increased from 30
    "pool_recycle": 1800,  # Reduced from 3600 to 30 minutes
    "pool_pre_ping": True,
    # Add statement timeout using server_settings
    "connect_args": {
        "server_settings": {
            "statement_timeout": "5000",  # 5 seconds in milliseconds
            "command_timeout": "5000",    # 5 seconds in milliseconds
        }
    }
}

# Create async engine for main database
engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_config
)

# Create async engine for test database  
test_engine = create_async_engine(
    settings.TEST_DATABASE_URL,
    **engine_config
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
    Includes retry logic optimized for asyncpg + Supabase.
    """
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                # Test the connection first with asyncpg
                await conn.execute(text("SELECT 1"))
                
                # Enable UUID extension
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                
                # Additional useful extensions for Supabase
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
                
                logger.info("Database initialized successfully with asyncpg")
                return
                
        except OperationalError as e:
            error_msg = str(e)
            logger.warning(f"Database connection attempt {attempt + 1}/{max_retries} failed: {error_msg}")
            
            # Check for specific asyncpg connection errors
            if "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                logger.info("Detected connection/timeout error, retrying...")
            
            if attempt == max_retries - 1:
                logger.error("All database connection attempts failed")
                raise
                
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)  # Exponential backoff, max 30 seconds
        
        except Exception as e:
            logger.error(f"Unexpected error during database initialization: {e}")
            raise


async def init_test_db():
    """
    Initialize test database with required extensions.
    """
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            async with test_engine.begin() as conn:
                # Test the connection
                await conn.execute(text("SELECT 1"))
                
                # Enable extensions
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
                
                # Drop all tables and recreate them
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
                
                logger.info("Test database initialized successfully with asyncpg")
                return
                
        except OperationalError as e:
            logger.warning(f"Test database connection attempt {attempt + 1}/{max_retries} failed: {e}")
            
            if attempt == max_retries - 1:
                raise
                
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session.
    Optimized for asyncpg with Supabase.
    """
    session = None
    try:
        session = async_session_factory()
        logger.debug("Database session started (asyncpg)")
        
        # Health check for Supabase with asyncpg
        await session.execute(text("SELECT 1"))
        
        yield session
        await session.commit()
        logger.debug("Database session committed")
        
    except Exception as e:
        if session:
            await session.rollback()
            logger.exception("Database session rolled back due to exception")
        raise
    finally:
        if session:
            await session.close()
            logger.debug("Database session closed")


async def get_test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async test database session.
    """
    session = None
    try:
        session = test_async_session_factory()
        logger.debug("Test database session started (asyncpg)")
        
        yield session
        await session.commit()
        logger.debug("Test database session committed")
        
    except Exception as e:
        if session:
            await session.rollback()
            logger.exception("Test database session rolled back due to exception")
        raise
    finally:
        if session:
            await session.close()
            logger.debug("Test database session closed")


async def check_db_health():
    """
    Health check function for database connectivity.
    Optimized for asyncpg + Supabase monitoring.
    """
    try:
        async with engine.begin() as conn:
            # Get PostgreSQL version
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            
            # Get connection info
            result = await conn.execute(text("SELECT current_database(), current_user, inet_server_addr(), inet_server_port()"))
            db_info = result.fetchone()
            
            logger.info(f"Database health check passed (asyncpg)")
            logger.info(f"PostgreSQL version: {version}")
            logger.info(f"Database: {db_info[0]}, User: {db_info[1]}, Server: {db_info[2]}:{db_info[3]}")
            
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def close_db_connections():
    """
    Gracefully close all database connections.
    Useful for shutdown procedures.
    """
    try:
        await engine.dispose()
        await test_engine.dispose()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


# Connection info logging (for debugging)
async def log_connection_info():
    """
    Log connection information for debugging purposes.
    """
    try:
        async with engine.begin() as conn:
            # Get asyncpg connection info
            result = await conn.execute(text("""
                SELECT 
                    current_database() as database,
                    current_user as user,
                    version() as version,
                    inet_server_addr() as server_addr,
                    inet_server_port() as server_port
            """))
            info = result.fetchone()
            
            logger.info("=== Database Connection Info (asyncpg) ===")
            logger.info(f"Database: {info.database}")
            logger.info(f"User: {info.user}")
            logger.info(f"Server: {info.server_addr}:{info.server_port}")
            logger.info(f"PostgreSQL: {info.version.split()[1] if info.version else 'Unknown'}")
            logger.info("==========================================")
            
    except Exception as e:
        logger.error(f"Could not retrieve connection info: {e}")