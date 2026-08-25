import unittest
import os
import tempfile
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.normalize import parse_number
from app.services.chunking import chunk_pages
from app.services.extraction import extract_document
from app.services.ratios import calculate_ratios
from app.core import faiss_store

class TestAIService(unittest.TestCase):

    def test_parse_number(self):
        self.assertEqual(parse_number("$1,234"), 1234.0)
        self.assertEqual(parse_number("(1,234)"), -1234.0)
        self.assertEqual(parse_number("1,234.50"), 1234.50)
        self.assertEqual(parse_number("12.5%"), 12.5)
        self.assertEqual(parse_number("1,234*"), 1234.0)
        self.assertIsNone(parse_number("-"))
        self.assertIsNone(parse_number("—"))
        self.assertIsNone(parse_number("N/A"))

    def test_chunking_preserves_paragraphs(self):
        text = "Paragraph 1 is about revenue.\n\nParagraph 2 is about operating expenses.\n\nParagraph 3 is about net income."
        pages = [{"page_number": 1, "text": text}]
        chunks = chunk_pages(pages)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertIn("Paragraph 1", chunks[0]["text"])
        self.assertEqual(chunks[0]["page_number"], 1)

    def test_faiss_scoped_search_and_deletion(self):
        faiss_store.remove_document(1)
        faiss_store.remove_document(2)

        faiss_store.add_chunk(document_id=1, chunk_index=0, page_number=1, text="Apple revenue grew 10% in fiscal 2024.")
        faiss_store.add_chunk(document_id=2, chunk_index=0, page_number=1, text="Microsoft cloud revenue reached $30B.")

        global_res = faiss_store.search("revenue", top_k=5)
        self.assertEqual(len(global_res), 2)

        doc1_res = faiss_store.search("revenue", document_ids=[1], top_k=5)
        self.assertEqual(len(doc1_res), 1)
        self.assertEqual(doc1_res[0]["documentId"], 1)

        doc2_res = faiss_store.search("revenue", document_ids=[2], top_k=5)
        self.assertEqual(len(doc2_res), 1)
        self.assertEqual(doc2_res[0]["documentId"], 2)

        faiss_store.remove_document(1)
        deleted_res = faiss_store.search("revenue", document_ids=[1], top_k=5)
        self.assertEqual(len(deleted_res), 0)

        rem_res = faiss_store.search("revenue", document_ids=[2], top_k=5)
        self.assertEqual(len(rem_res), 1)

        faiss_store.remove_document(2)

    def test_txt_extraction(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("This is a financial text file.\nSample content for testing.")
            temp_path = f.name
            
        try:
            pages = extract_document(temp_path, "TXT")
            self.assertEqual(len(pages), 1)
            self.assertEqual(pages[0]["page_number"], 1)
            self.assertIn("financial text file", pages[0]["text"])
        finally:
            os.remove(temp_path)

    def test_calculate_ratios(self):
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
        self.assertEqual(ratios["gross_margin_pct"], 40.0)
        self.assertEqual(ratios["operating_margin_pct"], 20.0)
        self.assertEqual(ratios["net_margin_pct"], 15.0)
        self.assertEqual(ratios["roe_pct"], 15.0)
        self.assertEqual(ratios["roa_pct"], 10.0)
        self.assertEqual(ratios["debt_to_equity"], 0.5)
        self.assertEqual(ratios["current_ratio"], 2.0)

if __name__ == "__main__":
    unittest.main()
