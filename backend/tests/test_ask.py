# tests for POST /ask. mocks from conftest.py replace schema introspection, llm + db — no api key or postgres needed.

import asyncpg

from app.core.validator import SQLValidationError


def test_ask_happy_path(client, mock_generate_sql, mock_run_query): # 200 — question, sql, and rows returned
    mock_generate_sql.return_value = 'SELECT COUNT(*) AS count FROM "Album"'
    mock_run_query.return_value = [{"count": 347}]

    response = client.post("/ask", json={"question": "How many albums are there?"})

    assert response.status_code == 200
    body = response.json()
    assert body["question"] == "How many albums are there?"
    assert body["sql"] == 'SELECT COUNT(*) AS count FROM "Album"'
    assert body["rows"] == [{"count": 347}]


def test_ask_llm_failure_returns_502(client, mock_generate_sql, mock_run_query): # 502 — llm error, run_query never called
    mock_generate_sql.side_effect = ValueError("Model did not return SQL")

    response = client.post("/ask", json={"question": "anything"})

    assert response.status_code == 502
    assert "error" in response.json()["detail"]
    mock_run_query.assert_not_called()


def test_ask_validation_failure_returns_422(client, mock_generate_sql, mock_run_query): # 422 — sql validation error
    mock_generate_sql.return_value = "DROP TABLE albums"
    mock_run_query.side_effect = SQLValidationError("Only SELECT statements are permitted, got Drop")

    response = client.post("/ask", json={"question": "delete everything"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "sql" in detail
    assert "error" in detail


def test_ask_database_error_returns_400(client, mock_generate_sql, mock_run_query): # 400 — postgres execution error
    mock_generate_sql.return_value = 'SELECT * FROM "NonExistentTable"'
    mock_run_query.side_effect = asyncpg.UndefinedTableError("relation does not exist")

    response = client.post("/ask", json={"question": "query a missing table"})

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "sql" in detail


def test_ask_missing_question_field_returns_422(client): # 422 — fastapi request validation, no mocks needed
    response = client.post("/ask", json={})
    assert response.status_code == 422


def test_ask_empty_question(client, mock_generate_sql, mock_run_query): # empty string is valid input
    mock_generate_sql.return_value = "SELECT 1"
    mock_run_query.return_value = [{"?column?": 1}]

    response = client.post("/ask", json={"question": ""})
    assert response.status_code == 200
