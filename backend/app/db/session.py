import asyncpg
from app.config import settings

_pool = None # for introspection
_ro_pool = None # for generated SQL

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.database_url) # pool of connections instead of opening a new connection for each request
    return _pool

async def get_readonly_pool(): 
    global _ro_pool
    if _ro_pool is None:
        _ro_pool = await asyncpg.create_pool(
            settings.database_url_ro,
            server_settings={"statement_timeout": "5000"},  # 5s cap applied to every connection
        )
    return _ro_pool

async def close_pools():
    # called on shutdown, and by integration tests — a pool is bound to the event loop that created it
    global _pool, _ro_pool
    for pool in (_pool, _ro_pool):
        if pool is not None:
            await pool.close()
    _pool = None
    _ro_pool = None