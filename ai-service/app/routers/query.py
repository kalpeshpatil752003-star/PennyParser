from fastapi import APIRouter
from pydantic import BaseModel
from app.services.rag import generate_answer

router = APIRouter()

class QueryRequest(BaseModel):
    question: str
    documentIds: list[int] = []

@router.post("/query")
async def query(request: QueryRequest):
    return await generate_answer(request.question, request.documentIds)