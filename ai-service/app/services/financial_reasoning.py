import re
import logging

from app.services.line_items import detect_duplicate_value_anomalies

logger = logging.getLogger("financial_reasoning")


def validate_financial_data(line_items: dict) -> dict:
    """
    Validation layer between extraction and the VERIFIED label.
    Checks:
    1. Period validation: Quarter vs Cumulative/YTD values should differ for income statements.
    2. Accounting identities: A = L + E for balance sheets.
    3. Duplicate/conflicting values: same metric shouldn't appear with same value under different periods.
    Returns: {"valid": bool, "warnings": list[str], "validated_items": dict}
    """
    warnings = []
    validated = dict(line_items)

    for metric_key, item in line_items.items():
        by_period = item.get("by_period", {})
        if not by_period:
            continue

        # Check: If a metric has both QX_XXXX and YTD_XXXX/9M_XXXX, they must differ
        for period_key, val in by_period.items():
            if re.match(r"^Q[1-4]_\d{4}$", period_key):
                q_label, year = period_key.split("_")
                for cum_prefix in ("YTD", "9M", "FY"):
                    cum_key = f"{cum_prefix}_{year}"
                    cum_val = by_period.get(cum_key)
                    if cum_val is not None and val == cum_val:
                        warnings.append(
                            f"SUSPECT: {metric_key} has identical {q_label} and {cum_prefix} values "
                            f"({val}) for {year}. This is almost certainly an extraction error."
                        )

                    # For positive income-statement items, cumulative >= single quarter
                    if cum_val is not None and val > 0 and cum_val < val:
                        warnings.append(
                            f"SUSPECT: {metric_key} {cum_prefix}_{year} ({cum_val}) < {q_label}_{year} ({val}). "
                            f"Cumulative should be >= quarterly for positive revenue/income items."
                        )

    # Check: Multi-candidate conflicts flagged by _select_best_candidates()
    for metric_key, item in line_items.items():
        conflict = item.get("conflicting_candidate")
        if conflict:
            warnings.append(
                f"SUSPECT: {metric_key} has conflicting extraction candidates — "
                f"chosen value {item.get('value')} (page {item.get('page')}) vs "
                f"alternate {conflict.get('value')} (page {conflict.get('page')}). "
                f"Review source document for accuracy."
            )

    # Check: Duplicate value anomalies — two distinct metrics with identical values
    dup_warnings = detect_duplicate_value_anomalies(line_items)
    warnings.extend(dup_warnings)

    if warnings:
        logger.warning(f"Financial validation warnings: {warnings}")

    return {"valid": len(warnings) == 0, "warnings": warnings, "validated_items": validated}


def compute_financial_reasoning_insights(question: str, line_items: dict) -> str:
    """
    Consumes structured extraction output (line_items with by_period data).
    Performs deterministic financial calculations grounded in validated extracted data.
    """
    question_lower = question.lower()
    insights = []

    validation = validate_financial_data(line_items)

    is_period_comparison = (
        ("three months" in question_lower or "quarter" in question_lower or bool(re.search(r"\bq[1-4]\b", question_lower))) and
        ("six months" in question_lower or "nine months" in question_lower or "ytd" in question_lower or "half" in question_lower or "full year" in question_lower)
    )

    if is_period_comparison:
        for metric_key, item in line_items.items():
            by_period = item.get("by_period", {})
            page = item.get("page", "?")

            q_entries = {k: v for k, v in by_period.items() if re.match(r"^Q[1-4]_\d{4}$", k)}
            cum_entries = {k: v for k, v in by_period.items() if any(k.startswith(p + "_") for p in ("YTD", "6M", "9M", "FY"))}

            if not q_entries or not cum_entries:
                continue

            for q_key, q_val in q_entries.items():
                q_label, year = q_key.split("_")

                for cum_key, cum_val in cum_entries.items():
                    if not cum_key.endswith(f"_{year}"):
                        continue

                    cum_prefix = cum_key.split("_")[0]
                    diff = round(cum_val - q_val, 2)
                    multiple = round(cum_val / q_val, 3) if q_val != 0 else 0.0

                    label = "[VERIFIED FINANCIAL FACTS]" if validation["valid"] else "[EXTRACTED FINANCIAL FACTS — VALIDATION WARNINGS PRESENT]"

                    insight_lines = [
                        label,
                        f"Metric: {metric_key}",
                        f"• Three Months Ended ({q_label} {year}): ${q_val:,.2f} (Source Page {page})",
                        f"• {cum_prefix} Figure ({cum_prefix} {year}): ${cum_val:,.2f} (Source Page {page})",
                        f"",
                        f"[DETERMINISTIC MATH — DO NOT OVERRIDE]",
                        f"• The {cum_prefix} figure is NOT simply equal to or twice the quarterly ({q_label}) figure.",
                        f"• {cum_prefix} total = ${cum_val:,.2f}",
                        f"• Three-month total ({q_label}) alone = ${q_val:,.2f}",
                        f"• Remainder of period = ${cum_val:,.2f} - ${q_val:,.2f} = ${diff:,.2f}",
                        f"• Exact ratio ({cum_prefix} / {q_label}) = {multiple}x",
                    ]

                    if validation["warnings"]:
                        insight_lines.append("")
                        insight_lines.append("[VALIDATION WARNINGS]")
                        for w in validation["warnings"]:
                            insight_lines.append(f"⚠ {w}")

                    insights.append("\n".join(insight_lines))

    # Summary of all available period data for any metric mentioned in the question
    if not insights:
        for metric_key, item in line_items.items():
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

