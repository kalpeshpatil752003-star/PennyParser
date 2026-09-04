import os
import re
import logging
import pdfplumber
from app.services.normalize import parse_number

logger = logging.getLogger("financial_extraction")

INCOME_KEYWORDS = [
    "net sales", "total revenue", "cost of products sold", "gross profit",
    "operating income", "net earnings", "net income", "earnings per share",
    "total revenues", "cost of sales", "income from operations"
]
BALANCE_KEYWORDS = [
    "total assets", "total liabilities", "stockholders equity", "shareholders equity",
    "current assets", "current liabilities", "total equity", "retained earnings",
    "cash and cash equivalents"
]
CASHFLOW_KEYWORDS = [
    "cash flow from operating", "investing activities", "financing activities",
    "net increase in cash", "net decrease in cash", "operating activities",
    "cash and cash equivalents at end of period"
]


def classify_page(text: str) -> str | None:
    text_lower = text.lower()
    scores = {
        "INCOME": sum(1 for k in INCOME_KEYWORDS if k in text_lower),
        "BALANCE": sum(1 for k in BALANCE_KEYWORDS if k in text_lower),
        "CASHFLOW": sum(1 for k in CASHFLOW_KEYWORDS if k in text_lower),
    }
    best_type, best_score = max(scores.items(), key=lambda kv: kv[1])
    return best_type if best_score >= 3 else None


def detect_scale(text: str) -> dict:
    """
    Detects scale/unit multipliers in statement headers ($ in millions, in thousands, in billions).
    """
    text_lower = text.lower()
    if re.search(r"\b(in\s+millions|in\s+million|\$\s*in\s*millions|\(\s*in\s*millions\s*\))\b", text_lower):
        return {"scale": "millions", "multiplier": 1_000_000.0, "display": "$ in millions"}
    elif re.search(r"\b(in\s+thousands|in\s+thousand|\$\s*in\s*thousands|\(\s*in\s*thousands\s*\))\b", text_lower):
        return {"scale": "thousands", "multiplier": 1_000.0, "display": "$ in thousands"}
    elif re.search(r"\b(in\s+billions|in\s+billion|\$\s*in\s*billions|\(\s*in\s*billions\s*\))\b", text_lower):
        return {"scale": "billions", "multiplier": 1_000_000_000.0, "display": "$ in billions"}
    return {"scale": "units", "multiplier": 1.0, "display": "exact"}


def score_table(rows: list[list[str]]) -> float:
    """
    Scores table quality: numeric density, row count, and column count consistency.
    """
    if not rows or len(rows) < 4:
        return 0.0

    total_cells = 0
    numeric_cells = 0
    col_counts = []

    for row in rows:
        if not row:
            continue
        col_counts.append(len(row))
        for cell in row:
            if cell is not None and str(cell).strip():
                total_cells += 1
                if parse_number(str(cell)) is not None:
                    numeric_cells += 1

    if total_cells == 0:
        return 0.0

    num_ratio = numeric_cells / total_cells
    avg_cols = sum(col_counts) / len(col_counts)
    col_variance = sum((c - avg_cols) ** 2 for c in col_counts) / len(col_counts)
    col_penalty = min(col_variance * 0.05, 0.4)

    return max(0.0, num_ratio - col_penalty + (0.1 if len(rows) >= 6 else 0.0))


def extract_pdf_financial_tables(file_path: str) -> list[dict]:
    results = []
    text_settings = {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "snap_tolerance": 5,
    }
    lines_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 5,
    }

    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            statement_type = classify_page(text)
            if not statement_type:
                continue

            scale_info = detect_scale(text)

            # Strategy 1: Text-based strategy
            tables_text = page.extract_tables(text_settings) or []
            # Strategy 2: Lines-based strategy
            tables_lines = page.extract_tables(lines_settings) or []
            # Strategy 3: Default strategy fallback
            tables_default = page.extract_tables() or []

            candidate_sets = [tables_text, tables_lines, tables_default]
            best_tables = []
            best_score = -1.0

            for cand_tables in candidate_sets:
                if not cand_tables:
                    continue
                score = sum(score_table(t) for t in cand_tables) / len(cand_tables)
                if score > best_score:
                    best_score = score
                    best_tables = cand_tables

            for table in best_tables:
                if len(table) < 4:
                    continue
                results.append({
                    "page_number": i + 1,
                    "statement_type": statement_type,
                    "rows": table,
                    "scale": scale_info,
                    "table_quality_score": max(best_score, 0.0),
                })
    return results


def extract_docx_financial_tables(file_path: str) -> list[dict]:
    try:
        import docx
        doc = docx.Document(file_path)
        results = []
        for i, table in enumerate(doc.tables):
            rows = []
            all_text_parts = []
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells]
                rows.append(row_cells)
                all_text_parts.extend(row_cells)

            table_text = " ".join(all_text_parts)
            statement_type = classify_page(table_text)
            if statement_type and len(rows) >= 4:
                scale_info = detect_scale(table_text)
                results.append({
                    "page_number": None,
                    "table_index": i + 1,
                    "statement_type": statement_type,
                    "rows": rows,
                    "scale": scale_info,
                })
        return results
    except Exception as e:
        logger.warning(f"Failed to extract DOCX financial tables: {e}")
        return []


def extract_financial_tables(file_path: str, file_type: str = "PDF") -> list[dict]:
    ext = os.path.splitext(file_path)[1].lower()
    if (file_type and file_type.upper() == "DOCX") or ext == ".docx":
        return extract_docx_financial_tables(file_path)
    elif (file_type and file_type.upper() == "PDF") or ext == ".pdf":
        return extract_pdf_financial_tables(file_path)
    return []