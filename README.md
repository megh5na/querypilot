# QueryPilot

Ask a question in plain English, get rows back. QueryPilot has Claude write the SQL, checks it, runs it against Postgres, and returns the query along with the results.

Backend only for now (FastAPI, asyncpg, sqlglot). It runs against the Chinook sample database.

## How a request flows

```
POST /ask → rate limit → read schema → Claude writes SQL → validate → cap rows → run → rows
```

The model's SQL is treated as untrusted input. Four independent checks sit between it and the data:

1. **Parse check:** sqlglot must see exactly one `SELECT`. Anything else gets a 422.
2. **Row cap:** queries are limited to 1000 rows. A bigger result gets a 413 instead of a silently truncated answer.
3. **Read-only role:** the query runs as a Postgres user that can only `SELECT`.
4. **Timeout:** 5 seconds per statement.

The schema Claude sees is read from the live database, so there are no table names hardcoded in the prompt.

## Run it

You need Python 3.12+, [uv](https://docs.astral.sh/uv/), Docker, and an Anthropic API key.

```bash
# database
docker run --name querypilot-db -d -p 5432:5432 \
  -e POSTGRES_USER=querypilot -e POSTGRES_PASSWORD=change-me -e POSTGRES_DB=chinook \
  pgvector/pgvector:pg16
psql postgresql://querypilot:change-me@localhost:5432/chinook -f chinook.sql   # Chinook sample data
psql postgresql://querypilot:change-me@localhost:5432/chinook -c "
  CREATE ROLE querypilot_ro LOGIN PASSWORD 'change-me-too';
  GRANT SELECT ON ALL TABLES IN SCHEMA public TO querypilot_ro;"

# app
cd backend
cp .env.example .env     # fill in the three values
uv sync
uv run uvicorn app.main:app --reload
```

Docs are at http://localhost:8000/docs. Try it:

```bash
curl -X POST localhost:8000/ask -H 'content-type: application/json' \
  -d '{"question": "Which 3 artists have the most albums?"}'
```

## Endpoints

| | |
|---|---|
| `POST /ask` | `{"question": "..."}` → `{question, sql, rows}` |
| `GET /schema` | the schema description sent to the model |
| `GET /health` | liveness check |

`/ask` errors: `413` result too large, `422` rejected SQL, `400` Postgres error, `429` rate limited (check `Retry-After`), `502`/`503` model failure or outage, `500` server misconfigured.

Every response carries an `X-Request-ID` header, and the JSON logs use the same ID, so you can trace one request through the logs.

## Configuration

Set in `backend/.env`:

| Variable | |
|---|---|
| `DATABASE_URL` | read-write connection, used only to read the schema |
| `DATABASE_URL_RO` | read-only connection, used for generated SQL |
| `ANTHROPIC_API_KEY` | |
| `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS` | optional, default 10 per 60s per IP |

## Tests

```bash
cd backend
uv run pytest                      # everything
uv run pytest -m "not integration" # fast, no database needed
```

Integration tests use the real database with the model stubbed. They skip themselves if Postgres isn't reachable.

## Known limits

No auth. Rate-limit counters are per process, so they won't hold across multiple workers. No frontend or Dockerfile yet.
