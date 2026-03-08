import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("TELEGRAM_USERS_DB_URL")

async def update_guests():
    print(f"Connecting to {DB_URL}")
    conn = await asyncpg.connect(DB_URL)
    result = await conn.execute("UPDATE users SET is_admin = TRUE WHERE is_guest = TRUE;")
    print("Result:", result)
    await conn.close()

if __name__ == "__main__":
    asyncio.run(update_guests())
