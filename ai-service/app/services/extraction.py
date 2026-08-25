import os

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

def extract_pages(file_path: str) -> list[dict]:
    """Returns [{ "page_number": int, "text": str }, ...] for PDF documents."""
    if fitz is None:
        return extract_txt(file_path)
    doc = fitz.open(file_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            pages.append({"page_number": i + 1, "text": text})
    doc.close()
    return pages

def extract_docx(file_path: str) -> list[dict]:
    """Extracts text from DOCX files, grouping paragraphs into logical pages of ~2000 chars."""
    try:
        import docx
        doc = docx.Document(file_path)
        full_text = []
        for p in doc.paragraphs:
            if p.text.strip():
                full_text.append(p.text.strip())
        combined = "\n\n".join(full_text)
    except ImportError:
        combined = ""
        
    if not combined:
        return extract_txt(file_path)
        
    return _split_into_logical_pages(combined)

def extract_txt(file_path: str) -> list[dict]:
    """Extracts text from TXT files, grouping lines into logical pages of ~2000 chars."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read().strip()
    if not text:
        return []
    return _split_into_logical_pages(text)

def _split_into_logical_pages(text: str, page_size: int = 2000) -> list[dict]:
    pages = []
    start = 0
    page_num = 1
    while start < len(text):
        end = start + page_size
        chunk = text[start:end].strip()
        if chunk:
            pages.append({"page_number": page_num, "text": chunk})
            page_num += 1
        start = end
    return pages

def extract_document(file_path: str, file_type: str) -> list[dict]:
    """
    Unified extraction dispatcher.
    Supports PDF, DOCX, TXT.
    Returns normalized list: [{ "page_number": int, "text": str }, ...]
    """
    file_type_upper = file_type.upper() if file_type else ""
    ext = os.path.splitext(file_path)[1].lower()
    
    if file_type_upper == "PDF" or ext == ".pdf":
        return extract_pages(file_path)
    elif file_type_upper == "DOCX" or ext == ".docx":
        return extract_docx(file_path)
    elif file_type_upper == "TXT" or ext == ".txt":
        return extract_txt(file_path)
    else:
        try:
            return extract_pages(file_path)
        except Exception:
            return extract_txt(file_path)