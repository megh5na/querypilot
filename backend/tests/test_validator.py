# for testing validator.py
import pytest
from app.core.validator import validate_sql, SQLValidationError


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