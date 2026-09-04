import re
import logging
from app.services.normalize import parse_number

logger = logging.getLogger("line_items")

# Metrics scoped by statement type
STATEMENT_METRICS = {
    "INCOME": [
        "revenue", "cost_of_goods_sold", "gross_profit",
        "operating_income", "net_income", "eps_basic", "eps_diluted"
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
    "eps_basic": [
        "basic earnings per share", "basic net income per share",
        "net income per share basic", "basic earnings per common share",
        "basic per share", "basic net loss per share",
        "earnings per share basic"
    ],
    "eps_diluted": [
        "diluted earnings per share", "diluted net income per share",
        "net income per share diluted", "diluted earnings per common share",
        "diluted per share", "diluted net loss per share",
        "earnings per share diluted"
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
    "eps_basic": [
        "shares", "weighted-average", "shareholders", "common shares",
        "basic and diluted shares", "shares outstanding",
        "weighted average number", "number of shares",
        "diluted"  # cross-exclusion: basic EPS must not match diluted rows
    ],
    "eps_diluted": [
        "shares", "weighted-average", "shareholders", "common shares",
        "basic and diluted shares", "shares outstanding",
        "weighted average number", "number of shares",
        "basic"  # cross-exclusion: diluted EPS must not match basic rows
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


def _is_combined_liabilities_and_equity_row(label_text: str) -> bool:
    """
    Order-agnostic check: catches rows like 'Total liabilities and stockholders' equity'
    regardless of word order. These are combined totals, not individual line items.
    """
    return "liabilit" in label_text and "equity" in label_text and "total" in label_text


def detect_duplicate_value_anomalies(found: dict) -> list[str]:
    """
    Flags when two different line items extract the exact same numeric value.
    In real financial statements, distinct metrics are virtually never bit-identical.
    """
    warnings = []
    seen_values: dict[float, str] = {}
    for metric_key, item in found.items():
        v = item.get("value")
        if v is None or v == 0:
            continue
        if v in seen_values and seen_values[v] != metric_key:
            warnings.append(
                f"SUSPECT: {metric_key} and {seen_values[v]} extracted identical values ({v}). "
                "Distinct financial line items are virtually never numerically identical — likely a row-matching error."
            )
        else:
            seen_values[v] = metric_key
    return warnings


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

    # 2. Order-agnostic veto for combined liabilities+equity rows
    if metric_key in ("total_equity", "total_liabilities"):
        if _is_combined_liabilities_and_equity_row(label_text):
            return False

    # 3. Exclusions check
    exclusions = EXCLUDE_IF_CONTAINS.get(metric_key, [])
    for bad in exclusions:
        if bad in label_text:
            return False

    # 4. Exact normalized pattern match
    patterns = LINE_ITEM_PATTERNS.get(metric_key, [])
    normalized_patterns = [normalize_label(p) for p in patterns]

    for p in normalized_patterns:
        if label_text == p:
            return True

    # 5. Strict boundary match (label starts with or equals pattern or is dominant)
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


def _detect_period_metadata(rows: list[list[str]], statement_type: str = "UNKNOWN") -> dict[int, dict]:
    """
    Builds rich period metadata per detected period column.
    Returns: col_idx -> {
        "period_key": str,
        "period_type": "duration" | "point_in_time",
        "fiscal_year": int | None,
        "quarter": str | None,
        "label": str,
        "start_date": str | None,
        "end_date": str | None,
        "as_of_date": str | None,
    }
    """
    col_period_keys = _detect_period_headers(rows)
    metadata_by_col = {}

    header_text = " ".join(" ".join(c or "" for c in r) for r in rows[:5]).lower()
    is_balance_sheet = statement_type.upper() == "BALANCE"

    month_days = {
        "march": "03-31", "mar": "03-31", "03": "03-31",
        "june": "06-30", "jun": "06-30", "06": "06-30",
        "september": "09-30", "sept": "09-30", "sep": "09-30", "09": "09-30",
        "december": "12-31", "dec": "12-31", "12": "12-31",
    }

    for col_idx, p_key in col_period_keys.items():
        m_year = re.search(r"(19|20)\d{2}", p_key)
        year = int(m_year.group(0)) if m_year else None

        detected_month_day = None
        for m_name, md in month_days.items():
            if m_name in header_text:
                detected_month_day = md
                break

        if is_balance_sheet:
            period_type = "point_in_time"
            quarter = None
            date_part = detected_month_day or "12-31"
            as_of_date = f"{year}-{date_part}" if year else None
            label = f"As of {p_key.replace('_', ' ')}" if not p_key.startswith("AsOf") else p_key.replace("AsOf_", "As of ")
            if detected_month_day and year:
                for k, v in month_days.items():
                    if v == detected_month_day and len(k) > 2:
                        label = f"As of {k.capitalize()} {detected_month_day.split('-')[1]}, {year}"
                        break
            meta = {
                "period_key": p_key,
                "period_type": period_type,
                "fiscal_year": year,
                "quarter": None,
                "label": label,
                "start_date": None,
                "end_date": None,
                "as_of_date": as_of_date,
            }
        else:
            period_type = "duration"
            quarter = None
            if p_key.startswith("Q"):
                quarter = p_key.split("_")[0]
                label = f"{quarter} {year}" if year else p_key
                end_date = f"{year}-{detected_month_day}" if year and detected_month_day else None
            elif p_key.startswith("YTD") or p_key.startswith("6M"):
                label = f"Six Months Ended {year}" if year else p_key
                end_date = f"{year}-{detected_month_day}" if year and detected_month_day else None
            elif p_key.startswith("9M"):
                label = f"Nine Months Ended {year}" if year else p_key
                end_date = f"{year}-{detected_month_day}" if year and detected_month_day else None
            else:
                label = f"FY {year}" if year else p_key
                end_date = f"{year}-12-31" if year else None

            meta = {
                "period_key": p_key,
                "period_type": period_type,
                "fiscal_year": year,
                "quarter": quarter,
                "label": label,
                "start_date": None,
                "end_date": end_date,
                "as_of_date": None,
            }

        metadata_by_col[col_idx] = meta

    return metadata_by_col


def _recompute(original_item: dict, new_value: float, source_a: dict, source_b: dict) -> dict:
    """
    Builds a recomputed line-item dict, preserving by_period from the two source legs.
    """
    by_period = {}
    a_periods = source_a.get("by_period", {})
    b_periods = source_b.get("by_period", {})
    a_val = source_a.get("value", 0)
    b_val = source_b.get("value", 0)
    is_sum = abs(new_value - (a_val + b_val)) < 0.01 * max(abs(new_value), 1)

    for p in set(list(a_periods.keys()) + list(b_periods.keys())):
        a_p = a_periods.get(p)
        b_p = b_periods.get(p)
        if a_p is not None and b_p is not None:
            by_period[p] = round((a_p + b_p) if is_sum else (a_p - b_p), 2)

    return {
        "value": round(new_value, 2),
        "by_period": by_period,
        "page": original_item.get("page") or source_a.get("page", 1),
        "statement_type": "BALANCE",
        "reconciled": True,
        "confidence": original_item.get("confidence", 0.0),
    }


def reconcile_balance_sheet_identity(found: dict) -> dict:
    """
    Symmetric A = L + E reconciliation.
    When the identity is broken, recomputes the leg with the lowest extraction
    confidence score from the other two — instead of always assuming liabilities is wrong.
    """
    A = found.get("total_assets")
    L = found.get("total_liabilities")
    E = found.get("total_equity")

    if not (A and L and E):
        return found  # can't check identity with <3 legs

    a, l, e = A.get("value"), L.get("value"), E.get("value")
    if None in (a, l, e):
        return found

    # Identity holds within 1% tolerance — nothing to fix
    if a != 0 and abs(a - (l + e)) <= 0.01 * abs(a):
        return found

    # Identity broken — trust the leg with lowest confidence the least
    legs = {"total_assets": (A, a), "total_liabilities": (L, l), "total_equity": (E, e)}
    confidences = {k: v[0].get("confidence", 1.0) for k, v in legs.items()}
    weakest = min(confidences, key=confidences.get)

    logger.warning(
        f"Balance sheet identity broken: A={a}, L={l}, E={e} (A-(L+E)={a-(l+e)}). "
        f"Confidence scores: {confidences}. Recomputing weakest leg: {weakest}"
    )

    if weakest == "total_equity":
        found["total_equity"] = _recompute(E, a - l, A, L)
    elif weakest == "total_liabilities":
        found["total_liabilities"] = _recompute(L, a - e, A, E)
    else:
        found["total_assets"] = _recompute(A, l + e, L, E)

    return found


def _select_best_candidates(candidates_by_metric: dict[str, list[dict]]) -> dict:
    """
    Scores all candidates per metric and selects the best one.
    Scoring factors: number of period columns matched, table quality, row depth.
    Retains a normalized confidence score for downstream reconciliation.
    Logs warnings and populates conflicting_candidate when top-2 values disagree.
    """
    found = {}
    for metric_key, candidates in candidates_by_metric.items():
        if not candidates:
            continue

        def score(c):
            return (
                c["n_periods_matched"] * 2.0      # more period columns matched = more likely a real total row
                + c["table_quality"]               # trust higher-quality tables more
                - (0.1 * c["row_idx"] if c["row_idx"] > 30 else 0)  # rows deep into a huge table are less likely primary
            )

        ranked = sorted(candidates, key=score, reverse=True)
        best = ranked[0]
        best_score = score(best)

        # Flag disagreement between top-2 distinct values for the validator to warn on
        if len(ranked) > 1 and ranked[1]["value"] is not None and best["value"] is not None:
            if best["value"] != 0 and abs(ranked[1]["value"] - best["value"]) / abs(best["value"]) > 0.02:
                best["conflicting_candidate"] = {
                    "value": ranked[1]["value"],
                    "page": ranked[1]["page"],
                }
                logger.warning(
                    f"{metric_key}: chosen value {best['value']} (page {best['page']}) disagrees with "
                    f"alternate candidate {ranked[1]['value']} (page {ranked[1]['page']})"
                )

        # Retain normalized confidence for downstream reconciliation (0.0 – 1.0)
        # Max theoretical score ≈ 8.0 (4 periods × 2.0 + 1.0 quality)
        best["confidence"] = min(best_score / 8.0, 1.0) if best_score > 0 else 0.1

        best.pop("row_idx", None)
        best.pop("table_quality", None)
        best.pop("n_periods_matched", None)
        found[metric_key] = best
    return found


class PeriodList(list):
    """
    A list of period objects, each with explicit metadata (period_type: "duration" | "point_in_time",
    start_date/end_date or as_of_date, fiscal_year, label) and every applicable metric as a flat field.
    Provides backward-compatible dict/metric access so downstream consumers and existing tests
    continue to work seamlessly.
    """
    def __init__(self, periods=None, audit_metadata=None):
        super().__init__(periods or [])
        self.audit_metadata = audit_metadata or {
            "source_scale": "units",
            "source_scale_display": "exact",
            "multiplier": 1.0,
        }

    @property
    def periods(self):
        return list(self)

    def to_dict(self) -> dict:
        return {
            "periods": [dict(p) for p in self],
            "audit_metadata": dict(self.audit_metadata),
        }

    def __getitem__(self, key):
        if isinstance(key, (int, slice)):
            return super().__getitem__(key)
        if key == "periods":
            return list(self)
        if key == "audit_metadata":
            return self.audit_metadata

        # Look up metric across periods for backward-compatible metric dict access
        for p in self:
            if isinstance(p, dict) and key in p and isinstance(p[key], dict) and "value" in p[key]:
                by_period = {
                    period["period_key"]: period[key]["value"]
                    for period in self
                    if isinstance(period, dict) and key in period and isinstance(period[key], dict) and "value" in period[key]
                }
                primary_val = p[key]["value"]
                return {
                    "value": primary_val,
                    "by_period": by_period,
                    "page": p[key].get("source_page"),
                    "table_index": p[key].get("source_table"),
                    "source": p[key].get("source", "extracted"),
                    "confidence": p[key].get("confidence", 1.0),
                    "scale_applied": self.audit_metadata.get("source_scale", "units"),
                    "conflicting_candidate": p[key].get("conflicting_candidate"),
                    "reconciled": p[key].get("reconciled", False),
                }
        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except (KeyError, IndexError, TypeError):
            return default

    def __contains__(self, key):
        if isinstance(key, str):
            if key in ("periods", "audit_metadata"):
                return True
            return any(isinstance(p, dict) and key in p for p in self)
        return super().__contains__(key)

    def items(self):
        metric_keys = set()
        for p in self:
            if isinstance(p, dict):
                for k in p:
                    if k not in ("period_key", "period_type", "fiscal_year", "quarter", "label", "start_date", "end_date", "as_of_date"):
                        metric_keys.add(k)
        for k in sorted(metric_keys):
            yield k, self[k]

    def keys(self):
        return [k for k, _ in self.items()]

    def values(self):
        return [v for _, v in self.items()]

    def __setitem__(self, key, value):
        if isinstance(key, int):
            super().__setitem__(key, value)
        elif key == "audit_metadata":
            self.audit_metadata = value
        else:
            if not self:
                self.append({"period_key": "FY_DEFAULT", "period_type": "duration", "fiscal_year": 2026, "label": "FY 2026"})
            if isinstance(value, dict) and "value" in value:
                self[0][key] = value
            else:
                self[0][key] = {"value": value, "source": "extracted", "confidence": 1.0}


def extract_line_items(tables: list[dict], locale: str = "en_US") -> PeriodList:
    candidates_by_metric: dict[str, list[dict]] = {}
    all_detected_metadata: dict[str, dict] = {}
    primary_scale_info = {"multiplier": 1.0, "scale": "units", "display": "exact"}

    for table in tables:
        rows = table.get("rows", [])
        if not rows:
            continue

        statement_type = table.get("statement_type", "UNKNOWN")
        table_quality = table.get("table_quality_score", 1.0)
        scale_info = table.get("scale", {"multiplier": 1.0, "scale": "units"})
        if scale_info.get("scale", "units") != "units" or primary_scale_info.get("scale") == "units":
            primary_scale_info = scale_info
        multiplier = scale_info.get("multiplier", 1.0)

        metadata_by_col = _detect_period_metadata(rows, statement_type)
        period_by_col = {c: m["period_key"] for c, m in metadata_by_col.items()}
        for m in metadata_by_col.values():
            all_detected_metadata[m["period_key"]] = m

        page_ref = table.get("page_number") or table.get("table_index", "?")
        logger.debug(f"Page {page_ref}: statement_type={statement_type}, period_by_col={period_by_col}, scale={scale_info.get('scale')}")

        # Scan rows
        for row_idx, row in enumerate(rows):
            if not row:
                continue
            cells = [c if c is not None else "" for c in row]

            # Find first numeric cell
            first_num_idx = None
            for idx, c in enumerate(cells):
                num = parse_number(c, locale=locale)
                if num is not None:
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

            numeric_with_cols = [
                (col_idx, parse_number(cell, locale=locale))
                for col_idx, cell in enumerate(cells[first_num_idx:], start=first_num_idx)
            ]
            numeric_with_cols = [(c, v) for c, v in numeric_with_cols if v is not None]

            if not numeric_with_cols:
                continue

            for metric_key in LINE_ITEM_PATTERNS:
                if not _match_metric(label_text, metric_key, statement_type):
                    continue

                # Standardize canonical internal unit to absolute real dollar value:
                # scale multiplier is applied fully before storing (EPS is per-share, never scaled)
                candidates = numeric_with_cols
                if metric_key.startswith("eps"):
                    candidates = [(col, v) for col, v in candidates if abs(v) < 100] or candidates
                else:
                    candidates = [(col, v * multiplier) for col, v in candidates]

                by_period = {}
                for col_idx, val in candidates:
                    if col_idx in period_by_col:
                        by_period[period_by_col[col_idx]] = val

                entry = {
                    "value": candidates[0][1] if candidates else None,
                    "by_period": by_period,
                    "page": table.get("page_number"),
                    "table_index": table.get("table_index"),
                    "statement_type": statement_type,
                    "scale_applied": scale_info.get("scale", "units"),
                    "row_idx": row_idx,
                    "n_periods_matched": len(by_period),
                    "table_quality": table_quality,
                    "source": "extracted",
                }
                candidates_by_metric.setdefault(metric_key, []).append(entry)
                logger.debug(f"Candidate {metric_key}: value={entry['value']}, by_period={by_period}, page={page_ref}")

    found = _select_best_candidates(candidates_by_metric)
    found = reconcile_balance_sheet_identity(found)

    # Build period-keyed structure
    all_period_keys = set()
    for item in found.values():
        all_period_keys.update(item.get("by_period", {}).keys())

    if not all_period_keys:
        all_period_keys = {"CURRENT"}

    def period_sort_rank(p_key: str):
        m_yr = re.search(r"(19|20)\d{2}", p_key)
        yr = int(m_yr.group(0)) if m_yr else 0
        q = re.search(r"Q([1-4])", p_key)
        q_num = int(q.group(1)) if q else (3 if "YTD" in p_key or "6M" in p_key else (4 if "9M" in p_key else 5))
        return (yr, q_num)

    sorted_p_keys = sorted(all_period_keys, key=period_sort_rank, reverse=True)

    periods = []
    for p_key in sorted_p_keys:
        meta = all_detected_metadata.get(p_key) or {}
        m_yr = re.search(r"(19|20)\d{2}", p_key)
        yr = meta.get("fiscal_year") or (int(m_yr.group(0)) if m_yr else None)
        p_type = meta.get("period_type")
        if not p_type:
            p_type = "point_in_time" if p_key.startswith("AsOf") else "duration"

        p_obj = {
            "period_key": p_key,
            "period_type": p_type,
            "fiscal_year": yr,
            "quarter": meta.get("quarter") or (re.search(r"Q[1-4]", p_key).group(0) if re.search(r"Q[1-4]", p_key) else None),
            "label": meta.get("label") or p_key.replace("_", " "),
            "start_date": meta.get("start_date"),
            "end_date": meta.get("end_date"),
            "as_of_date": meta.get("as_of_date"),
        }

        for metric_key, item in found.items():
            val = None
            if p_key in item.get("by_period", {}):
                val = item["by_period"][p_key]
            elif len(all_period_keys) == 1 and item.get("value") is not None:
                val = item["value"]

            if val is not None:
                p_obj[metric_key] = {
                    "value": val,
                    "source": "derived" if item.get("reconciled") else "extracted",
                    "source_page": item.get("page"),
                    "source_table": item.get("table_index"),
                    "confidence": round(item.get("confidence", 0.9), 3),
                }
                if item.get("conflicting_candidate"):
                    p_obj[metric_key]["conflicting_candidate"] = item["conflicting_candidate"]

        periods.append(p_obj)

    audit_meta = {
        "source_scale": primary_scale_info.get("scale", "units"),
        "source_scale_display": primary_scale_info.get("display", primary_scale_info.get("scale", "exact")),
        "multiplier": primary_scale_info.get("multiplier", 1.0),
    }

    return PeriodList(periods, audit_metadata=audit_meta)


def compute_period_comparisons(line_items: dict) -> dict:
    """
    For each metric with 2+ periods, chronologically rank them and pair the
    most-recent with the next-most-recent as current/prior — works for any
    document's actual period keys, no hardcoded format assumed.
    """
    def sort_key(period_key: str):
        # Extract year + optional quarter for chronological ordering
        m = re.search(r"(19|20)\d{2}", period_key)
        year = int(m.group(0)) if m else 0
        q = re.search(r"Q([1-4])", period_key)
        quarter = int(q.group(1)) if q else 4  # bare years / FY sort last in that year
        return (year, quarter)

    comparisons = {}
    for metric_key, item in line_items.items():
        by_period = item.get("by_period", {})
        if len(by_period) < 2:
            continue
        ranked = sorted(by_period.items(), key=lambda kv: sort_key(kv[0]), reverse=True)
        (curr_key, curr_val), (prior_key, prior_val) = ranked[0], ranked[1]
        if prior_val == 0:
            continue
        comparisons[metric_key] = {
            "current_period": curr_key, "current_value": curr_val,
            "prior_period": prior_key, "prior_value": prior_val,
            "pct_change": round((curr_val - prior_val) / abs(prior_val) * 100, 2),
        }
    return comparisons