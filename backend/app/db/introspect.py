# reads schema and turns it into plain text summary

import time
from app.db.session import get_pool

_cache: dict = {  # schema remains unchanged, so reqest is cached every 5 mins
    "description": None,
    "fetched_at": 0.0,
}

CACHE_TTL = 300  # seconds


async def get_schema_description() -> str:
    now = time.monotonic()
    if _cache["description"] is not None and now - _cache["fetched_at"] < CACHE_TTL:
        return _cache["description"]

    pool = await get_pool() # use the read write pool from session.py
    rows = await pool.fetch("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """) 

    tables: dict[str, list[str]] = {}
    for r in rows:
        tables.setdefault(r["table_name"], []).append(
            f'{r["column_name"]} ({r["data_type"]})'
        )

    description = "\n".join(
        f'Table "{t}": {", ".join(cols)}' for t, cols in tables.items()
    )

    _cache["description"] = description
    _cache["fetched_at"] = now
    return description

# rather than hardcode schema rules, introspection adapts to changes automatically