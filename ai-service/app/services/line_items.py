import re
import logging
from app.services.normalize import parse_number

logger = logging.getLogger("line_items")

# Metrics scoped by statement type
STATEMENT_METRICS = {
    "INCOME": [
        "revenue", "cost_of_goods_sold", "gross_profit",
        "operating_income", "net_income", "eps"
    ],
    "BALANCE": [
        "total_assets", "total_liabilities", "total_equity",
        "current_assets", "current_liabilities"
    ],
    "CASHFLOW": [
        "operating_cash_flow", "investing_cash_flow",
        "financing_cash_flow", "free_cash_flow"
    ],
}

LINE_ITEM_PATTERNS = {
    # Income statement
    "revenue": [
        "total net sales", "net sales", "total revenues", "total revenue",
        "net revenues", "net revenue", "revenues", "revenue"
    ],
    "cost_of_goods_sold": [
        "total cost of sales", "cost of products sold", "cost of goods sold",
        "cost of revenue", "cost of sales"
    ],
    "gross_profit": ["gross profit", "gross margin"],
    "operating_income": [
        "operating income", "income from operations",
        "operating profit", "operating earnings"
    ],
    "net_income": [
        "net income", "net earnings", "net loss", "net income loss"
    ],
    "eps": [
        "diluted earnings per share", "basic earnings per share",
        "earnings per share diluted", "net income per share diluted",
        "net income per share basic", "diluted per share", "basic per share",
        "diluted net income per share", "diluted net loss per share",
        "diluted", "basic"
    ],

    # Balance sheet
    "total_assets": ["total assets", "assets total"],
    "total_liabilities": ["total liabilities", "liabilities total"],
    "total_equity": [
        "total stockholders equity", "total shareholders equity",
        "total equity", "stockholders equity", "shareholders equity",
        "total members equity", "total partners equity"
    ],
    "current_assets": ["total current assets", "current assets"],
    "current_liabilities": ["total current liabilities", "current liabilities"],

    # Cash flow
    "operating_cash_flow": [
        "net cash provided by operating activities",
        "net cash from operating activities",
        "operating activities"
    ],
    "investing_cash_flow": [
        "net cash used in investing activities",
        "net cash provided by investing activities",
        "investing activities"
    ],
    "financing_cash_flow": [
        "net cash used in financing activities",
        "net cash provided by financing activities",
        "financing activities"
    ],
    "free_cash_flow": ["free cash flow"],
}

EXCLUDE_IF_CONTAINS = {
    "revenue": [
        "deferred revenue", "unearned revenue", "cost of revenue",
        "cost of sales", "revenue share", "contract liabilities",
        "deferred income", "allowance", "pass-through"
    ],
    "cost_of_goods_sold": [
        "operating expense", "selling general and administrative", "gross profit"
    ],
    "gross_profit": ["percentage", "percent", "%", "margin %"],
    "operating_income": [
        "before income tax", "provision for income", "tax", "non-operating"
    ],
    "net_income": [
        "before income tax", "attributable to noncontrolling",
        "per share", "comprehensive income", "shares"
    ],
    "eps": [
        "shares", "weighted-average", "shareholders", "common shares",
        "basic and diluted shares", "shares outstanding",
        "weighted average number", "number of shares"
    ],
    "total_assets": [
        "current assets", "noncurrent assets", "other assets",
        "operating lease right-of-use assets"
    ],
    "total_liabilities": [
        "and stockholders", "and shareholders", "and equity",
        "plus stockholders", "plus equity", "current liabilities",
        "noncurrent liabilities"
    ],
    "total_equity": ["and liabilities", "plus liabilities"],
    "current_assets": ["noncurrent", "other current assets"],
    "current_liabilities": ["noncurrent", "other current liabilities"],
}


def normalize_label(label: str) -> str:
    return re.sub(r"[^\w\s]", "", label.lower()).strip()


