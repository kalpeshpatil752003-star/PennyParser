import os
import re
import asyncio
import logging
import httpx

from app.core.config import SPRING_BASE_URL, INTERNAL_SERVICE_TOKEN
from app.services.extraction import extract_document
from app.services.chunking import chunk_pages
from app.core.faiss_store import add_chunks_batch, remove_document
from app.services.financial_extraction import extract_financial_tables
from app.services.line_items import extract_line_items, compute_period_comparisons
from app.services.ratios import calculate_ratios
from app.services.rag import store_line_items

logger = logging.getLogger("pipeline")


async def run_pipeline(document_id: int, file_path: str, file_type: str):
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Clean previous state for idempotency
            remove_document(document_id)

            await report_status(client, document_id, "EXTRACTING")
            pages = extract_document(file_path, file_type)
            logger.info(f"[doc {document_id}] extracted {len(pages)} pages/sections for fileType={file_type}")

            if not pages:
                raise ValueError("No text content could be extracted from document.")

            await report_status(client, document_id, "CHUNKING")
            chunks = chunk_pages(pages)
            logger.info(f"[doc {document_id}] created {len(chunks)} chunks")

            await report_status(client, document_id, "EMBEDDING")
            # Batch chunk addition (single-pass embedding and persistence)
            added_metas = add_chunks_batch(document_id, chunks)

            chunks_meta = []
            for meta in added_metas:
                chunks_meta.append({
                    "chunkIndex": meta["chunk_index"],
                    "pageNumber": meta["page_number"],
                    "textPreview": meta["text"][:200],
                    "vectorId": meta["vector_id"]
                })

            # Sync chunks to PostgreSQL
            await sync_chunks_to_spring(client, document_id, chunks_meta)

            # Financial Extraction (PDF, DOCX, etc.)
            line_items = {}
            ratios = {}
            period_comparisons = {}
            try:
                ext = os.path.splitext(file_path)[1].lower()
                ft_upper = (file_type or "").upper()
                if ft_upper in ("PDF", "DOCX") or ext in (".pdf", ".docx"):
                    logger.info(f"[doc {document_id}] extracting financial statements for format={file_type}")
                    tables = extract_financial_tables(file_path, file_type)
                    logger.info(f"[doc {document_id}] found {len(tables)} candidate financial tables")

                    if tables:
                        extraction_result = extract_line_items(tables)
                        line_items = extraction_result
                        periods = extraction_result.periods if hasattr(extraction_result, "periods") else list(extraction_result)
                        audit_metadata = getattr(extraction_result, "audit_metadata", {})
                        ratios = calculate_ratios(line_items)
                        period_comparisons = compute_period_comparisons(line_items)

                        for p in periods:
                            logger.info(f"[doc {document_id}] period={p.get('period_key')} ({p.get('period_type')}): label='{p.get('label')}'")

                if line_items:
                    store_line_items(document_id, line_items)

                # Sync financials (with period-keyed structure and audit metadata) to Spring Boot
                await sync_financials_to_spring(
                    client,
                    document_id,
                    line_items=dict(line_items.items()) if hasattr(line_items, "items") else line_items,
                    ratios=ratios,
                    period_comparisons=period_comparisons,
                    periods=[dict(p) for p in periods] if 'periods' in locals() and periods else None,
                    audit_metadata=audit_metadata if 'audit_metadata' in locals() else None,
                )

            except Exception as fe:
                # Decoupled financial extraction failure: do not crash document RAG
                logger.warning(f"[doc {document_id}] Financial statement extraction encountered an issue: {fe}. Document text/RAG remains available.")

            await report_status(client, document_id, "READY")
            logger.info(f"[doc {document_id}] READY — {len(chunks)} vectors and metadata synced.")

        except Exception as e:
            logger.exception(f"[doc {document_id}] pipeline failed: {e}")
            remove_document(document_id)
            await report_status(client, document_id, "FAILED", error=str(e))


async def report_status(client: httpx.AsyncClient, document_id: int, status: str, error: str = None, retries: int = 3):
    url = f"{SPRING_BASE_URL}/internal/v1/documents/{document_id}/status"
    headers = {"X-Internal-Token": INTERNAL_SERVICE_TOKEN}
    payload = {"status": status}
    if error:
        payload["errorMessage"] = error

    for attempt in range(retries):
        try:
            resp = await client.put(url, json=payload, headers=headers)
            resp.raise_for_status()
            return
        except Exception as e:
            if attempt == retries - 1:
                logger.error(f"[doc {document_id}] Failed to report status '{status}' after {retries} attempts: {e}")
            else:
                await asyncio.sleep(0.5 * (attempt + 1))


async def sync_chunks_to_spring(client: httpx.AsyncClient, document_id: int, chunks_meta: list[dict], retries: int = 3):
    url = f"{SPRING_BASE_URL}/internal/v1/documents/{document_id}/chunks"
    headers = {"X-Internal-Token": INTERNAL_SERVICE_TOKEN}

    for attempt in range(retries):
        try:
            resp = await client.post(url, json=chunks_meta, headers=headers)
            resp.raise_for_status()
            return
        except Exception as e:
            if attempt == retries - 1:
                logger.error(f"[doc {document_id}] Failed to sync chunks after {retries} attempts: {e}")
            else:
                await asyncio.sleep(0.5 * (attempt + 1))


async def sync_financials_to_spring(
    client: httpx.AsyncClient,
    document_id: int,
    line_items: dict,
    ratios: dict,
    period_comparisons: dict = None,
    periods: list[dict] = None,
    audit_metadata: dict = None,
    retries: int = 3
):
    url = f"{SPRING_BASE_URL}/internal/v1/documents/{document_id}/financials"
    headers = {"X-Internal-Token": INTERNAL_SERVICE_TOKEN}
    payload = {"lineItems": line_items, "ratios": ratios}
    if period_comparisons:
        payload["periodComparisons"] = period_comparisons
    if periods:
        payload["periods"] = periods
    if audit_metadata:
        payload["auditMetadata"] = audit_metadata

    for attempt in range(retries):
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return
        except Exception as e:
            if attempt == retries - 1:
                logger.error(f"[doc {document_id}] Failed to sync financials after {retries} attempts: {e}")
            else:
                await asyncio.sleep(0.5 * (attempt + 1))