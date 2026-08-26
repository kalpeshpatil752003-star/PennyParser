import pytest
import os
from app.services.normalize import parse_number
from app.services.chunking import chunk_pages
from app.services.extraction import extract_document
from app.services.ratios import calculate_ratios
from app.services.line_items import extract_line_items
from app.core import faiss_store

def test_parse_number():
    assert parse_number("$1,234") == 1234.0
    assert parse_number("(1,234)") == -1234.0
    assert parse_number("1,234.50") == 1234.50
    assert parse_number("12.5%") == 12.5
    assert parse_number("1,234*") == 1234.0
    assert parse_number("-") is None
    assert parse_number("—") is None
    assert parse_number("N/A") is None

def test_chunking_preserves_paragraphs():
    text = "Paragraph 1 is about revenue.\n\nParagraph 2 is about operating expenses.\n\nParagraph 3 is about net income."
    pages = [{"page_number": 1, "text": text}]
    chunks = chunk_pages(pages)
    assert len(chunks) >= 1
    assert "Paragraph 1" in chunks[0]["text"]
    assert chunks[0]["page_number"] == 1

def test_faiss_scoped_search_and_deletion(tmp_path):
    # Reset FAISS state
    faiss_store.remove_document(1)
    faiss_store.remove_document(2)

    faiss_store.add_chunk(document_id=1, chunk_index=0, page_number=1, text="Apple revenue grew 10% in fiscal 2024.")
    faiss_store.add_chunk(document_id=2, chunk_index=0, page_number=1, text="Microsoft cloud revenue reached $30B.")

    # Global search on scoped docs returns results
    global_res = faiss_store.search("revenue", document_ids=[1, 2], top_k=5)
    assert len(global_res) == 2

    # Scoped search only returns requested documentId
    doc1_res = faiss_store.search("revenue", document_ids=[1], top_k=5)
    assert len(doc1_res) == 1
    assert doc1_res[0]["documentId"] == 1

    doc2_res = faiss_store.search("revenue", document_ids=[2], top_k=5)
    assert len(doc2_res) == 1
    assert doc2_res[0]["documentId"] == 2

    # Deleting document 1 removes its vectors
    faiss_store.remove_document(1)
    deleted_res = faiss_store.search("revenue", document_ids=[1], top_k=5)
    assert len(deleted_res) == 0

    # Document 2 vectors remain intact
    rem_res = faiss_store.search("revenue", document_ids=[2], top_k=5)
    assert len(rem_res) == 1

    # Cleanup
    faiss_store.remove_document(2)

def test_txt_extraction(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("This is a financial text file.\nSample content for testing.", encoding="utf-8")
    
    pages = extract_document(str(txt_file), "TXT")
    assert len(pages) == 1
    assert pages[0]["page_number"] == 1
    assert "financial text file" in pages[0]["text"]

def test_calculate_ratios():
    items = {
        "revenue": {"value": 1000.0},
        "cost_of_goods_sold": {"value": 600.0},
        "gross_profit": {"value": 400.0},
        "operating_income": {"value": 200.0},
        "net_income": {"value": 150.0},
        "total_assets": {"value": 1500.0},
        "total_liabilities": {"value": 500.0},
        "total_equity": {"value": 1000.0},
        "current_assets": {"value": 600.0},
        "current_liabilities": {"value": 300.0},
    }
    ratios = calculate_ratios(items)
    assert ratios["gross_margin_pct"] == 40.0
    assert ratios["operating_margin_pct"] == 20.0
    assert ratios["net_margin_pct"] == 15.0
    assert ratios["roe_pct"] == 15.0
    assert ratios["roa_pct"] == 10.0
    assert ratios["debt_to_equity"] == 0.5
    assert ratios["current_ratio"] == 2.0
