import httpx
from app.core.faiss_store import search

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3:8b"

def build_prompt(question: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        f"[Page {c['page_number']}]: {c['text']}" for c in chunks
    )
    return f"""You are a financial research assistant. Answer the question using ONLY the context below.

STRICT FORMATTING RULES:
- Break your answer into short paragraphs, one idea per paragraph.
- After EVERY paragraph, add the page number(s) it came from, in this exact format: (Page X)
- If a paragraph draws on multiple pages, list them together like: (Page 38, Page 43)
- Use every page from the context that is actually relevant — do not just cite one page for the whole answer.
- If the answer isn't in the context, say you don't have enough information, and cite nothing.

EXAMPLE FORMAT:
Revenue grew 8% year-over-year, driven by strong performance in the retail segment.
(Page 12)

The reconciliation of non-GAAP measures shows adjusted operating income of $4.2 billion, up from $3.9 billion last year.
(Page 43, Page 48)

Context:
{context}

Question: {question}

Answer:"""

async def generate_answer(question: str, document_ids: list[int]) -> dict:
    retrieved = search(question, top_k=5)
    retrieved = [c for c in retrieved if c["documentId"] in document_ids] if document_ids else retrieved

    if not retrieved:
        return {"answer": "I don't have enough information in the uploaded documents to answer that.", "citations": []}

    prompt = build_prompt(question, retrieved)

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(OLLAMA_URL, json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        })
        response.raise_for_status()
        answer_text = response.json()["response"].strip()

    # Dedupe citations by (documentId, page), then sort by page
    seen = set()
    citations = []
    for c in retrieved:
        key = (c["documentId"], c["page_number"])
        if key not in seen:
            seen.add(key)
            citations.append({"documentId": c["documentId"], "page": c["page_number"]})
    citations.sort(key=lambda c: c["page"])

    return {"answer": answer_text, "citations": citations}