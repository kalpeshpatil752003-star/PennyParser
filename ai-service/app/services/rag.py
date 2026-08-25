import re
import logging
import httpx
from app.core.config import OLLAMA_URL, MODEL_NAME
from app.core.faiss_store import search

logger = logging.getLogger("rag")

def build_prompt(question: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        f"[Chunk {c['chunk_id']}] (Page {c['page_number']}): {c['text']}" for c in chunks
    )
    return f"""You are a financial research assistant. Answer the question using ONLY the context below.

STRICT FORMATTING RULES:
- Break your answer into short paragraphs, one idea per paragraph.
- Reference the chunk ID in brackets for statements, e.g. [Chunk {chunks[0]['chunk_id'] if chunks else 'id'}].
- After EVERY paragraph, include the page number(s), e.g. (Page 12).
- If the answer isn't in the context, say you don't have enough information and cite nothing.

Context:
{context}

Question: {question}

Answer:"""

async def generate_answer(question: str, document_ids: list[int] = None) -> dict:
    retrieved = search(query=question, document_ids=document_ids, top_k=5)

    if not retrieved:
        return {"answer": "I don't have enough information in the uploaded documents to answer that.", "citations": []}

    prompt = build_prompt(question, retrieved)
    answer_text = ""

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(OLLAMA_URL, json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False
            })
            response.raise_for_status()
            answer_text = response.json().get("response", "").strip()
    except Exception as e:
        logger.warning(f"Ollama LLM call failed or unavailable ({e}). Generating grounded fallback answer from retrieved context.")
        # Fallback to grounded summary of top retrieved chunks if Ollama service is not running locally
        top_chunks_summary = "\n".join([f"• Page {c['page_number']}: {c['text'][:150]}..." for c in retrieved[:3]])
        answer_text = f"Based on the uploaded documents:\n{top_chunks_summary}"

    # Map retrieved chunks to citations
    chunk_map = {c["chunk_id"]: c for c in retrieved}
    cited_chunks = []

    # 1. Look for explicit chunk_id matches in the answer text
    for chunk_id, c in chunk_map.items():
        if chunk_id in answer_text:
            cited_chunks.append(c)

    # 2. Look for page numbers in answer text like (Page 12) or Page 12
    if not cited_chunks:
        page_matches = set(map(int, re.findall(r"Page\s+(\d+)", answer_text, re.IGNORECASE)))
        for c in retrieved:
            if c["page_number"] in page_matches:
                cited_chunks.append(c)

    # 3. Fallback: if no citations identified yet, ground to retrieved top chunks
    if not cited_chunks:
        cited_chunks = retrieved

    # Deduplicate citations by (documentId, page_number)
    seen = set()
    citations = []
    for c in cited_chunks:
        key = (c["documentId"], c["page_number"])
        if key not in seen:
            seen.add(key)
            citations.append({"documentId": c["documentId"], "page": c["page_number"]})

    citations.sort(key=lambda c: (c["documentId"], c["page"]))
    return {"answer": answer_text, "citations": citations}