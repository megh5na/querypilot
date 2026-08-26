# tests for run_query in executor.py — specifically the row-limit wiring.
# validate_sql / enforce_row_limit correctness is covered in test_validator.py.
# these tests mock the readonly pool directly, since /ask's tests mock
# run_query itself and never exercise what's inside it.

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.executor import run_query, ResultTooLargeError
from app.core.validator import MAX_RESULT_ROWS, SQLValidationError


def mock_pool_returning(rows): # fake pool/connection pair whose fetch() returns the given rows
    conn = AsyncMock()
    conn.fetch.return_value = rows
    pool = MagicMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    pool.acquire.return_value.__aexit__.return_value = None
    return pool, conn


async def test_run_query_returns_rows_under_cap():
    rows = [{"AlbumId": i} for i in range(5)]
    pool, _ = mock_pool_returning(rows)

    with patch("app.core.executor.get_readonly_pool", return_value=pool):
        result = await run_query('SELECT "AlbumId" FROM "Album" LIMIT 5')

    assert result == rows


async def test_run_query_injects_limit_when_sql_has_none():
    pool, conn = mock_pool_returning([{"AlbumId": 1}])

    with patch("app.core.executor.get_readonly_pool", return_value=pool):
        await run_query('SELECT "AlbumId" FROM "Album"')

    executed_sql = conn.fetch.call_args[0][0]
    assert f"LIMIT {MAX_RESULT_ROWS + 1}" in executed_sql


async def test_run_query_raises_when_matches_exceed_cap():
    # simulates the db actually having more than MAX_RESULT_ROWS matches:
    # the injected max_rows + 1 sentinel comes back in full.
    rows = [{"AlbumId": i} for i in range(MAX_RESULT_ROWS + 1)]
    pool, _ = mock_pool_returning(rows)

    with patch("app.core.executor.get_readonly_pool", return_value=pool):
        with pytest.raises(ResultTooLargeError, match=str(MAX_RESULT_ROWS)):
            await run_query('SELECT "AlbumId" FROM "Album"')


async def test_run_query_rejects_explicit_limit_above_cap():
    pool, conn = mock_pool_returning([])

    with patch("app.core.executor.get_readonly_pool", return_value=pool):
        with pytest.raises(SQLValidationError, match="exceeds the maximum"):
            await run_query(f'SELECT "AlbumId" FROM "Album" LIMIT {MAX_RESULT_ROWS + 500}')

    conn.fetch.assert_not_called() # rejected before ever touching the db
