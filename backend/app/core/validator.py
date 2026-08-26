import sqlglot
import sqlglot.errors

MAX_RESULT_ROWS = 1000  # ceiling on rows any single query is allowed to return


class SQLValidationError(ValueError): # raised when generated sql fails structural validation
    pass


def validate_sql(sql: str) -> str: # parse and validate an sql string before execution
    # 1. parse to catch syntax errors
    try:
        statements = sqlglot.parse(sql, dialect="postgres")
    except sqlglot.errors.ParseError as e:
        raise SQLValidationError(f"SQL syntax error: {e}") from e

    # 2. check for exactly one statement
    if len(statements) != 1:
        raise SQLValidationError(
            f"Expected exactly 1 statement, got {len(statements)}"
        )

    statement = statements[0]

    if statement is None:
        raise SQLValidationError("SQL parsed to empty statement")

    # 3. check that statement is a select
    if not isinstance(statement, sqlglot.exp.Select):
        kind = type(statement).__name__
        raise SQLValidationError(
            f"Only SELECT statements are permitted, got {kind}"
        )

    return sql


def enforce_row_limit(sql: str, max_rows: int = MAX_RESULT_ROWS) -> str:
    # caps how many rows a validated SELECT can return. called after
    # validate_sql, so sql is already known to be exactly one SELECT statement.
    statement = sqlglot.parse_one(sql, dialect="postgres")

    existing_limit = statement.args.get("limit")
    if existing_limit is not None:
        limit_value = existing_limit.expression
        if isinstance(limit_value, sqlglot.exp.Literal) and limit_value.is_int:
            if int(limit_value.this) > max_rows:
                raise SQLValidationError(
                    f"LIMIT {limit_value.this} exceeds the maximum of {max_rows} rows"
                )
        return sql

    statement.set(
        "limit", sqlglot.exp.Limit(expression=sqlglot.exp.Literal.number(max_rows + 1))
    )
    return statement.sql(dialect="postgres")