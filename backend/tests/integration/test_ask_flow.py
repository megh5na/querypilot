# POST /ask through the whole stack: real validator, row cap, read-only role and postgres.
# only generate_sql is stubbed (mock_generate_sql from tests/conftest.py) — so these tests
# decide what "the model" returned and check what the rest of the system does with it.

import pytest

pytestmark = pytest.mark.integration


async def ask(api, question="q"):
    return await api.post("/ask", json={"question": question})


async def test_happy_path_returns_real_data(api, mock_generate_sql):
    mock_generate_sql.return_value = "SELECT COUNT(*) AS n FROM album"

    response = await ask(api, "how many albums?")

    assert response.status_code == 200
    assert response.json()["rows"] == [{"n": 347}]


async def test_real_schema_is_what_the_llm_receives(api, mock_generate_sql):
    mock_generate_sql.return_value = "SELECT 1"

    await ask(api)

    question, schema = mock_generate_sql.call_args.args
    assert 'Table "album"' in schema and 'Table "track"' in schema


async def test_destructive_sql_is_rejected_and_data_survives(api, mock_generate_sql):
    mock_generate_sql.return_value = "DROP TABLE album"

    response = await ask(api)
    assert response.status_code == 422

    mock_generate_sql.return_value = "SELECT COUNT(*) AS n FROM album"
    assert (await ask(api)).json()["rows"] == [{"n": 347}]  # still there


async def test_oversized_result_returns_413(api, mock_generate_sql):
    mock_generate_sql.return_value = "SELECT * FROM track"

    assert (await ask(api)).status_code == 413


async def test_wrong_table_name_returns_400_with_the_sql(api, mock_generate_sql):
    mock_generate_sql.return_value = 'SELECT * FROM "Album"'  # what the old prompt made the model write

    response = await ask(api)

    assert response.status_code == 400
    assert response.json()["detail"]["sql"] == 'SELECT * FROM "Album"'


async def test_schema_endpoint_serves_the_real_schema(api):
    response = await api.get("/schema")

    assert response.status_code == 200
    assert 'Table "invoice_line"' in response.json()["schema"]
