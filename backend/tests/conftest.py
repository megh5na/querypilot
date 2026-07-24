# shared pytest fixtures for /ask route tests.
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(): # fastapi test client
    return TestClient(app)


@pytest.fixture
def mock_generate_sql(): # replace llm call with a controllable mock — no real anthropic requests
    with patch("app.api.routes.ask.generate_sql", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_run_query(): # replace db execution with a controllable mock — no postgres needed
    with patch("app.api.routes.ask.run_query", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_get_schema_description(): # replace schema introspection — avoids real postgres + event loop issues
    with patch("app.api.routes.ask.get_schema_description", new_callable=AsyncMock) as mock:
        mock.return_value = 'Table "Album": AlbumId (integer), Title (character varying)'
        yield mock
