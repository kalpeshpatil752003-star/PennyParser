from fastapi import APIRouter
from app.core.faiss_store import remove_document
from app.services.rag import remove_line_items

router = APIRouter()

@router.delete("/documents/{document_id}")
async def delete_document_vectors(document_id: int):
    removed_vectors = remove_document(document_id)
    remove_line_items(document_id)
    return {"documentId": document_id, "removedVectors": removed_vectors}
