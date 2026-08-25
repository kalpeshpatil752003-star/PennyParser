import fitz  # PyMuPDF

def extract_pages(file_path: str) -> list[dict]:
    """Returns [{ "page_number": int, "text": str }, ...]"""
    doc = fitz.open(file_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            pages.append({"page_number": i + 1, "text": text})
    doc.close()
    return pages