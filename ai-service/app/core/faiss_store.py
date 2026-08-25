import numpy as np
import pickle
import os
import logging
import hashlib

logger = logging.getLogger("faiss_store")

DIMENSION = 384
INDEX_PATH = "faiss_index.bin"
METADATA_PATH = "faiss_metadata.pkl"

try:
    import faiss
    from sentence_transformers import SentenceTransformer
    _model = SentenceTransformer("all-MiniLM-L6-v2")
    _has_faiss = True
except Exception as e:
    logger.warning(f"FAISS/SentenceTransformers not fully initialized ({e}). Using numpy fallback vector engine.")
    faiss = None
    _model = None
    _has_faiss = False

_metadata_store: dict[int, dict] = {}
_index = faiss.IndexFlatIP(DIMENSION) if _has_faiss else None

def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector, axis=-1, keepdims=True)
    norm = np.where(norm == 0, 1e-12, norm)
    return vector / norm

def _fallback_embed(text: str) -> np.ndarray:
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    arr = np.frombuffer(seed * (DIMENSION // len(seed) + 1), dtype=np.uint8)[:DIMENSION].astype("float32")
    return _normalize(arr)

def embed_text(text: str) -> np.ndarray:
    if _model is not None:
        vec = _model.encode([text])[0].astype("float32")
        return _normalize(vec)
    return _fallback_embed(text)

def _persist():
    if _has_faiss and _index is not None:
        faiss.write_index(_index, INDEX_PATH)
    with open(METADATA_PATH, "wb") as f:
        # Save metadata without non-serializable objects
        pickle.dump(_metadata_store, f)

def _load_or_init():
    global _index, _metadata_store
    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "rb") as f:
                _metadata_store = pickle.load(f)
        except Exception:
            _metadata_store = {}
            
    if _has_faiss:
        if os.path.exists(INDEX_PATH):
            try:
                _index = faiss.read_index(INDEX_PATH)
                return
            except Exception:
                pass
        _index = faiss.IndexFlatIP(DIMENSION)
        if _metadata_store:
            vectors = np.array([m["vector"] for m in _metadata_store.values()], dtype="float32")
            if len(vectors) > 0:
                _index.add(_normalize(vectors))

_load_or_init()

def add_chunk(document_id: int, chunk_index: int, page_number: int, text: str) -> dict:
    global _index, _metadata_store
    chunk_id = f"doc{document_id}_c{chunk_index}_p{page_number}"
    vector = embed_text(text).reshape(1, -1)
    
    vector_id = len(_metadata_store)
    if _has_faiss and _index is not None:
        _index.add(vector)
        
    meta = {
        "vector_id": vector_id,
        "chunk_id": chunk_id,
        "documentId": document_id,
        "chunk_index": chunk_index,
        "page_number": page_number,
        "text": text,
        "vector": vector[0].tolist()
    }
    _metadata_store[vector_id] = meta
    _persist()
    return meta

def remove_document(document_id: int) -> int:
    global _index, _metadata_store
    remaining = [meta for meta in _metadata_store.values() if meta["documentId"] != document_id]
    removed_count = len(_metadata_store) - len(remaining)
    
    _metadata_store = {}
    if _has_faiss:
        _index = faiss.IndexFlatIP(DIMENSION)
        
    if remaining:
        vectors = np.array([m["vector"] for m in remaining], dtype="float32")
        vectors = _normalize(vectors)
        if _has_faiss and _index is not None:
            _index.add(vectors)
        for i, meta in enumerate(remaining):
            meta["vector_id"] = i
            _metadata_store[i] = meta
            
    _persist()
    return removed_count

def search(query: str, document_ids: list[int] = None, top_k: int = 5) -> list[dict]:
    if not _metadata_store:
        return []
        
    query_vector = embed_text(query).reshape(1, -1)
    allowed_set = set(document_ids) if document_ids else None
    
    if _has_faiss and _index is not None and _index.ntotal > 0:
        k_search = min(_index.ntotal, max(top_k * 10, 100))
        distances, indices = _index.search(query_vector, k_search)
        results = []
        for idx, score in zip(indices[0], distances[0]):
            if idx in _metadata_store:
                meta = _metadata_store[idx]
                if allowed_set is None or meta["documentId"] in allowed_set:
                    res = dict(meta)
                    res["score"] = float(score)
                    results.append(res)
                    if len(results) >= top_k:
                        break
        return results
    else:
        # Fallback numpy dot product search
        scored = []
        q_vec = query_vector[0]
        for meta in _metadata_store.values():
            if allowed_set is None or meta["documentId"] in allowed_set:
                doc_vec = np.array(meta["vector"], dtype="float32")
                score = float(np.dot(q_vec, doc_vec))
                res = dict(meta)
                res["score"] = score
                scored.append(res)
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

def get_chunks_for_document(document_id: int) -> list[dict]:
    return [
        dict(meta)
        for meta in _metadata_store.values()
        if meta["documentId"] == document_id
    ]