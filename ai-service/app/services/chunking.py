CHUNK_TARGET_SIZE = 1000
CHUNK_OVERLAP = 150

def chunk_pages(pages: list[dict]) -> list[dict]:
    """
    Structure-aware chunker for financial reports.
    Preserves paragraphs and financial tables where possible without breaking rows.
    Returns [{ "text": str, "page_number": int }, ...]
    """
    chunks = []
    for page in pages:
        text = page["text"]
        page_num = page["page_number"]
        
        # Split by paragraphs or double newlines
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [text.strip()]
            
        current_chunk = ""
        
        for para in paragraphs:
            # If current_chunk + para fits comfortably, append
            if len(current_chunk) + len(para) + 2 <= CHUNK_TARGET_SIZE:
                current_chunk = (current_chunk + "\n\n" + para).strip()
            else:
                if current_chunk:
                    chunks.append({"text": current_chunk, "page_number": page_num})
                
                # If paragraph itself is huge (> CHUNK_TARGET_SIZE), keep up to 2500 chars intact if it looks like a table
                if len(para) > CHUNK_TARGET_SIZE:
                    if len(para) <= 2500:
                        chunks.append({"text": para, "page_number": page_num})
                        current_chunk = ""
                    else:
                        # Fallback sliding window for exceptionally long blocks
                        start = 0
                        while start < len(para):
                            end = start + CHUNK_TARGET_SIZE
                            chunks.append({"text": para[start:end], "page_number": page_num})
                            start += CHUNK_TARGET_SIZE - CHUNK_OVERLAP
                        current_chunk = ""
                else:
                    # Start new chunk with overlap from end of current_chunk if available
                    overlap = current_chunk[-CHUNK_OVERLAP:] if current_chunk else ""
                    current_chunk = (overlap + "\n\n" + para).strip()
                    
        if current_chunk:
            chunks.append({"text": current_chunk, "page_number": page_num})
            
    return chunks