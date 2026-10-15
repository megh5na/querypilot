# run_query, the read-only role, and introspection against the real chinook db.
# chinook is static, so exact counts are safe to assert (347 albums, 3503 tracks).

import asyncpg
import pytest

from app.core.executor import ResultTooLargeError, run_query
from app.core.validator import SQLValidationError
from app.db import session
from app.db.introspect import get_schema_description

pytestmark = pytest.mark.integration


async def test_run_query_returns_real_rows():
    rows = await run_query("SELECT album_id, title FROM album ORDER BY album_id LIMIT 2")

    assert [r["album_id"] for r in rows] == [1, 2]
    assert rows[1]["title"] == "Balls to the Wall"


async def test_unlimited_query_under_the_cap_returns_every_row():
    # no LIMIT in the sql -> executor injects LIMIT 1001, which must not truncate 347 rows
    rows = await run_query("SELECT album_id FROM album")

    assert len(rows) == 347


async def test_query_over_the_cap_raises_instead_of_truncating():
    with pytest.raises(ResultTooLargeError):
        await run_query("SELECT * FROM track")  # 3503 rows


async def test_explicit_limit_is_respected():
    assert len(await run_query("SELECT * FROM track LIMIT 5")) == 5


async def test_explicit_limit_over_the_cap_is_rejected_before_the_db():
    with pytest.raises(SQLValidationError):
        await run_query("SELECT * FROM track LIMIT 5000")


async def test_missing_table_surfaces_as_a_postgres_error():
    with pytest.raises(asyncpg.UndefinedTableError):
        await run_query('SELECT * FROM "Track"')  # quoted PascalCase doesn't exist here


async def test_readonly_role_cannot_write():
    # the validator never sees this statement, so this proves the role itself is the safety net.
    # WHERE false means that even if the role were misconfigured, nothing would change.
    pool = await session.get_readonly_pool()

    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await pool.execute("UPDATE album SET title = title WHERE false")


async def test_readonly_pool_applies_the_statement_timeout():
    pool = await session.get_readonly_pool()

    assert await pool.fetchval("SHOW statement_timeout") == "5s"


async def test_schema_description_matches_the_real_database():
    description = await get_schema_description()

    assert 'Table "album": album_id (integer)' in description
    assert description.count("\nTable ") + 1 == 11  # all chinook tables, nothing missing


async def test_close_pools_releases_and_resets_both_pools():
    await session.get_pool()
    await session.get_readonly_pool()

    await session.close_pools()

    assert session._pool is None
    assert session._ro_pool is None
