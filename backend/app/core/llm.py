from anthropic import (
    AsyncAnthropic,
    APIError,
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    PermissionDeniedError,
    RateLimitError,
)
from app.config import settings

client = AsyncAnthropic(api_key=settings.anthropic_api_key)


class LLMError(Exception): # base: something went wrong turning a question into sql
    pass


class LLMConfigError(LLMError): # our side is misconfigured (bad api key, no model access) 
    pass


class LLMUnavailableError(LLMError): # anthropic is temporarily unreachable/overloaded — safe to retry
    pass

SQL_TOOL = {
    "name": "submit_sql",
    "description": "Submit one read-only PostgreSQL SELECT query that answers the question.",
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "A single PostgreSQL SELECT statement."}
        },
        "required": ["sql"],
    },
}

SYSTEM = (
    "You translate questions into PostgreSQL SELECT queries. "
    "Use table and column names exactly as they appear in the schema, including their case. "
    "Generate only read-only SELECT statements. Always call the submit_sql tool."
)

async def generate_sql(question: str, schema_description: str) -> str:
    # translate anthropic sdk exceptions into our own hierarchy here, at the
    # boundary - callers (ask.py) shouldn't need to know anthropic's exception types to decide how to respond.
    try:
        message = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM,
            tools=[SQL_TOOL],
            tool_choice={"type": "tool", "name": "submit_sql"},
            messages=[{
                "role": "user",
                "content": f"Database schema:\n{schema_description}\n\nQuestion: {question}",
            }],
        )
    except (AuthenticationError, PermissionDeniedError) as e:
        raise LLMConfigError(f"Anthropic API credentials rejected: {e}") from e
    except (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError) as e:
        raise LLMUnavailableError(f"Anthropic API temporarily unavailable: {e}") from e
    except APIError as e:
        raise LLMError(f"Anthropic API request failed: {e}") from e

    for block in message.content:
        if block.type == "tool_use":
            return block.input["sql"]
    raise LLMError("Model did not return SQL")