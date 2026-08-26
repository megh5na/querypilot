# tests get_schema_description function from the introspect module

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.db import introspect


@pytest.fixture(autouse=True)  # resests cache before and after every test so they dont affect eo
def reset_cache():
    """Reset the module-level cache before every test in this file."""
    introspect._cache["description"] = None
    introspect._cache["fetched_at"] = 0.0
    yield
    introspect._cache["description"] = None
    introspect._cache["fetched_at"] = 0.0


@pytest.fixture
def mock_pool(): # fake db pool returning 2 rows for the album table
    pool = AsyncMock()
    pool.fetch.return_value = [
        {"table_name": "Album", "column_name": "AlbumId", "data_type": "integer"},
        {"table_name": "Album", "column_name": "Title", "data_type": "character varying"},
    ]
    return pool


async def test_fetches_schema_on_first_call(mock_pool):
    with patch("app.db.introspect.get_pool", return_value=mock_pool):
        result = await introspect.get_schema_description()

    assert 'Table "Album"' in result
    assert "AlbumId (integer)" in result
    mock_pool.fetch.assert_called_once()


async def test_returns_cached_result_on_second_call(mock_pool):
    with patch("app.db.introspect.get_pool", return_value=mock_pool):
        first = await introspect.get_schema_description()
        second = await introspect.get_schema_description()

    assert first == second
    assert mock_pool.fetch.call_count == 1  # DB queried exactly once


async def test_cache_expires_after_ttl(mock_pool):
    with patch("app.db.introspect.get_pool", return_value=mock_pool):
        with patch("app.db.introspect.time") as mock_time:
            mock_time.monotonic.return_value = 0.0
            await introspect.get_schema_description()

            # Advance time past TTL
            mock_time.monotonic.return_value = introspect.CACHE_TTL + 1
            await introspect.get_schema_description()

    assert mock_pool.fetch.call_count == 2  # DB queried again after TTL