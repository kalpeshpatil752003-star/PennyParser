import pdfplumber

INCOME_KEYWORDS = ["net sales", "total revenue", "cost of products sold", "gross profit",
                   "operating income", "net earnings", "net income", "earnings per share"]
BALANCE_KEYWORDS = ["total assets", "total liabilities", "stockholders equity", "shareholders equity",
                    "current assets", "current liabilities", "total equity"]
CASHFLOW_KEYWORDS = ["cash flow from operating", "investing activities", "financing activities",
                     "net increase in cash", "net decrease in cash", "operating activities"]

def classify_page(text: str) -> str | None:
    text_lower = text.lower()
    scores = {
        "INCOME": sum(1 for k in INCOME_KEYWORDS if k in text_lower),
        "BALANCE": sum(1 for k in BALANCE_KEYWORDS if k in text_lower),
        "CASHFLOW": sum(1 for k in CASHFLOW_KEYWORDS if k in text_lower),
    }
    best_type, best_score = max(scores.items(), key=lambda kv: kv[1])
    return best_type if best_score >= 3 else None  # require strong signal, avoid false positives

def extract_financial_tables(file_path: str) -> list[dict]:
    results = []
    table_settings = {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "snap_tolerance": 5,
    }
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            statement_type = classify_page(text)
            if not statement_type:
                continue

            tables = page.extract_tables(table_settings)
            if not tables:
                tables = page.extract_tables()

            for table in tables:
                if len(table) < 5:
                    continue
                results.append({"page_number": i + 1, "statement_type": statement_type, "rows": table})
    return results