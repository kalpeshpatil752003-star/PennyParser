import re
import os
import pickle
import logging
import httpx
from app.core.config import OLLAMA_URL, MODEL_NAME
from app.core.faiss_store import search
from app.services.financial_reasoning import compute_financial_reasoning_insights

logger = logging.getLogger("rag")

LINE_ITEMS_STORE_PATH = "line_items_store.pkl"

# Module-level store for structured extraction per document.
# Populated by pipeline.py after extraction completes.
# Persisted to disk so it survives server restarts.
_document_line_items: dict[int, dict] = {}


def _persist_line_items():
    """Save line_items store to disk."""
    try:
        with open(LINE_ITEMS_STORE_PATH, "wb") as f:
            pickle.dump(_document_line_items, f)
    except Exception as e:
        logger.error(f"Failed to persist line_items store: {e}")


def _load_line_items():
    """Load line_items store from disk on startup."""
    global _document_line_items
    if os.path.exists(LINE_ITEMS_STORE_PATH):
        try:
            with open(LINE_ITEMS_STORE_PATH, "rb") as f:
                loaded = pickle.load(f)
                if isinstance(loaded, dict):
                    _document_line_items = loaded
                    logger.info(f"Loaded line_items store for {len(loaded)} documents from disk")
        except Exception as e:
            logger.error(f"Failed to load line_items store: {e}")
            _document_line_items = {}


# Load on import
_load_line_items()


def store_line_items(document_id: int, line_items: dict):
    """Called by pipeline.py to cache structured extraction results for RAG reasoning."""
    _document_line_items[document_id] = line_items
    _persist_line_items()
    logger.info(f"[doc {document_id}] Stored {len(line_items)} line items for RAG reasoning")


def remove_line_items(document_id: int):
    """Called when a document is deleted."""
    if document_id in _document_line_items:
        del _document_line_items[document_id]
        _persist_line_items()


def get_line_items(document_ids: list[int] = None) -> dict:
    """Returns merged line_items for the requested document IDs."""
    if not document_ids:
        merged = {}
        for items in _document_line_items.values():
            merged.update(items)
        return merged

    merged = {}
    for doc_id in document_ids:
        items = _document_line_items.get(doc_id, {})
        merged.update(items)
    return merged


def build_prompt(question: str, chunks: list[dict], reasoning_block: str = "") -> str:
    context_blocks = []
    for c in chunks:
        context_blocks.append(f"[Fact {c['chunk_id']}] (Page {c['page_number']}): {c['text']}")

    context_str = "\n\n".join(context_blocks)
    if reasoning_block:
        context_str = f"{reasoning_block}\n\nDOCUMENT FACTS:\n{context_str}"

    return f"""You are an expert financial research assistant. Answer the user's question using ONLY the verified context below.

STRICT ACCURACY RULES:
1. Do NOT invent arithmetic relationships, multiples, or calculations unsupported by the context.
2. Three-month (quarterly) figures represent that 3-month period alone (e.g., Q2).
3. Six-month (year-to-date / 6M) figures represent the combined total of Q1 + Q2. The six-month total is NOT simply twice the three-month total.
4. Whenever you mention a financial figure, attach its exact page citation in parentheses, e.g. (Page 1) or (Page 5).
5. If facts come from multiple pages (e.g. Page 1 and Page 5), cite EACH page separately for its respective fact.
6. If a DETERMINISTIC MATH block is provided above, you MUST use those exact values. Do NOT recalculate or override them.

VERIFIED CONTEXT:
{context_str}

QUESTION: {question}

ANSWER:"""


def _build_fallback_answer(question: str, reasoning_block: str, retrieved: list[dict]) -> str:
    """
    Produces a substantive answer from the deterministic reasoning block and retrieved chunks
    when the LLM is unavailable. This is NOT just a list of page citations.
    """
    sections = []

    # 1. The deterministic reasoning block IS the primary answer content when LLM is offline
    if reasoning_block:
        sections.append(reasoning_block)

    # 2. Add relevant context excerpts with proper page citations
    if retrieved:
        sections.append("\nRelevant source excerpts from the uploaded document:")
        for c in retrieved[:3]:
            text_preview = c["text"][:300].strip()
            sections.append(f"\n(Page {c['page_number']}): {text_preview}")

    if not sections:
        return "I don't have enough information in the uploaded documents to answer that."

    return "\n".join(sections)


async def generate_answer(question: str, document_ids: list[int] = None) -> dict:
    retrieved = search(query=question, document_ids=document_ids, top_k=5)

    if not retrieved:
        return {"answer": "I don't have enough information in the uploaded documents to answer that.", "citations": []}

    # Get structured line items for the requested documents
    line_items = get_line_items(document_ids)
    reasoning_block = compute_financial_reasoning_insights(question, line_items) if line_items else ""

    logger.info(f"RAG query: question='{question[:80]}...', retrieved={len(retrieved)} chunks, "
                f"line_items={len(line_items)} metrics, reasoning_block_len={len(reasoning_block)}")

    prompt = build_prompt(question, retrieved, reasoning_block)
    answer_text = ""
    llm_succeeded = False

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(OLLAMA_URL, json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0
                }
            })
            response.raise_for_status()
            answer_text = response.json().get("response", "").strip()
            llm_succeeded = bool(answer_text)
            logger.info(f"Ollama LLM response length: {len(answer_text)}")
    except Exception as e:
        logger.warning(f"Ollama LLM call failed or unavailable ({e}). Using deterministic fallback.")

    if not llm_succeeded:
        answer_text = _build_fallback_answer(question, reasoning_block, retrieved)
        logger.info(f"Fallback answer length: {len(answer_text)}")

    # Fact-level citation mapping
    chunk_map = {c["chunk_id"]: c for c in retrieved}
    cited_chunks = []

    # 1. Match explicit chunk IDs
    for chunk_id, c in chunk_map.items():
        if chunk_id in answer_text:
            cited_chunks.append(c)

    # 2. Match page numbers mentioned in text (Page 5, pp. 5, p. 5, [Page 5])
    page_matches = re.findall(r"(?:Page|pp?\.?|p\.)\s*(\d+)", answer_text, re.IGNORECASE)
    page_numbers_in_answer = set(map(int, page_matches)) if page_matches else set()

    for c in retrieved:
        if c["page_number"] in page_numbers_in_answer:
            cited_chunks.append(c)

    # 3. If no explicit page cited in text, only pick the top relevant retrieved chunk(s)
    if not cited_chunks:
        cited_chunks = retrieved[:2]

    seen = set()
    citations = []
    for c in cited_chunks:
        key = (c["documentId"], c["page_number"])
        if key not in seen:
            seen.add(key)
            citations.append({"documentId": c["documentId"], "page": c["page_number"]})

    citations.sort(key=lambda c: (c["documentId"], c["page"]))

    logger.info(f"Final answer length: {len(answer_text)}, citations: {citations}")
    return {"answer": answer_text, "citations": citations}