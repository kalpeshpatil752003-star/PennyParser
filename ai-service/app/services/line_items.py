import re
import logging
from app.services.normalize import parse_number

logger = logging.getLogger("line_items")

LINE_ITEM_PATTERNS = {
    "revenue": ["total net sales", "net sales", "total revenue", "net revenue", "revenue"],
    "cost_of_goods_sold": ["total cost of sales", "cost of products sold", "cost of goods sold", "cost of revenue", "cost of sales"],
    "gross_profit": ["gross margin", "gross profit"],
    "operating_income": ["operating income", "income from operations"],
    "net_income": ["net earnings", "net income"],
    "total_assets": ["total assets"],
    "total_liabilities": ["total liabilities"],
    "total_equity": ["total stockholders equity", "total shareholders equity", "total equity", "stockholders equity", "shareholders equity"],
    "current_assets": ["total current assets"],
    "current_liabilities": ["total current liabilities"],
    "eps": ["diluted", "basic earnings per share"],
}

EXCLUDE_IF_CONTAINS = {
    "total_liabilities": ["and stockholders", "and shareholders", "and equity", "plus stockholders", "plus equity"],
    "revenue": ["cost of revenue"],
    "total_equity": ["and liabilities", "plus liabilities"],
}


def normalize_label(label: str) -> str:
    return re.sub(r"[^\w\s]", "", label.lower()).strip()


def reconstruct_label(cells: list[str]) -> str:
    """
    Reconstructs labels that have been fragmented across cells by table extraction grid splitting.
    Example: ['Total liabiliti', 'es'] -> 'Total liabilities'
    Example: ['Total liabilities a', "nd stockholders' equity"] -> "Total liabilities and stockholders' equity"
    """
    cleaned_cells = [c.strip() for c in cells if c and c.strip()]
    if not cleaned_cells:
        return ""

    label_parts = []
    for cell in cleaned_cells:
        if not label_parts:
            label_parts.append(cell)
            continue

        last = label_parts[-1]
        if re.search(r"[a-zA-Z]{1,12}$", last) and re.match(r"^[a-zA-Z]{1,4}(?:\s|[^\w]|$)", cell):
            label_parts[-1] = last + cell
        else:
            label_parts.append(cell)

    raw_joined = " ".join(label_parts)
    raw_joined = re.sub(r"\s+", " ", raw_joined).strip()
    return normalize_label(raw_joined)


def _is_probably_year(value: float) -> bool:
    return value == int(value) and 1900 <= value <= 2100


# ---------------------------------------------------------------------------
# Period-aware header detection
# ---------------------------------------------------------------------------

def _detect_period_headers(rows: list[list[str]]) -> dict[int, str]:
    """
    Scans header rows for period qualifiers and year numbers.
    Returns a dict mapping column_index -> period_key.

    Period keys:
      - "Q2_2026" for "Three Months Ended June 30, 2026"
      - "YTD_2026" for "Six Months Ended June 30, 2026"
      - "2026" for plain year columns (balance sheets, etc.)

    Strategy:
      1. Scan first 5 rows for period qualifier phrases.
      2. Track which horizontal zones (column spans) each qualifier covers.
      3. Map year columns to the qualifier zone they fall in.
    """
    period_zones: list[dict] = []  # [{"qualifier": "3M"|"6M", "start_col": int, "end_col": int, "row": int}]
    year_columns: list[tuple[int, int]] = []  # [(col_idx, year)]

    header_rows = rows[:5]

    for row_idx, row in enumerate(header_rows):
        if not row:
            continue

        full_row_text = " ".join(c or "" for c in row).lower()

        # Find period qualifier phrases in the full row text
        has_3m = bool(re.search(r"three\s+months?\s+ended", full_row_text))
        has_6m = bool(re.search(r"six\s+months?\s+ended", full_row_text))

        if has_3m or has_6m:
            # Determine column positions for each qualifier
            for col_idx, cell in enumerate(row):
                if not cell:
                    continue
                cell_lower = cell.strip().lower()
                if re.search(r"three\s+months?\s+ended", cell_lower):
                    period_zones.append({"qualifier": "3M", "col": col_idx, "row": row_idx})
                elif re.search(r"six\s+months?\s+ended", cell_lower):
                    period_zones.append({"qualifier": "6M", "col": col_idx, "row": row_idx})

        # Find year numbers
        for col_idx, cell in enumerate(row):
            if not cell:
                continue
            parsed = parse_number(cell.strip())
            if parsed and _is_probably_year(parsed):
                year_columns.append((col_idx, int(parsed)))

    if not year_columns:
        return {}

    # If no period qualifier zones found, return plain year mapping
    if not period_zones:
        return {col: str(year) for col, year in year_columns}

    # Map each year column to the nearest period qualifier to its left (or containing it)
    period_by_col: dict[int, str] = {}

    # Sort year columns by position
    year_columns.sort(key=lambda x: x[0])

    # Sort period zones by column position
    period_zones.sort(key=lambda z: z["col"])

    for col_idx, year in year_columns:
        # Find the closest period zone to the left of or at this column
        best_zone = None
        for zone in period_zones:
            if zone["col"] <= col_idx:
                best_zone = zone

        if best_zone:
            q = best_zone["qualifier"]
            if q == "3M":
                period_by_col[col_idx] = f"Q2_{year}"
            elif q == "6M":
                period_by_col[col_idx] = f"YTD_{year}"
        else:
            period_by_col[col_idx] = str(year)

    return period_by_col


