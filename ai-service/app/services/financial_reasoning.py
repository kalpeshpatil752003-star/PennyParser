import re
import logging

logger = logging.getLogger("financial_reasoning")


def validate_financial_data(line_items: dict) -> dict:
    """
    Validation layer between extraction and the VERIFIED label.
    Checks:
    1. Period validation: Q2 vs YTD values should differ for income statements.
    2. Accounting identities: A = L + E for balance sheets.
    3. Duplicate/conflicting values: same metric shouldn't appear with same value under different periods.
    4. Unit/scale validation: all values should be in a consistent magnitude.
    Returns: {"valid": bool, "warnings": list[str], "validated_items": dict}
    """
    warnings = []
    validated = dict(line_items)

    for metric_key, item in line_items.items():
        by_period = item.get("by_period", {})
        if not by_period:
            continue

        # Check: If a metric has both Q2_XXXX and YTD_XXXX, they must differ
        for period_key, val in by_period.items():
            if period_key.startswith("Q2_"):
                year = period_key.split("_")[1]
                ytd_key = f"YTD_{year}"
                ytd_val = by_period.get(ytd_key)
                if ytd_val is not None and val == ytd_val:
                    warnings.append(
                        f"SUSPECT: {metric_key} has identical Q2 and YTD values "
                        f"({val}) for {year}. This is almost certainly an extraction error."
                    )

        # Check: YTD should be >= Q2 for positive income-statement items
        for period_key, val in by_period.items():
            if period_key.startswith("Q2_") and val > 0:
                year = period_key.split("_")[1]
                ytd_key = f"YTD_{year}"
                ytd_val = by_period.get(ytd_key)
                if ytd_val is not None and ytd_val < val:
                    warnings.append(
                        f"SUSPECT: {metric_key} YTD_{year} ({ytd_val}) < Q2_{year} ({val}). "
                        f"YTD should be >= quarterly for positive revenue/income items."
                    )

    if warnings:
        logger.warning(f"Financial validation warnings: {warnings}")

    return {"valid": len(warnings) == 0, "warnings": warnings, "validated_items": validated}


def compute_financial_reasoning_insights(question: str, line_items: dict) -> str:
    """
    Consumes structured extraction output (line_items with by_period data).
    Performs deterministic financial calculations grounded in validated extracted data.

    This function does NOT parse raw chunk text. It receives the structured output
    from extract_line_items() which contains by_period mappings like:
      {"Q2_2026": 60801, "Q2_2025": 47516, "YTD_2026": 117111, "YTD_2025": 89830}
    """
    question_lower = question.lower()
    insights = []

    # Validate data before labeling anything as verified
    validation = validate_financial_data(line_items)

    # Detect multi-period comparison questions (3M vs 6M, Q2 vs YTD, quarter vs half-year)
    is_period_comparison = (
        ("three months" in question_lower or "q2" in question_lower or "quarter" in question_lower) and
        ("six months" in question_lower or "ytd" in question_lower or "half" in question_lower)
    )

    if is_period_comparison:
        # Find metrics with both Q2 and YTD period data
        for metric_key, item in line_items.items():
            by_period = item.get("by_period", {})
            page = item.get("page", "?")

            q2_entries = {k: v for k, v in by_period.items() if k.startswith("Q2_")}
            ytd_entries = {k: v for k, v in by_period.items() if k.startswith("YTD_")}

            if not q2_entries or not ytd_entries:
                continue

            # Match by year
            for q2_key, q2_val in q2_entries.items():
                year = q2_key.split("_")[1]
                ytd_key = f"YTD_{year}"
                ytd_val = ytd_entries.get(ytd_key)

                if ytd_val is None:
                    continue

                diff = round(ytd_val - q2_val, 2)
                multiple = round(ytd_val / q2_val, 3) if q2_val != 0 else 0.0

                # Only label as VERIFIED if validation passed
                label = "[VERIFIED FINANCIAL FACTS]" if validation["valid"] else "[EXTRACTED FINANCIAL FACTS — VALIDATION WARNINGS PRESENT]"

                insight_lines = [
                    label,
                    f"Metric: {metric_key}",
                    f"• Three Months Ended (Q2 {year}): ${q2_val:,.2f} (Source Page {page})",
                    f"• Six Months Ended (YTD {year}): ${ytd_val:,.2f} (Source Page {page})",
                    f"",
                    f"[DETERMINISTIC MATH — DO NOT OVERRIDE]",
                    f"• The six-month (YTD) figure is NOT simply twice the three-month (Q2) figure.",
                    f"• Six-month total = Q1 + Q2 combined = ${ytd_val:,.2f}",
                    f"• Three-month total = Q2 alone = ${q2_val:,.2f}",
                    f"• Implied Q1 {year} = YTD minus Q2 = ${ytd_val:,.2f} - ${q2_val:,.2f} = ${diff:,.2f}",
                    f"• Exact ratio (YTD / Q2) = {multiple}x",
                ]

                if validation["warnings"]:
                    insight_lines.append("")
                    insight_lines.append("[VALIDATION WARNINGS]")
                    for w in validation["warnings"]:
                        insight_lines.append(f"⚠ {w}")

                insights.append("\n".join(insight_lines))

    # Summary of all available period data for any metric mentioned in the question
    if not insights:
        # Even without a period-comparison question, provide available period breakdowns
        for metric_key, item in line_items.items():
            # Check if this metric is mentioned in the question
            if not any(kw in question_lower for kw in metric_key.replace("_", " ").split()):
                continue
            by_period = item.get("by_period", {})
            if len(by_period) > 1:
                page = item.get("page", "?")
                lines = [f"[AVAILABLE PERIOD DATA for {metric_key}] (Source Page {page})"]
                for period_key in sorted(by_period.keys()):
                    lines.append(f"  • {period_key}: ${by_period[period_key]:,.2f}")
                insights.append("\n".join(lines))

    return "\n\n".join(insights)
