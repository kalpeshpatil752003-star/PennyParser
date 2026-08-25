import faiss
import numpy as np
import pickle
import os
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2")
DIMENSION = 384

INDEX_PATH = "faiss_index.bin"
METADATA_PATH = "faiss_metadata.pkl"

if os.path.exists(INDEX_PATH) and os.path.exists(METADATA_PATH):
    _index = faiss.read_index(INDEX_PATH)
    with open(METADATA_PATH, "rb") as f:
        _metadata_store: dict[int, dict] = pickle.load(f)
else:
    _index = faiss.IndexFlatL2(DIMENSION)
    _metadata_store: dict[int, dict] = {}

def _persist():
    faiss.write_index(_index, INDEX_PATH)
    with open(METADATA_PATH, "wb") as f:
        pickle.dump(_metadata_store, f)

def embed_text(text: str) -> np.ndarray:
    return _model.encode([text])[0]

def add_chunk(document_id: int, page_number: int, text: str) -> int:
    vector = embed_text(text).astype("float32").reshape(1, -1)
    vector_id = _index.ntotal
    _index.add(vector)
    _metadata_store[vector_id] = {"documentId": document_id, "page_number": page_number, "text": text}
    _persist()
    return vector_id

def search(query: str, top_k: int = 5) -> list[dict]:
    if _index.ntotal == 0:
        return []
    query_vector = embed_text(query).astype("float32").reshape(1, -1)
    distances, indices = _index.search(query_vector, top_k)
    results = []
    for idx in indices[0]:
        if idx in _metadata_store:
            results.append(_metadata_store[idx])
    return results

def get_chunks_for_document(document_id: int) -> list[dict]:
    return [
        {"vector_id": vid, **meta}
        for vid, meta in _metadata_store.items()
        if meta["documentId"] == document_id
    ]