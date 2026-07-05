import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

pool: asyncpg.Pool | None = None


async def init_pool():
    global pool
    pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))


async def close_pool():
    if pool:
        await pool.close()


async def get_user_by_email(email: str) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM user WHERE email = $1", email)


async def update_user_name_in_db(email: str, current_first: str, current_last: str, new_first: str, new_last: str) -> None:
    async with pool.acquire() as conn:
        user = await conn.fetchrow('SELECT * FROM "user" WHERE email = $1', email)
        if user is None:
            raise ValueError(f"ไม่พบ user ที่มีอีเมล {email} ใน DB")
        if user["name"] != current_first or user["lastname"] != current_last:
            raise ValueError(f"ชื่อปัจจุบันไม่ตรง: คาดหวัง '{user['name']} {user['lastname']}' แต่ได้ '{current_first} {current_last}'")
        await conn.execute(
            'UPDATE "user" SET name = $1, lastname = $2 WHERE email = $3',
            new_first, new_last, email
        )
