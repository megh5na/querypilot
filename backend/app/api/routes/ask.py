from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncpg
from app.core.executor import run_query
from app.db.introspect import get_schema_description
from app.core.llm import generate_sql

router = APIRouter()

class AskRequest(BaseModel): # expect question in json format
    question: str

@router.post("/ask") # endpoint to ask a question
async def ask(req: AskRequest):
    schema_description = await get_schema_description()
    sql = await generate_sql(req.question, schema_description) # send question and schema description to llm to get sql back
    try:
        rows = await run_query(sql)
    except asyncpg.PostgresError as e:
        raise HTTPException(status_code=400, detail={"sql": sql, "error": str(e)}) # if error, raise HTTPException
    return {"question": req.question, "sql": sql, "rows": rows} # return question, sql, and rows