from fastapi import APIRouter
from app.core.faiss_store import remove_document

router = APIRouter()

@router.delete("/documents/{document_id}")
async def delete_document_vectors(document_id: int):
    removed_vectors = remove_document(document_id)
    return {"documentId": document_id, "removedVectors": removed_vectors}
