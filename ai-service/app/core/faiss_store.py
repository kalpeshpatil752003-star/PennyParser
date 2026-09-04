import os
import pickle
import logging
import re
import numpy as np

logger = logging.getLogger("faiss_store")

DIMENSION = 384
INDEX_PATH = "faiss_index.bin"
METADATA_PATH = "faiss_metadata.pkl"

_model = None
_has_faiss = False
_embedding_available = False

try:
    import faiss
    from sentence_transformers import SentenceTransformer
    _model = SentenceTransformer("all-MiniLM-L6-v2")
    _has_faiss = True
    _embedding_available = True
    logger.info("SentenceTransformer and FAISS successfully loaded.")
except Exception as e:
    logger.error(
        f"CRITICAL: SentenceTransformers or FAISS failed to initialize ({e}). "
        "Semantic embeddings are unavailable. System will use keyword-based retrieval."
    )
    faiss = None
    _model = None
    _has_faiss = False
    _embedding_available = False

_metadata_store: dict[int, dict] = {}
_index = faiss.IndexFlatIP(DIMENSION) if _has_faiss else None


def is_semantic_embedding_available() -> bool:
    return _embedding_available


def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector, axis=-1, keepdims=True)
    norm = np.where(norm == 0, 1e-12, norm)
    return vector / norm


def embed_text(text: str) -> np.ndarray:
    """Embeds single text string using SentenceTransformer."""
    if _model is not None:
        vec = _model.encode([text])[0].astype("float32")
        return _normalize(vec)
    # Zero vector fallback for metadata storage when model is unavailable
    return np.zeros((DIMENSION,), dtype="float32")


def embed_texts_batch(texts: list[str]) -> np.ndarray:
    """Embeds a batch of texts in a single pass."""
    if _model is not None and texts:
        vecs = _model.encode(texts, show_progress_bar=False, batch_size=32).astype("float32")
        return _normalize(vecs)
    return np.zeros((len(texts), DIMENSION), dtype="float32")


def _persist():
    try:
        if _has_faiss and _index is not None:
            faiss.write_index(_index, INDEX_PATH)
        with open(METADATA_PATH, "wb") as f:
            pickle.dump(_metadata_store, f)
    except Exception as e:
        logger.error(f"Failed to persist FAISS index/metadata: {e}")


def _load_or_init():
    global _index, _metadata_store
    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "rb") as f:
                loaded = pickle.load(f)
                if isinstance(loaded, dict):
                    _metadata_store = loaded
        except Exception as e:
            logger.error(f"Error reading metadata store: {e}")
            _metadata_store = {}

    if _has_faiss:
        _index = faiss.IndexFlatIP(DIMENSION)
        valid_vectors = []
        clean_store = {}
        if _metadata_store:
            sorted_keys = sorted(_metadata_store.keys())
            for k in sorted_keys:
                meta = _metadata_store[k]
                if isinstance(meta, dict) and "vector" in meta and meta["vector"] is not None:
                    new_id = len(clean_store)
                    meta["vector_id"] = new_id
                    clean_store[new_id] = meta
                    valid_vectors.append(meta["vector"])

            _metadata_store = clean_store
            if valid_vectors:
                vectors = np.array(valid_vectors, dtype="float32")
                _index.add(_normalize(vectors))
            logger.info(f"Rebuilt FAISS IndexFlatIP with {len(valid_vectors)} vectors synced to metadata store.")


_load_or_init()


