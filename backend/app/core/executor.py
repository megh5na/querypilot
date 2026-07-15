# single place to execute SQL queries on the readonly database
# called by ask.py, depends on db.session.py

from app.db.session import get_readonly_pool
from app.core.validator import validate_sql, SQLValidationError

__all__ = ["run_query", "SQLValidationError"] # re-export validator errors


async def run_query(sql: str) -> list[dict]:

    validate_sql(sql) # validate sql before execution

    pool = await get_readonly_pool() # get readonly database pool
    async with pool.acquire() as conn: # acquire connection from pool
        rows = await conn.fetch(sql) # execute sql
    return [dict(r) for r in rows] # return rows as list of dictionaries