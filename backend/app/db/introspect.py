# reading postgres schema and turn it into plain text summary

from app.db.session import get_pool

async def get_schema_description() -> str:
    pool = await get_pool()  # get pool from session.py
    rows = await pool.fetch("""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns  
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """) # reads from information_schema.columns
    tables: dict[str, list[str]] = {}
    for r in rows:
        tables.setdefault(r["table_name"], []).append(f'{r["column_name"]} ({r["data_type"]})')
    return "\n".join(f'Table "{t}": {", ".join(cols)}' for t, cols in tables.items())