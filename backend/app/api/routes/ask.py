from fastapi import APIRouter
from pydantic import BaseModel
from app.db.introspect import get_schema_description
from app.core.llm import generate_sql

router = APIRouter()

class AskRequest(BaseModel): # expect question in json format
    question: str

@router.post("/ask") # endpoint to ask a question
async def ask(req: AskRequest):
    schema_description = await get_schema_description() 
    sql = await generate_sql(req.question, schema_description) # send question and schema description to llm to get sql back
    return {"question": req.question, "sql": sql} # return question and sql