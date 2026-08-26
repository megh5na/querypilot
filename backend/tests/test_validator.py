# for testing validator.py
import pytest
from app.core.validator import validate_sql, enforce_row_limit, SQLValidationError, MAX_RESULT_ROWS


def test_valid_select():
    sql = "SELECT 1"
    assert validate_sql(sql) == sql


def test_valid_select_with_quoted_table(): # valid select with quoted table name
    sql = 'SELECT * FROM "Album" LIMIT 10'
    assert validate_sql(sql) == sql


def test_rejects_drop_table(): # rejects drop table statement
    with pytest.raises(SQLValidationError, match="Only SELECT statements are permitted"):
        validate_sql("DROP TABLE albums")


def test_rejects_multiple_statements(): # rejects multiple statements
    with pytest.raises(SQLValidationError, match="Expected exactly 1 statement"):
        validate_sql("SELECT 1; SELECT 2")


def test_rejects_nonsense(): # rejects nonsense statement
    with pytest.raises(SQLValidationError):
        validate_sql("not sql at all !!!")


def test_rejects_insert():
    with pytest.raises(SQLValidationError, match="Only SELECT statements are permitted"):
        validate_sql("INSERT INTO albums VALUES (1, 'test')")


def test_rejects_update():
    with pytest.raises(SQLValidationError, match="Only SELECT statements are permitted"):
        validate_sql("UPDATE albums SET title = 'x' WHERE albumid = 1")


def test_returns_original_sql_unchanged():
    # validate_sql should return the original string, not a normalized version
    sql = 'SELECT "Title" FROM "Album" WHERE "AlbumId" = 1'
    assert validate_sql(sql) is sql


# --- enforce_row_limit -------------------------------------------------

def test_injects_limit_when_absent(): # no LIMIT clause -> max_rows + 1 sentinel is added
    sql = 'SELECT "Title" FROM "Album"'
    result = enforce_row_limit(sql, max_rows=10)
    assert "LIMIT 11" in result


def test_leaves_limit_under_cap_untouched(): # explicit LIMIT below the cap is left alone
    sql = 'SELECT "Title" FROM "Album" LIMIT 5'
    assert enforce_row_limit(sql, max_rows=10) == sql


def test_leaves_limit_at_cap_untouched(): # explicit LIMIT exactly at the cap is allowed
    sql = 'SELECT "Title" FROM "Album" LIMIT 10'
    assert enforce_row_limit(sql, max_rows=10) == sql


def test_rejects_limit_above_cap(): # explicit LIMIT over the cap fails loudly, not clamped
    sql = 'SELECT "Title" FROM "Album" LIMIT 5000'
    with pytest.raises(SQLValidationError, match="exceeds the maximum of 10 rows"):
        enforce_row_limit(sql, max_rows=10)


def test_default_max_rows_is_used_when_not_specified():
    sql = 'SELECT "Title" FROM "Album"'
    result = enforce_row_limit(sql)
    assert f"LIMIT {MAX_RESULT_ROWS + 1}" in result