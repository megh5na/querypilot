from anthropic import AsyncAnthropic
from app.config import settings

client = AsyncAnthropic(api_key=settings.anthropic_api_key)

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
    'Table and column names are PascalCase and must be double-quoted, e.g. "Album"."Title". '
    "Generate only read-only SELECT statements. Always call the submit_sql tool."
)

async def generate_sql(question: str, schema_description: str) -> str:
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
    for block in message.content:
        if block.type == "tool_use":
            return block.input["sql"]
    raise ValueError("Model did not return SQL")