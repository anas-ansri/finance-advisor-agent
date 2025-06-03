from fastapi import FastAPI
import asyncpg
import os

app = FastAPI()

# Sanitize DATABASE_URL for asyncpg (remove +asyncpg if needed)
raw_url = os.getenv("DATABASE_URL", "")
if raw_url.startswith("postgresql+asyncpg://"):
    DATABASE_URL = raw_url.replace("postgresql+asyncpg://", "postgresql://", 1)
else:
    DATABASE_URL = raw_url

@app.get("/")
async def root():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        version = await conn.fetchval("SELECT version();")
        await conn.close()
        return {"message": "✅ Connected", "postgres_version": version}
    except Exception as e:
        return {"message": "❌ Connection failed", "error": str(e)}
