from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncpg
from app.core.executor import run_query, SQLValidationError
from app.db.introspect import get_schema_description
from app.core.llm import generate_sql

router = APIRouter()

class AskRequest(BaseModel): # expect question in json format
    question: str

class AskResponse(BaseModel): # response to ask request
    question: str
    sql: str
    rows: list[dict]

@router.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    schema_description = await get_schema_description() # get schema description

    try:
        sql = await generate_sql(req.question, schema_description) # generate sql
    except ValueError as e:
        raise HTTPException(status_code=502, detail={"error": str(e)}) # if error, raise HTTPException

    try:
        rows = await run_query(sql) # execute sql
    except SQLValidationError as e:
        raise HTTPException(status_code=422, detail={"sql": sql, "error": str(e)}) # if sql validation error, raise HTTPException
    except asyncpg.PostgresError as e:
        raise HTTPException(status_code=400, detail={"sql": sql, "error": str(e)}) # if postgres error, raise HTTPException

    return AskResponse(question=req.question, sql=sql, rows=rows) # return question, sql, and rows