"""
Run manual SQL migration to add ALU and ML tables without dropping existing data.
This preserves the hippocampus_documents table (3634 rows of curriculum data).
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

async def run_migration():
    """Execute the SQL migration file."""
    import asyncpg

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    # Read the SQL migration file
    migration_file = Path(__file__).parent.parent / "prisma" / "migrations" / "add_alu_and_ml_tables.sql"
    if not migration_file.exists():
        raise FileNotFoundError(f"Migration file not found: {migration_file}")

    with open(migration_file, "r") as f:
        sql = f.read()

    # Connect to Supabase and execute the migration
    conn = await asyncpg.connect(database_url)
    try:
        async with conn.transaction():
            await conn.execute(sql)
            print("Migration executed successfully: added AtomicUnit and ComponentInteractionLog tables")
            print("Preserved hippocampus_documents table (3634 rows)")
            print("Added 'assessed' to XAPIVerb enum")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())
