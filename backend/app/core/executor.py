# single place to execute SQL queries on the readonly database
# called by ask.py, depends on db.session.py

from app.db.session import get_readonly_pool

async def run_query(sql: str) -> list[dict]:
    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql)
    return [dict(r) for r in rows]