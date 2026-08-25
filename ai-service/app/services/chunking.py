CHUNK_SIZE = 800       # characters
CHUNK_OVERLAP = 150    # characters, so context isn't lost at chunk boundaries

def chunk_pages(pages: list[dict]) -> list[dict]:
    """Returns [{ "text": str, "page_number": int }, ...]"""
    chunks = []
    for page in pages:
        text = page["text"]
        start = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            chunk_text = text[start:end]
            chunks.append({"text": chunk_text, "page_number": page["page_number"]})
            start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks