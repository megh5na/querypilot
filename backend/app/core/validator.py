import sqlglot
import sqlglot.errors


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