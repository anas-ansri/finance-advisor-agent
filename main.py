import asyncio
import asyncpg
import os

# Read the DATABASE_URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

async def test_connection():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        version = await conn.fetchval("SELECT version();")
        print("✅ Connected to Postgres:", version)
        await conn.close()
    except Exception as e:
        print("❌ Connection failed:", e)

if __name__ == "__main__":
    asyncio.run(test_connection())
