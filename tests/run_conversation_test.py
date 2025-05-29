import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import Base, engine, init_db
from tests.test_conversation import test_conversation

# Load environment variables
load_dotenv()

async def setup_database():
    """Set up test database"""
    print("\nSetting up test database...")
    # Initialize database with extensions
    await init_db()
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

async def cleanup_database():
    """Clean up the test database"""
    async with engine.begin() as conn:
        # Drop all tables
        await conn.run_sync(Base.metadata.drop_all)

async def main():
    """Run the conversation test"""
    try:
        # Set up database
        print("Setting up test database...")
        await setup_database()
        
        # Run the test
        print("\nRunning conversation test...")
        await test_conversation()
        
    except Exception as e:
        print(f"Error during test: {str(e)}")
        raise
    finally:
        # Clean up database
        print("\nCleaning up test database...")
        await cleanup_database()

if __name__ == "__main__":
    # Run the test
    asyncio.run(main()) 