import asyncpg, asyncio
async def main():
    conn = await asyncpg.connect("postgresql://postgres:gMUhmO1V2ahYp3Fn@db.shddfqcfmokwyyrhmcyb.supabase.co:5432/postgres")
    print("Connected")
    await conn.close()