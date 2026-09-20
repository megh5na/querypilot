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
- integration tests (test_ask.py) - only the two external dependencies (llm and db) are mocked

## day 7
- schema description now cached in-process for 5 minutes.
- defense layer : validator.py has enforce_row_limit() — injects LIMIT 1001 when the generated sql has none, and rejects (doesn't clamp) an explicit LIMIT above 1000.
- executor.py raises ResultTooLargeError when that sentinel row comes back
- added test_executor.py — run_query was previously only exercised through mocks in test_ask.py, so its internals had no real coverage.

## day 8
- app/core/logging.py: JSONFormatter writes every log line as one json object (timestamp, level, logger, message + known extra fields), and configure_logging() installs it on the root logger at startup.
- a request_id contextvar is set once per request in a new middleware in main.py, so every log line touched by that request — main.py, ask.py, wherever — carries the same id without threading it through function signatures.
- ask.py now logs at each stage: question received, sql generated (+ duration), query executed (+ duration, row count), and a warning/error on each failure branch before it becomes an HTTPException.
- middleware also logs one "request completed" line per request with method, path, status code, and total duration, and returns the request id as an X-Request-ID response header.
- added test_logging.py (JSONFormatter in isolation) and test_main.py (the middleware sets a header, different requests get different ids).

## day 9
- found a real gap while reviewing day 8's logging: ask.py only caught `ValueError`, but anthropic's sdk errors (bad key, rate limit, timeout) don't subclass ValueError — they'd have crashed as raw unhandled 500s.
- app/core/llm.py now has its own exception hierarchy — LLMError, LLMConfigError (our fault, not transient), LLMUnavailableError (anthropic's side is down, retryable) — and translates anthropic's sdk exceptions into these inside generate_sql, so ask.py never has to know anthropic's exception types exist.
- ask.py maps them to distinct status codes: 500 for config errors (with a generic client-facing message — the real anthropic error only goes to the log), 503 for unavailable, 502 for everything else.
- added test_llm.py — generate_sql's exception translation had zero coverage before (same gap test_executor.py fixed for run_query on day 7).
