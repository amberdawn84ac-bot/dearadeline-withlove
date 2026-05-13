"""Fix null emails and roles in User table before migration."""
import asyncio
import asyncpg

async def fix_data():
    conn = await asyncpg.connect(
        'postgresql://postgres:th0tTTjvVE5vyvBJ@db.gyxowttfwqbajoapfebf.supabase.co:5432/postgres'
    )
    
    # Fix null emails
    await conn.execute("""
        UPDATE "User" 
        SET email = CONCAT('user_', id, '@placeholder.com') 
        WHERE email IS NULL
    """)
    
    # Fix null roles
    await conn.execute("""
        UPDATE "User" 
        SET role = 'STUDENT' 
        WHERE role IS NULL
    """)
    
    print("Fixed null emails and roles")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_data())
