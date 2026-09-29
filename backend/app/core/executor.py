# single place to execute SQL queries on the readonly database
# called by ask.py, depends on db.session.py

from app.db.session import get_readonly_pool
from app.core.validator import validate_sql, enforce_row_limit, MAX_RESULT_ROWS, SQLValidationError

__all__ = ["run_query", "SQLValidationError", "ResultTooLargeError"] # re-export validator errors


class ResultTooLargeError(Exception): # raised when a query matches more rows than we allow back
    pass


async def run_query(sql: str) -> list[dict]:

    validate_sql(sql) # structural safety: parseable, single statement, SELECT only
    limited_sql = enforce_row_limit(sql) # resource safety: caps rows returned (see validator.py)

    pool = await get_readonly_pool() # get readonly database pool
    async with pool.acquire() as conn: # acquire connection from pool
        rows = await conn.fetch(limited_sql) # execute sql

    if len(rows) > MAX_RESULT_ROWS:
        raise ResultTooLargeError(
            f"Query matched more than {MAX_RESULT_ROWS} rows. "
            "Add a LIMIT or narrow the WHERE clause."
        )

    return [dict(r) for r in rows] # return rows as list of dictionaries