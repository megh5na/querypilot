import logging
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncpg
from app.core.executor import run_query, SQLValidationError, ResultTooLargeError
from app.db.introspect import get_schema_description
from app.core.llm import generate_sql, LLMError, LLMConfigError, LLMUnavailableError

router = APIRouter()
logger = logging.getLogger(__name__)

class AskRequest(BaseModel): # expect question in json format
    question: str

class AskResponse(BaseModel): # response to ask request
    question: str
    sql: str
    rows: list[dict]

@router.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    logger.info("ask received", extra={"question": req.question})
    schema_description = await get_schema_description() # get schema description

    start = time.monotonic()
    try:
        sql = await generate_sql(req.question, schema_description) # generate sql
    except LLMConfigError as e:
        # our fault (bad api key, no model access), just log it server-side
        logger.error("llm configuration error", extra={"sql_error": str(e)})
        raise HTTPException(status_code=500, detail={"error": "SQL generation is misconfigured"})
    except LLMUnavailableError as e:
        # anthropic's side is down/overloaded — safe to retry, so say so
        logger.warning("llm unavailable", extra={"sql_error": str(e)})
        raise HTTPException(status_code=503, detail={"error": "SQL generation is temporarily unavailable"})
    except LLMError as e:
        logger.warning("sql generation failed", extra={"sql_error": str(e)})
        raise HTTPException(status_code=502, detail={"error": str(e)}) # if error, raise HTTPException
    logger.info(
        "sql generated",
        extra={"sql": sql, "duration_ms": round((time.monotonic() - start) * 1000, 1)},
    )

    start = time.monotonic()
    try:
        rows = await run_query(sql) # execute sql
    except SQLValidationError as e:
        logger.warning("sql validation failed", extra={"sql": sql, "sql_error": str(e)})
        raise HTTPException(status_code=422, detail={"sql": sql, "error": str(e)}) # if sql validation error, raise HTTPException
    except ResultTooLargeError as e:
        logger.warning("result too large", extra={"sql": sql, "sql_error": str(e)})
        raise HTTPException(status_code=413, detail={"sql": sql, "error": str(e)}) # if result exceeds row cap, raise HTTPException
    except asyncpg.PostgresError as e:
        logger.error("query execution failed", extra={"sql": sql, "sql_error": str(e)})
        raise HTTPException(status_code=400, detail={"sql": sql, "error": str(e)}) # if postgres error, raise HTTPException
    logger.info(
        "query executed",
        extra={"row_count": len(rows), "duration_ms": round((time.monotonic() - start) * 1000, 1)},
    )

    return AskResponse(question=req.question, sql=sql, rows=rows) # return question, sql, and rows
