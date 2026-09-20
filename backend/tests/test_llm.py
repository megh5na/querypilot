# tests for generate_sql's exception translation 
# test_ask.py mocks generate_sql entirely, so this logic had no coverage
# there, same gap test_executor.py fixed for run_query.

import httpx
import pytest
from anthropic import (
    APIConnectionError,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)
from unittest.mock import AsyncMock, patch

from app.core.llm import generate_sql, LLMError, LLMConfigError, LLMUnavailableError

_request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _status_error(cls, status_code):
    return cls("boom", response=httpx.Response(status_code, request=_request), body=None)


async def test_generate_sql_returns_sql_from_tool_use():
    message = AsyncMock()
    message.content = [type("Block", (), {"type": "tool_use", "input": {"sql": "SELECT 1"}})()]

    with patch("app.core.llm.client.messages.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = message
        result = await generate_sql("anything", "schema")

    assert result == "SELECT 1"


async def test_generate_sql_raises_llm_error_when_no_tool_use_block():
    message = AsyncMock()
    message.content = []  # model responded but never called the tool

    with patch("app.core.llm.client.messages.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = message
        with pytest.raises(LLMError, match="did not return SQL"):
            await generate_sql("anything", "schema")


async def test_generate_sql_wraps_authentication_error_as_config_error():
    with patch("app.core.llm.client.messages.create", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = _status_error(AuthenticationError, 401)
        with pytest.raises(LLMConfigError):
            await generate_sql("anything", "schema")


async def test_generate_sql_wraps_rate_limit_as_unavailable():
    with patch("app.core.llm.client.messages.create", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = _status_error(RateLimitError, 429)
        with pytest.raises(LLMUnavailableError):
            await generate_sql("anything", "schema")


async def test_generate_sql_wraps_connection_error_as_unavailable():
    with patch("app.core.llm.client.messages.create", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = APIConnectionError(request=_request)
        with pytest.raises(LLMUnavailableError):
            await generate_sql("anything", "schema")


async def test_generate_sql_wraps_other_api_errors_as_llm_error():
    with patch("app.core.llm.client.messages.create", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = _status_error(BadRequestError, 400)
        with pytest.raises(LLMError):
            await generate_sql("anything", "schema")
