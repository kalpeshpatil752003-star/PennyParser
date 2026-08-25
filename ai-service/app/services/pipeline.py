import logging
import json
import os
import httpx

from app.core.config import SPRING_BASE_URL, INTERNAL_SERVICE_TOKEN
from app.services.extraction import extract_document
from app.services.chunking import chunk_pages
from app.core.faiss_store import add_chunk, remove_document
from app.services.financial_extraction import extract_financial_tables
from app.services.line_items import extract_line_items
from app.services.ratios import calculate_ratios

logger = logging.getLogger("pipeline")

FINANCIAL_STORE_PATH = "financial_store.json"

if os.path.exists(FINANCIAL_STORE_PATH):
    with open(FINANCIAL_STORE_PATH, "r") as f:
        _financial_store: dict[str, dict] = json.load(f)
else:
    _financial_store: dict[str, dict] = {}


def _persist_financials():
    with open(FINANCIAL_STORE_PATH, "w") as f:
        json.dump(_financial_store, f)


def remove_financials(document_id: int):
    key = str(document_id)
    if key in _financial_store:
        del _financial_store[key]
        _persist_financials()


async def run_pipeline(document_id: int, file_path: str, file_type: str):
    async with httpx.AsyncClient() as client:
        try:
            # Clean previous state to ensure idempotency
            remove_document(document_id)
            remove_financials(document_id)

            await report_status(client, document_id, "EXTRACTING")
            pages = extract_document(file_path, file_type)
            logger.info(f"[doc {document_id}] extracted {len(pages)} pages/sections for fileType={file_type}")

            await report_status(client, document_id, "CHUNKING")
            chunks = chunk_pages(pages)
            logger.info(f"[doc {document_id}] created {len(chunks)} chunks")

            await report_status(client, document_id, "EMBEDDING")
            for i, chunk in enumerate(chunks):
                add_chunk(document_id, chunk_index=i, page_number=chunk["page_number"], text=chunk["text"])

            if file_type.upper() == "PDF":
                logger.info(f"[doc {document_id}] extracting financial statements")
                tables = extract_financial_tables(file_path)
                logger.info(f"[doc {document_id}] found {len(tables)} candidate financial tables")

                line_items = extract_line_items(tables)
                ratios = calculate_ratios(line_items)
                _financial_store[str(document_id)] = {"lineItems": line_items, "ratios": ratios}
                _persist_financials()
            else:
                _financial_store[str(document_id)] = {"lineItems": {}, "ratios": {}}
                _persist_financials()

            await report_status(client, document_id, "READY")
            logger.info(f"[doc {document_id}] READY — {len(chunks)} vectors stored")

        except Exception as e:
            logger.exception(f"[doc {document_id}] pipeline failed: {e}")
            remove_document(document_id)
            remove_financials(document_id)
            await report_status(client, document_id, "FAILED", error=str(e))


async def report_status(client: httpx.AsyncClient, document_id: int, status: str, error: str = None):
    url = f"{SPRING_BASE_URL}/internal/v1/documents/{document_id}/status"
    headers = {"X-Internal-Token": INTERNAL_SERVICE_TOKEN}
    payload = {"status": status}
    if error:
        payload["errorMessage"] = error
    try:
        await client.put(url, json=payload, headers=headers)
    except Exception as e:
        logger.error(f"[doc {document_id}] Failed to report status '{status}' to Spring Boot: {e}")


def get_financials(document_id: int) -> dict:
    return _financial_store.get(str(document_id), {"lineItems": {}, "ratios": {}})