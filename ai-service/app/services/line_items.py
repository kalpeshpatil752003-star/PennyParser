import re
from app.services.normalize import parse_number

LINE_ITEM_PATTERNS = {
    "revenue": ["total net sales", "net sales", "total revenue", "net revenue", "revenue"],
    "cost_of_goods_sold": ["total cost of sales", "cost of products sold", "cost of goods sold", "cost of revenue", "cost of sales"],
    "gross_profit": ["gross margin", "gross profit"],
    "operating_income": ["operating income", "income from operations"],
    "net_income": ["net earnings", "net income"],
    "total_assets": ["total assets"],
    "total_liabilities": ["total liabilities"],
    "total_equity": ["total shareholders equity", "total stockholders equity", "total equity"],
    "current_assets": ["total current assets"],
    "current_liabilities": ["total current liabilities"],
    "eps": ["diluted", "basic earnings per share"],
}

EXCLUDE_IF_CONTAINS = {
    "total_liabilities": ["and stockholders", "and shareholders"],
    "revenue": ["cost of revenue"],
}

def normalize_label(label: str) -> str:
    return re.sub(r"[^\w\s]", "", label.lower()).strip()

def _is_probably_year(value: float) -> bool:
    return value == int(value) and 1900 <= value <= 2100

def extract_years_from_header(rows: list[list[str]]) -> list[tuple[int, int]]:
    """Returns [(column_index, year), ...] from header rows."""
    years = []
    for row in rows[:3]:  # Check first 3 rows
        if not row:
            continue
        for idx, cell in enumerate(row):
            if not cell:
                continue
            parsed = parse_number(cell)
            if parsed and _is_probably_year(parsed):
                years.append((idx, int(parsed)))
    return years

def extract_line_items(tables: list[dict]) -> dict:
    found = {}
    for table in tables:
        rows = table["rows"]
        if not rows:
            continue

        header_years = extract_years_from_header(rows)
        year_by_col = {col_idx: year for col_idx, year in header_years}

        for row in rows:
            if not row:
                continue
            cells = [c if c is not None else "" for c in row]

            first_num_idx = next(
                (idx for idx, c in enumerate(cells) if parse_number(c) is not None and not _is_probably_year(parse_number(c))), None
            )
            if first_num_idx is None:
                continue

            label_text = normalize_label(" ".join(cells[:first_num_idx]))
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

                by_year = {}
                for col_idx, val in candidates:
                    if col_idx in year_by_col:
                        by_year[year_by_col[col_idx]] = val

                primary_val = candidates[0][1] if candidates else None

                found[metric_key] = {
                    "value": primary_val,
                    "by_year": by_year,
                    "page": table["page_number"],
                    "statement_type": table.get("statement_type", "UNKNOWN")
                }
    return found