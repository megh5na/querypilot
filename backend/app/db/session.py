import asyncpg
from app.config import settings

_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.database_url) # pool of connections instead of opening a new connection for each request
    return _pool