def reconstruct_label(cells: list[str]) -> str:
    """
    Reconstructs labels that have been fragmented across cells by table extraction grid splitting.
    Example: ['Total liabiliti', 'es'] -> 'total liabilities'
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
    """Checks if a float value in a header row is a calendar year."""
    return value is not None and value == int(value) and 1900 <= value <= 2100


def _match_metric(label_text: str, metric_key: str, statement_type: str) -> bool:
    """
    Evaluates whether label_text matches a target metric_key under statement_type.
    Applies statement-type scoping, exclusion lists, and exact/dominant matching.
    """
    # 1. Statement-type scoping
    st_upper = statement_type.upper() if statement_type else "UNKNOWN"
    if st_upper in STATEMENT_METRICS:
        allowed_metrics = STATEMENT_METRICS[st_upper]
        if metric_key not in allowed_metrics:
            return False

    # 2. Exclusions check
    exclusions = EXCLUDE_IF_CONTAINS.get(metric_key, [])
    for bad in exclusions:
        if bad in label_text:
            return False

    # 3. Exact normalized pattern match
    patterns = LINE_ITEM_PATTERNS.get(metric_key, [])
    normalized_patterns = [normalize_label(p) for p in patterns]

    for p in normalized_patterns:
        if label_text == p:
            return True

    # 4. Strict boundary match (label starts with or equals pattern or is dominant)
    for p in normalized_patterns:
        # Check word boundary pattern
        if re.search(rf"\b{re.escape(p)}\b", label_text):
            # For short words like 'revenue', ensure it's not a modifier in a different metric
            label_words = label_text.split()
            pattern_words = p.split()
            if len(label_words) <= len(pattern_words) + 1:
                return True
            if label_text.startswith(p) or label_text.endswith(p):
                return True

    return False


# ---------------------------------------------------------------------------
# Dynamic Period & Quarter Header Detection
# ---------------------------------------------------------------------------

MONTH_QUARTERS = {
    "march": "Q1",
    "mar": "Q1",
    "03": "Q1",
    "june": "Q2",
    "jun": "Q2",
    "06": "Q2",
    "september": "Q3",
    "sept": "Q3",
    "sep": "Q3",
    "09": "Q3",
    "december": "Q4",
    "dec": "Q4",
    "12": "Q4",
}


def _detect_period_headers(rows: list[list[str]]) -> dict[int, str]:
    """
    Scans header rows for period qualifiers (3M, 6M, 9M, FY), dates, and year numbers.
    Returns a dict mapping column_index -> period_key (e.g. Q1_2026, Q2_2026, YTD_2026, 9M_2026, FY_2025, 2026).
    """
    period_zones: list[dict] = []
    year_columns: list[tuple[int, int]] = []

    header_rows = rows[:5]
    detected_years = set()

    for row_idx, row in enumerate(header_rows):
        if not row:
            continue

        full_row_text = " ".join(c or "" for c in row).lower()

        # Check for qualifiers in cells or full row
        for col_idx, cell in enumerate(row):
            if not cell:
                continue
            cell_lower = cell.strip().lower()

            # Determine qualifier type
            q_type = None
            if re.search(r"three\s+months?\s+ended|3\s+months?\s+ended|quarter\s+ended|first\s+quarter|second\s+quarter|third\s+quarter|fourth\s+quarter", cell_lower):
                q_type = "3M"
            elif re.search(r"six\s+months?\s+ended|6\s+months?\s+ended|two\s+quarters\s+ended", cell_lower):
                q_type = "6M"
            elif re.search(r"nine\s+months?\s+ended|9\s+months?\s+ended|three\s+quarters\s+ended", cell_lower):
                q_type = "9M"
            elif re.search(r"twelve\s+months?\s+ended|12\s+months?\s+ended|years?\s+ended|fiscal\s+year\s+ended|full\s+year", cell_lower):
                q_type = "FY"

            # Check for month in this cell or row context
            detected_quarter = None
            if q_type == "3M":
                if "first quarter" in cell_lower or "1st quarter" in cell_lower:
                    detected_quarter = "Q1"
                elif "second quarter" in cell_lower or "2nd quarter" in cell_lower:
                    detected_quarter = "Q2"
                elif "third quarter" in cell_lower or "3rd quarter" in cell_lower:
                    detected_quarter = "Q3"
                elif "fourth quarter" in cell_lower or "4th quarter" in cell_lower:
                    detected_quarter = "Q4"
                else:
                    # Check for month names
                    for m_name, q in MONTH_QUARTERS.items():
                        if m_name in cell_lower or m_name in full_row_text:
                            detected_quarter = q
                            break
                if not detected_quarter:
                    detected_quarter = "Q2"  # fallback default

            if q_type:
                period_zones.append({
                    "qualifier": q_type,
                    "quarter": detected_quarter,
                    "col": col_idx,
                    "row": row_idx,
                    "raw": cell_lower
                })

            # Check for explicit year in cell
            parsed = parse_number(cell.strip())
            if parsed and _is_probably_year(parsed):
                year_columns.append((col_idx, int(parsed)))
                detected_years.add(int(parsed))
            else:
                # Also check date strings like "June 30, 2026"
                m_year = re.search(r"\b(19\d\d|20\d\d)\b", cell)
                if m_year:
                    year_val = int(m_year.group(1))
                    year_columns.append((col_idx, year_val))
                    detected_years.add(year_val)

    if not year_columns:
        return {}

    # Deduplicate year columns by col_idx (keep first)
    seen_cols = set()
    unique_year_cols = []
    for col_idx, yr in sorted(year_columns, key=lambda x: x[0]):
        if col_idx not in seen_cols:
            seen_cols.add(col_idx)
            unique_year_cols.append((col_idx, yr))

    # If no period qualifier zones found, return plain year mapping
    if not period_zones:
        return {col: str(year) for col, year in unique_year_cols}

    # Map each year column to the closest qualifier zone to its left or covering it
    period_by_col: dict[int, str] = {}
    period_zones.sort(key=lambda z: z["col"])

    for col_idx, year in unique_year_cols:
        best_zone = None
        for zone in period_zones:
            if zone["col"] <= col_idx:
                best_zone = zone

        if best_zone:
            q = best_zone["qualifier"]
            if q == "3M":
                q_prefix = best_zone.get("quarter") or "Q2"
                period_by_col[col_idx] = f"{q_prefix}_{year}"
            elif q == "6M":
                period_by_col[col_idx] = f"YTD_{year}"
            elif q == "9M":
                period_by_col[col_idx] = f"9M_{year}"
            elif q == "FY":
                period_by_col[col_idx] = f"FY_{year}"
            else:
                period_by_col[col_idx] = str(year)
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
        rows = table.get("rows", [])
        if not rows:
            continue

        statement_type = table.get("statement_type", "UNKNOWN")
        period_by_col = _detect_period_headers(rows)
        logger.debug(f"Page {table.get('page_number')}: statement_type={statement_type}, period_by_col={period_by_col}")

        # Scan rows
        for row_idx, row in enumerate(rows):
            if not row:
                continue
            cells = [c if c is not None else "" for c in row]

            # Find first numeric cell
            first_num_idx = None
            for idx, c in enumerate(cells):
                num = parse_number(c)
                if num is not None:
                    # If this cell is in the first 3 rows, has no preceding label, and looks like a year, it's a header
                    preceding_label = reconstruct_label(cells[:idx])
                    if row_idx < 3 and not preceding_label and _is_probably_year(num):
                        continue
                    first_num_idx = idx
                    break

            if first_num_idx is None:
                continue

            label_text = reconstruct_label(cells[:first_num_idx])
            if not label_text:
                continue

            numeric_with_cols = []
            for col_idx, cell in enumerate(cells[first_num_idx:], start=first_num_idx):
                num = parse_number(cell)
                if num is not None:
                    numeric_with_cols.append((col_idx, num))

            if not numeric_with_cols:
                continue

            for metric_key in LINE_ITEM_PATTERNS:
                if metric_key in found:
                    continue

                if not _match_metric(label_text, metric_key, statement_type):
                    continue

                candidates = numeric_with_cols
                if metric_key == "eps":
                    candidates = [(col, v) for col, v in candidates if abs(v) < 100] or candidates

                by_period = {}
                for col_idx, val in candidates:
                    if col_idx in period_by_col:
                        by_period[period_by_col[col_idx]] = val

                primary_val = candidates[0][1] if candidates else None

                found[metric_key] = {
                    "value": primary_val,
                    "by_period": by_period,
                    "page": table.get("page_number", 1),
                    "statement_type": statement_type
                }
                logger.debug(f"Extracted {metric_key}: value={primary_val}, by_period={by_period}")

    return validate_and_reconcile_balance_sheet(found)