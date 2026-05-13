"""Enable pgvector extension in PostgreSQL."""
import asyncio
import asyncpg

async def enable_extension():
    conn = await asyncpg.connect(
        'postgresql://postgres:th0tTTjvVE5vyvBJ@db.gyxowttfwqbajoapfebf.supabase.co:5432/postgres'
    )
    
    # Enable pgvector extension
    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    print("Enabled pgvector extension")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(enable_extension())
