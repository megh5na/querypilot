## day 1
- set up uv, fastapi, and postgres in docker as pgvector. learned that uv manages the venv
- automatically, and that fastapi generates live api docs at /docs. got a /health
- endpoint working and a database running in a container.

## day 2
- loaded the chinook sample database into my postgres container.
- added config management + a .env file holding db url and a placeholder anthropic api key.
- added a database connection pool in app/db/session.py.
- wrote schema introspection in app/db/introspect.py which turns the live db structure into a plain text description. why self introspection and not hardcoded rules? querying information_schema.columns returns one row per column across the database, with table_name, column_name, and data_type. it can adapt to database changes better.
- exposed it as GET /schema via app/api/routes/schema.py.

## day 3
- app/core/llm.py has a generate_sql function that calls claude and returns a sql string.
- POST /ask accepts a question, introspects the schema, asks the model for sql, returns it. does not execute it yet.
- used model claude-sonnet-4-6.

## day 4
- dedicated read-only postgres role
- app/core/executor.py -> runs generated sql
- /ask executes and return rows, with asyncpg.PostgresError at http 400.
- so now, flow is "question -> sql -> execute -> rows"

## day 5
- app/core/validator.py uses sqlglot to parse generated sql before it hits the database. checks: parseable, exactly one statement, must be a SELECT. 
- added AskResponse pydantic model so fastapi validates the response shape too.
- 3 layer defense for execution: sqlglot validation -> read-only role -> statement timeout.

## day 6
- added pytest infrastructure: pytest, pytest-asyncio, httpx as dev dependencies
- tests/conftest.py holds two fixtures: mock_generate_sql and mock_run_query.
- unit tests (test_validator.py) - no db no nothing.
- integration tests (test_ask.py) - only the two external dependencies (llm and db) are mocked.
- production consideration: fast unit tests (no I/O) should be the majority. integration tests are slower and require more setup. keep the ratio high.
- production consideration: mocks make tests fast and deterministic, but they don't prove the real system works end-to-end. that's what integration/e2e tests with a real db are for, added later.