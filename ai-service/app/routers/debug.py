from fastapi import APIRouter
from app.core.faiss_store import get_chunks_for_document
from app.services.pipeline import get_financials

router = APIRouter()

@router.get("/debug/chunks/{document_id}")
async def debug_chunks(document_id: int):
    chunks = get_chunks_for_document(document_id)
    return {"documentId": document_id, "chunkCount": len(chunks), "chunks": chunks}

@router.get("/debug/financials/{document_id}")
async def debug_financials(document_id: int):
    return get_financials(document_id)