from fastapi import APIRouter
from app.core.faiss_store import remove_document
from app.services.pipeline import remove_financials

router = APIRouter()

@router.delete("/documents/{document_id}")
async def delete_document_vectors(document_id: int):
    removed_vectors = remove_document(document_id)
    remove_financials(document_id)
    return {"documentId": document_id, "removedVectors": removed_vectors}
