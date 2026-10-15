# fixtures for tests that talk to a real postgres (the chinook db from .env).
# everything here is skipped automatically when the db isn't reachable, so a plain
# `uv run pytest` still works without docker. the llm is still stubbed — only the db is real.

import asyncio

import asyncpg
import httpx
import pytest

from app.config import settings
from app.db import introspect, session
from app.main import app


def _db_reachable() -> bool:
    async def ping():
        conn = await asyncpg.connect(settings.database_url, timeout=2)
        await conn.close()

    try:
        asyncio.run(ping())
        return True
    except (OSError, asyncpg.PostgresError, asyncio.TimeoutError):
        return False


_DB_UP = _db_reachable()  # checked once per test run, at collection time


def pytest_collection_modifyitems(items):
    skip = pytest.mark.skip(reason="postgres not reachable at DATABASE_URL")
    for item in items:
        if "integration" in item.keywords and not _DB_UP:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
async def fresh_pools():
    # asyncpg pools are bound to the event loop that created them, and pytest-asyncio gives
    # every test its own loop — so each test needs its own pools, closed when it finishes.
    session._pool = None
    session._ro_pool = None
    introspect._cache.update(description=None, fetched_at=0.0)
    yield
    await session.close_pools()


@pytest.fixture
def mock_get_schema_description():
    # overrides the autouse fixture of the same name in tests/conftest.py:
    # here we want the real introspection, not the canned schema string
    yield None


@pytest.fixture
async def api():
    # in-process client that runs on the test's own event loop (unlike TestClient, which
    # spins up a separate loop per request and would orphan the pools)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
