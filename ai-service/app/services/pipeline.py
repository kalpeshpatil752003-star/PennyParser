import logging
import httpx

from app.core.config import SPRING_BASE_URL, INTERNAL_SERVICE_TOKEN
from app.services.extraction import extract_document
from app.services.chunking import chunk_pages
from app.core.faiss_store import add_chunk, remove_document
from app.services.financial_extraction import extract_financial_tables
from app.services.line_items import extract_line_items
from app.services.ratios import calculate_ratios
from app.services.rag import store_line_items

logger = logging.getLogger("pipeline")


async def run_pipeline(document_id: int, file_path: str, file_type: str):
    async with httpx.AsyncClient() as client:
        try:
            # Clean previous state for idempotency
            remove_document(document_id)

            await report_status(client, document_id, "EXTRACTING")
            pages = extract_document(file_path, file_type)
            logger.info(f"[doc {document_id}] extracted {len(pages)} pages/sections for fileType={file_type}")

            await report_status(client, document_id, "CHUNKING")
            chunks = chunk_pages(pages)
            logger.info(f"[doc {document_id}] created {len(chunks)} chunks")

            await report_status(client, document_id, "EMBEDDING")
            chunks_meta = []
            for i, chunk in enumerate(chunks):
                meta = add_chunk(document_id, chunk_index=i, page_number=chunk["page_number"], text=chunk["text"])
                chunks_meta.append({
                    "chunkIndex": i,
                    "pageNumber": chunk["page_number"],
                    "textPreview": chunk["text"][:200],
                    "vectorId": meta["vector_id"]
                })

            # Sync chunks to PostgreSQL
            await sync_chunks_to_spring(client, document_id, chunks_meta)

            line_items = {}
            ratios = {}
            if file_type.upper() == "PDF":
                logger.info(f"[doc {document_id}] extracting financial statements")
                tables = extract_financial_tables(file_path)
                logger.info(f"[doc {document_id}] found {len(tables)} candidate financial tables")

                line_items = extract_line_items(tables)
                ratios = calculate_ratios(line_items)

                # Log extracted period data for debugging
                for metric_key, item in line_items.items():
                    logger.info(f"[doc {document_id}] {metric_key}: value={item.get('value')}, by_period={item.get('by_period', {})}")

            # Cache structured line items for RAG reasoning engine
            if line_items:
                store_line_items(document_id, line_items)

            # Sync financial line items & ratios to PostgreSQL
            await sync_financials_to_spring(client, document_id, line_items, ratios)

            await report_status(client, document_id, "READY")
            logger.info(f"[doc {document_id}] READY — {len(chunks)} vectors and Postgres metadata stored")

        except Exception as e:
            logger.exception(f"[doc {document_id}] pipeline failed: {e}")
            remove_document(document_id)
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


async def sync_chunks_to_spring(client: httpx.AsyncClient, document_id: int, chunks_meta: list[dict]):
    url = f"{SPRING_BASE_URL}/internal/v1/documents/{document_id}/chunks"
    headers = {"X-Internal-Token": INTERNAL_SERVICE_TOKEN}
    try:
        resp = await client.post(url, json=chunks_meta, headers=headers)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"[doc {document_id}] Failed to sync chunks to Spring Boot PostgreSQL: {e}")


async def sync_financials_to_spring(client: httpx.AsyncClient, document_id: int, line_items: dict, ratios: dict):
    url = f"{SPRING_BASE_URL}/internal/v1/documents/{document_id}/financials"
    headers = {"X-Internal-Token": INTERNAL_SERVICE_TOKEN}
    payload = {"lineItems": line_items, "ratios": ratios}
    try:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"[doc {document_id}] Failed to sync financials to Spring Boot PostgreSQL: {e}")