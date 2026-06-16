# endpoint to get the schema description

from fastapi import APIRouter # groups related routes together
from app.db.introspect import get_schema_description

router = APIRouter()

@router.get("/schema")
async def schema():
    return {"schema": await get_schema_description()} # returns the schema description

# example response: "schema": "Table \"album\": albumid (integer), title (character varying), artistid (integer)\nTable \"artist\": artistid (integer), name (character varying)\n..."