def add_chunks_batch(document_id: int, chunks: list[dict]) -> list[dict]:
    """
    Embeds and stores all chunks for a document in a single batch,
    persisting to disk once (O(N) instead of O(N^2)).
    """
    global _index, _metadata_store
    if not chunks:
        return []

    texts = [c["text"] for c in chunks]
    vectors = embed_texts_batch(texts)

    results_meta = []
    start_id = len(_metadata_store)

    if _has_faiss and _index is not None and _embedding_available:
        _index.add(vectors)

    for i, chunk in enumerate(chunks):
        vector_id = start_id + i
        chunk_index = chunk.get("chunk_index", i)
        page_number = chunk.get("page_number", 1)
        chunk_id = f"doc{document_id}_c{chunk_index}_p{page_number}"
        vec_list = vectors[i].tolist() if _embedding_available else []

        meta = {
            "vector_id": vector_id,
            "chunk_id": chunk_id,
            "documentId": document_id,
            "chunk_index": chunk_index,
            "page_number": page_number,
            "text": chunk["text"],
            "vector": vec_list
        }
        _metadata_store[vector_id] = meta
        results_meta.append(meta)

    _persist()
    return results_meta


def add_chunk(document_id: int, chunk_index: int, page_number: int, text: str) -> dict:
    """Single-chunk backward compatibility wrapper."""
    res = add_chunks_batch(document_id, [{"chunk_index": chunk_index, "page_number": page_number, "text": text}])
    return res[0] if res else {}


def remove_document(document_id: int) -> int:
    global _index, _metadata_store
    remaining = [meta for meta in _metadata_store.values() if meta.get("documentId") != document_id]
    removed_count = len(_metadata_store) - len(remaining)

    _metadata_store = {}
    if _has_faiss:
        _index = faiss.IndexFlatIP(DIMENSION)

    if remaining:
        clean_vectors = []
        for i, meta in enumerate(remaining):
            meta["vector_id"] = i
            _metadata_store[i] = meta
            if "vector" in meta and meta["vector"]:
                clean_vectors.append(meta["vector"])

        if _has_faiss and _index is not None and clean_vectors and _embedding_available:
            vectors = np.array(clean_vectors, dtype="float32")
            _index.add(_normalize(vectors))

    _persist()
    return removed_count


def _keyword_search(query: str, document_ids: list[int] = None, top_k: int = 5) -> list[dict]:
    """Token-overlap BM25-style keyword search fallback."""
    query_tokens = set(re.findall(r"\w+", query.lower()))
    if not query_tokens:
        return []

    allowed_set = set(document_ids) if document_ids else None
    scored = []

    for meta in _metadata_store.values():
        if allowed_set is not None and meta.get("documentId") not in allowed_set:
            continue

        text_lower = meta.get("text", "").lower()
        chunk_tokens = set(re.findall(r"\w+", text_lower))
        if not chunk_tokens:
            continue

        overlap = len(query_tokens.intersection(chunk_tokens))
        score = overlap / (len(query_tokens) + 1e-5)
        if score > 0:
            res = dict(meta)
            res["score"] = float(score)
            scored.append(res)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def search(query: str, document_ids: list[int] = None, top_k: int = 5) -> list[dict]:
    if not _metadata_store:
        return []

    allowed_set = set(document_ids) if document_ids else None

    # If semantic model is available and FAISS is ready, perform dense vector search
    if _embedding_available and _has_faiss and _index is not None and _index.ntotal > 0:
        query_vector = embed_text(query).reshape(1, -1)
        k_search = min(_index.ntotal, max(top_k * 10, 100))
        distances, indices = _index.search(query_vector, k_search)
        results = []
        for idx, score in zip(indices[0], distances[0]):
            if idx in _metadata_store:
                meta = _metadata_store[idx]
                if allowed_set is None or meta.get("documentId") in allowed_set:
                    res = dict(meta)
                    res["score"] = float(score)
                    results.append(res)
                    if len(results) >= top_k:
                        break
        return results

    # Fallback to deterministic keyword retrieval
    logger.warning("Using keyword search fallback for RAG retrieval.")
    return _keyword_search(query, document_ids=document_ids, top_k=top_k)


def get_chunks_for_document(document_id: int) -> list[dict]:
    return [
        dict(meta)
        for meta in _metadata_store.values()
        if meta.get("documentId") == document_id
    ]