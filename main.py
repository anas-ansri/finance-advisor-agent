import asyncio
import asyncpg
import os

# Get database URL from env
raw_url = os.getenv("DATABASE_URL")

# Fix URL scheme if needed
if raw_url.startswith("postgresql+asyncpg://"):
    DATABASE_URL = raw_url.replace("postgresql+asyncpg://", "postgresql://", 1)
else:
    DATABASE_URL = raw_url

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
