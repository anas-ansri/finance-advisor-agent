#!/usr/bin/env python3
"""
Test database connection script for debugging Heroku deployment issues.
"""
import asyncio
import asyncpg
import ssl
import os
from urllib.parse import urlparse

async def test_connection():
    """Test database connection with various SSL configurations."""
    
    # Get database URL from environment or use the one from Heroku config
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:gMUhmO1V2ahYp3Fn@db.shddfqcfmokwyyrhmcyb.supabase.co:5432/postgres")
    
    # Remove the +asyncpg part for direct asyncpg connection
    if "+asyncpg" in database_url:
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    print(f"Testing connection to: {database_url.split('@')[1] if '@' in database_url else 'unknown'}")
    
    # Parse URL
    parsed = urlparse(database_url)
    
    # Test different SSL configurations
    ssl_configs = [
        {"ssl": "require"},
        {"ssl": "prefer"},
        {"ssl": ssl.create_default_context()},
        {"ssl": None}
    ]
    
    for i, ssl_config in enumerate(ssl_configs):
        print(f"\n--- Test {i+1}: SSL config = {ssl_config} ---")
        try:
            conn = await asyncpg.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/') or 'postgres',
                **ssl_config
            )
            
            # Test a simple query
            result = await conn.fetchval("SELECT 1")
            print(f"✓ Connection successful! Query result: {result}")
            
            # Get server info
            server_version = await conn.fetchval("SELECT version()")
            print(f"✓ Server version: {server_version[:50]}...")
            
            await conn.close()
            print("✓ Connection closed successfully")
            break
            
        except Exception as e:
            print(f"✗ Connection failed: {str(e)}")
    
    else:
        print("\n❌ All connection attempts failed!")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
