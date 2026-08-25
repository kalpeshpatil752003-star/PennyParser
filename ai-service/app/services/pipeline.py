import logging
import json
import os
import httpx

from app.core.config import SPRING_BASE_URL, INTERNAL_SERVICE_TOKEN
from app.services.extraction import extract_pages
from app.services.chunking import chunk_pages
from app.core.faiss_store import add_chunk
from app.services.financial_extraction import extract_financial_tables
from app.services.line_items import extract_line_items
from app.services.ratios import calculate_ratios

logger = logging.getLogger("pipeline")

# Persistent store for extracted financial data: documentId (str) -> {"lineItems": ..., "ratios": ...}
FINANCIAL_STORE_PATH = "financial_store.json"

if os.path.exists(FINANCIAL_STORE_PATH):
    with open(FINANCIAL_STORE_PATH, "r") as f:
        _financial_store: dict[str, dict] = json.load(f)
else:
    _financial_store: dict[str, dict] = {}


def _persist_financials():
    with open(FINANCIAL_STORE_PATH, "w") as f:
        json.dump(_financial_store, f)


async def run_pipeline(document_id: int, file_path: str, file_type: str):
    async with httpx.AsyncClient() as client:
        try:
            await report_status(client, document_id, "EXTRACTING")
            pages = extract_pages(file_path)
            logger.info(f"[doc {document_id}] extracted {len(pages)} pages")
            if pages:
                logger.info(f"[doc {document_id}] page 1 preview: {pages[0]['text'][:200]}")

            await report_status(client, document_id, "CHUNKING")
            chunks = chunk_pages(pages)
            logger.info(f"[doc {document_id}] created {len(chunks)} chunks")
            if chunks:
                logger.info(f"[doc {document_id}] chunk 0 preview: {chunks[0]['text'][:200]}")

            await report_status(client, document_id, "EMBEDDING")
            for i, chunk in enumerate(chunks):
                vector_id = add_chunk(document_id, chunk["page_number"], chunk["text"])
                if i == 0:
                    logger.info(f"[doc {document_id}] first vector_id assigned: {vector_id}")

            logger.info(f"[doc {document_id}] extracting financial statements")
            tables = extract_financial_tables(file_path)
            logger.info(f"[doc {document_id}] found {len(tables)} candidate financial tables")

            line_items = extract_line_items(tables)
            ratios = calculate_ratios(line_items)
            _financial_store[str(document_id)] = {"lineItems": line_items, "ratios": ratios}
            _persist_financials()
            logger.info(f"[doc {document_id}] line items: {line_items}")
            logger.info(f"[doc {document_id}] ratios: {ratios}")

            await report_status(client, document_id, "READY")
            logger.info(f"[doc {document_id}] READY — {len(chunks)} vectors stored")

        except Exception as e:
            logger.exception(f"[doc {document_id}] pipeline failed")
            await report_status(client, document_id, "FAILED", error=str(e))


async def report_status(client: httpx.AsyncClient, document_id: int, status: str, error: str = None):
    url = f"{SPRING_BASE_URL}/internal/v1/documents/{document_id}/status"
    headers = {"X-Internal-Token": INTERNAL_SERVICE_TOKEN}
    payload = {"status": status}
    if error:
        payload["errorMessage"] = error
    await client.put(url, json=payload, headers=headers)


def get_financials(document_id: int) -> dict:
    return _financial_store.get(str(document_id), {"lineItems": {}, "ratios": {}})