def validate_and_reconcile_balance_sheet(found: dict) -> dict:
    """
    Applies Accounting Equation Validation: Total Assets = Total Liabilities + Total Equity.
    If total_liabilities was incorrectly extracted as (Total Liabilities + Equity),
    recalculates Total Liabilities = Total Assets - Total Equity.
    """
    total_assets_item = found.get("total_assets")
    total_liabilities_item = found.get("total_liabilities")
    total_equity_item = found.get("total_equity")

    if total_assets_item and total_equity_item:
        A = total_assets_item.get("value")
        E = total_equity_item.get("value")

        if A is not None and E is not None:
            expected_L = round(A - E, 2)
            current_L = total_liabilities_item.get("value") if total_liabilities_item else None

            if current_L is None or abs(A - (current_L + E)) > (0.01 * A):
                if expected_L > 0:
                    by_period = {}
                    for p, A_p in total_assets_item.get("by_period", {}).items():
                        E_p = total_equity_item.get("by_period", {}).get(p)
                        if E_p is not None:
                            by_period[p] = round(A_p - E_p, 2)

                    found["total_liabilities"] = {
                        "value": expected_L,
                        "by_period": by_period,
                        "page": total_assets_item.get("page", 1),
                        "statement_type": "BALANCE",
                        "reconciled": True
                    }
    return found


def extract_line_items(tables: list[dict]) -> dict:
    found = {}
    for table in tables:
        rows = table["rows"]
        if not rows:
            continue

        period_by_col = _detect_period_headers(rows)
        logger.debug(f"Page {table['page_number']}: period_by_col = {period_by_col}")

        for row in rows:
            if not row:
                continue
            cells = [c if c is not None else "" for c in row]

            first_num_idx = next(
                (idx for idx, c in enumerate(cells) if parse_number(c) is not None and not _is_probably_year(parse_number(c))), None
            )
            if first_num_idx is None:
                continue

            label_text = reconstruct_label(cells[:first_num_idx])
            if not label_text:
                continue

            numeric_with_cols = []
            for col_idx, cell in enumerate(cells[first_num_idx:], start=first_num_idx):
                num = parse_number(cell)
                if num is not None and not _is_probably_year(num):
                    numeric_with_cols.append((col_idx, num))

            if not numeric_with_cols:
                continue

            for metric_key, patterns in LINE_ITEM_PATTERNS.items():
                if metric_key in found:
                    continue
                if not any(normalize_label(p) in label_text for p in patterns):
                    continue
                if any(bad in label_text for bad in EXCLUDE_IF_CONTAINS.get(metric_key, [])):
                    continue

                candidates = numeric_with_cols
                if metric_key == "eps":
                    candidates = [(col, v) for col, v in candidates if v < 100] or candidates

                by_period = {}
                for col_idx, val in candidates:
                    if col_idx in period_by_col:
                        by_period[period_by_col[col_idx]] = val

                primary_val = candidates[0][1] if candidates else None

                found[metric_key] = {
                    "value": primary_val,
                    "by_period": by_period,
                    "page": table["page_number"],
                    "statement_type": table.get("statement_type", "UNKNOWN")
                }
                logger.debug(f"Extracted {metric_key}: value={primary_val}, by_period={by_period}")

    return validate_and_reconcile_balance_sheet(found)