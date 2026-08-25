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

# Labels that should NOT count as a match even though the pattern is a substring —
# these are combined/summary rows that would otherwise collide with a simpler metric.
EXCLUDE_IF_CONTAINS = {
    "total_liabilities": ["and stockholders", "and shareholders"],
    "revenue": ["cost of revenue"],
}

def normalize_label(label: str) -> str:
    return re.sub(r"[^\w\s]", "", label.lower()).strip()

def _is_probably_year(value: float) -> bool:
    return value == int(value) and 1900 <= value <= 2100

def extract_line_items(tables: list[dict]) -> dict:
    found = {}
    for table in tables:
        for row in table["rows"]:
            if not row:
                continue
            cells = [c if c is not None else "" for c in row]

            first_num_idx = next(
                (idx for idx, c in enumerate(cells) if parse_number(c) is not None), None
            )
            if first_num_idx is None:
                continue

            label_text = normalize_label(" ".join(cells[:first_num_idx]))
            if not label_text:
                continue

            numeric_cells = [n for n in (parse_number(c) for c in cells[first_num_idx:]) if n is not None]
            if not numeric_cells:
                continue

            for metric_key, patterns in LINE_ITEM_PATTERNS.items():
                if metric_key in found:
                    continue
                if not any(normalize_label(p) in label_text for p in patterns):
                    continue
                if any(bad in label_text for bad in EXCLUDE_IF_CONTAINS.get(metric_key, [])):
                    continue  # this row is a combined/summary row, skip it

                candidates = [v for v in numeric_cells if not _is_probably_year(v)] or numeric_cells

                if metric_key == "eps":
                    # EPS is always a small per-share number — filter out share counts (millions)
                    candidates = [v for v in candidates if v < 100] or candidates

                found[metric_key] = {"value": candidates[0], "page": table["page_number"]}
    return found