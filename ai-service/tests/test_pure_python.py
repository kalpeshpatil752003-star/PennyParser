import unittest

from app.services.normalize import parse_number, is_footnote_marker
from app.services.ratios import calculate_ratios
from app.services.financial_extraction import detect_scale, score_table
from app.services.line_items import (
    reconstruct_label,
    reconcile_balance_sheet_identity,
    extract_line_items,
    _detect_period_headers,
    detect_duplicate_value_anomalies,
    _is_combined_liabilities_and_equity_row,
    compute_period_comparisons,
)
from app.services.financial_reasoning import (
    compute_financial_reasoning_insights,
    validate_financial_data,
)


class TestParseNumber(unittest.TestCase):

    def test_parse_number_variations(self):
        self.assertEqual(parse_number("$1,234"), 1234.0)
        self.assertEqual(parse_number("(1,234)"), -1234.0)
        self.assertEqual(parse_number("1,234.50"), 1234.50)
        self.assertEqual(parse_number("12.5%"), 12.5)
        self.assertEqual(parse_number("1,234*"), 1234.0)
        self.assertEqual(parse_number("1,234a"), 1234.0)
        self.assertEqual(parse_number("1,234(1)"), 1234.0)
        self.assertIsNone(parse_number("-"))
        self.assertIsNone(parse_number("—"))
        self.assertIsNone(parse_number("N/A"))

    def test_footnote_marker_exclusion(self):
        self.assertTrue(is_footnote_marker("(1)"))
        self.assertTrue(is_footnote_marker("[1]"))
        self.assertTrue(is_footnote_marker("(a)"))
        self.assertTrue(is_footnote_marker("*"))
        self.assertIsNone(parse_number("(1)"))
        self.assertIsNone(parse_number("[1]"))
        self.assertIsNone(parse_number("(a)"))


class TestLabelReconstruction(unittest.TestCase):

    def test_reconstruct_fragmented_label(self):
        self.assertEqual(reconstruct_label(["Total liabiliti", "es"]), "total liabilities")
        self.assertEqual(
            reconstruct_label(["Total liabilities a", "nd stockholders' equity"]),
            "total liabilities and stockholders equity",
        )

    def test_reconstruct_clean_label(self):
        self.assertEqual(reconstruct_label(["Total assets"]), "total assets")
        self.assertEqual(reconstruct_label(["Revenue"]), "revenue")

    def test_reconstruct_empty(self):
        self.assertEqual(reconstruct_label([]), "")
        self.assertEqual(reconstruct_label(["", "", ""]), "")


class TestPeriodHeaderDetection(unittest.TestCase):
    """
    Tests dynamic quarter and period detection for Q1, Q2, Q3, 9M, and FY.
    """

    def test_q1_headers(self):
        rows = [
            ["", "Three Months Ended March 31,", ""],
            ["", "2026", "2025"],
        ]
        period_map = _detect_period_headers(rows)
        self.assertEqual(period_map[1], "Q1_2026")
        self.assertEqual(period_map[2], "Q1_2025")

    def test_q2_multi_period_headers(self):
        rows = [
            ["", "Three Months Ended June 30,", "", "Six Months Ended June 30,", ""],
            ["", "2026", "2025", "2026", "2025"],
        ]
        period_map = _detect_period_headers(rows)
        self.assertEqual(period_map[1], "Q2_2026")
        self.assertEqual(period_map[2], "Q2_2025")
        self.assertEqual(period_map[3], "YTD_2026")
        self.assertEqual(period_map[4], "YTD_2025")

    def test_q3_nine_months_headers(self):
        rows = [
            ["", "Three Months Ended September 30,", "", "Nine Months Ended September 30,", ""],
            ["", "2026", "2025", "2026", "2025"],
        ]
        period_map = _detect_period_headers(rows)
        self.assertEqual(period_map[1], "Q3_2026")
        self.assertEqual(period_map[2], "Q3_2025")
        self.assertEqual(period_map[3], "9M_2026")
        self.assertEqual(period_map[4], "9M_2025")

    def test_balance_sheet_plain_years(self):
        rows = [
            ["", "June 30, 2026", "December 31, 2025"],
            ["", "2026", "2025"],
        ]
        period_map = _detect_period_headers(rows)
        self.assertIn("2026", period_map.values())
        self.assertIn("2025", period_map.values())


class TestMetricContaminationPrevention(unittest.TestCase):
    """
    Tests that substring matching does NOT contaminate metrics.
    """

    def test_deferred_revenue_does_not_match_revenue(self):
        mock_balance_table = {
            "page_number": 4,
            "statement_type": "BALANCE",
            "rows": [
                ["", "2026", "2025"],
                ["Accounts payable", "15,000", "12,000"],
                ["Deferred revenue", "8,500", "7,200"],
                ["Total liabilities", "50,000", "40,000"],
                ["Total stockholders' equity", "60,000", "50,000"],
                ["Total assets", "110,000", "90,000"],
            ]
        }
        mock_income_table = {
            "page_number": 5,
            "statement_type": "INCOME",
            "rows": [
                ["", "2026", "2025"],
                ["Revenue", "120,000", "95,000"],
                ["Cost of revenue", "40,000", "30,000"],
                ["Operating income", "35,000", "28,000"],
                ["Net income", "25,000", "20,000"],
            ]
        }

        # Even if Balance Sheet appears first, revenue MUST come from Income statement, not Deferred revenue
        items = extract_line_items([mock_balance_table, mock_income_table])
        self.assertEqual(items["revenue"]["value"], 120000.0)
        self.assertNotEqual(items["revenue"]["value"], 8500.0)

    def test_diluted_shares_does_not_match_eps(self):
        mock_income_table = {
            "page_number": 5,
            "statement_type": "INCOME",
            "rows": [
                ["", "2026", "2025"],
                ["Net income", "18,271", "14,017"],
                ["Diluted weighted-average shares outstanding", "2,548", "2,576"],
                ["Diluted earnings per share", "7.17", "5.44"],
            ]
        }
        items = extract_line_items([mock_income_table])
        self.assertIn("eps_diluted", items)
        self.assertEqual(items["eps_diluted"]["value"], 7.17)
        self.assertNotEqual(items["eps_diluted"]["value"], 2548.0)

    def test_real_financial_value_in_year_range(self):
        """Values in 1900-2100 in data rows must NOT be eaten as year headers."""
        mock_income_table = {
            "page_number": 5,
            "statement_type": "INCOME",
            "rows": [
                ["", "2026"],
                ["Revenue", "10,000"],
                ["Net income", "2,024"],
            ]
        }
        items = extract_line_items([mock_income_table])
        self.assertIn("net_income", items)
        self.assertEqual(items["net_income"]["value"], 2024.0)


class TestIncomeStatementExtraction(unittest.TestCase):

    def _make_meta_income_table(self):
        return {
            "page_number": 5,
            "statement_type": "INCOME",
            "rows": [
                ["", "Three Months Ended June 30,", "", "Six Months Ended June 30,", ""],
                ["", "2026", "2025", "2026", "2025"],
                ["Revenue", "60,801", "47,516", "117,111", "89,830"],
                ["Cost of revenue", "19,858", "14,857", "38,205", "28,478"],
                ["Gross profit", "40,943", "32,659", "78,906", "61,352"],
                ["Operating income", "22,653", "18,389", "41,498", "31,634"],
                ["Net income", "18,271", "14,017", "32,835", "24,120"],
            ],
        }

    def test_revenue_period_distinction(self):
        tables = [self._make_meta_income_table()]
        items = extract_line_items(tables)

        self.assertIn("revenue", items)
        by_period = items["revenue"]["by_period"]

        self.assertIn("Q2_2026", by_period)
        self.assertIn("YTD_2026", by_period)
        self.assertEqual(by_period["Q2_2026"], 60801.0)
        self.assertEqual(by_period["YTD_2026"], 117111.0)
        self.assertNotEqual(by_period["Q2_2026"], by_period["YTD_2026"])


class TestScaleDetection(unittest.TestCase):

    def test_detect_scale(self):
        self.assertEqual(detect_scale("CONSOLIDATED STATEMENTS OF OPERATIONS ($ in millions)")["scale"], "millions")
        self.assertEqual(detect_scale("In thousands, except per share amounts")["scale"], "thousands")
        self.assertEqual(detect_scale("Amounts in billions")["scale"], "billions")
        self.assertEqual(detect_scale("Plain report")["scale"], "units")


class TestFinancialReasoning(unittest.TestCase):

    def test_period_comparison_math(self):
        line_items = {
            "revenue": {
                "value": 60801.0,
                "by_period": {
                    "Q2_2026": 60801.0,
                    "Q2_2025": 47516.0,
                    "YTD_2026": 117111.0,
                    "YTD_2025": 89830.0,
                },
                "page": 5,
                "statement_type": "INCOME",
            }
        }

        question = "What was the revenue for the three months ended June 30, 2026 compared with six months ended June 30, 2026?"
        insights = compute_financial_reasoning_insights(question, line_items)

        self.assertIn("60,801", insights)
        self.assertIn("117,111", insights)
        self.assertIn("56,310", insights)
        self.assertIn("1.926", insights)

    def test_validation_catches_identical_q2_ytd(self):
        line_items = {
            "revenue": {
                "value": 60801.0,
                "by_period": {
                    "Q2_2026": 60801.0,
                    "YTD_2026": 60801.0,
                },
                "page": 5,
            }
        }
        result = validate_financial_data(line_items)
        self.assertFalse(result["valid"])


class TestBalanceSheetReconciliation(unittest.TestCase):

    def test_pdfplumber_split_cell_extraction(self):
        mock_tables = [
            {
                "page_number": 6,
                "statement_type": "BALANCE",
                "rows": [
                    ["", "2026", "2025"],
                    ["Total current assets", "", "125,475"],
                    ["Total assets", "", "449,956"],
                    ["Total current liabilities", "", "56,379"],
                    ["Total liabiliti", "es", "", "188,735"],
                    ["Total stockholders' equity", "", "261,221"],
                    ["Total liabilities a", "nd stockholders' equity", "", "449,956"],
                ],
            }
        ]
        items = extract_line_items(mock_tables)
        self.assertEqual(items["total_assets"]["value"], 449956.0)
        self.assertEqual(items["total_liabilities"]["value"], 188735.0)
        self.assertEqual(items["total_equity"]["value"], 261221.0)


class TestRatioCalculations(unittest.TestCase):

    def test_standard_ratios(self):
        items = {
            "revenue": {"value": 1000.0},
            "cost_of_goods_sold": {"value": 600.0},
            "gross_profit": {"value": 400.0},
            "operating_income": {"value": 200.0},
            "net_income": {"value": 150.0},
            "total_assets": {"value": 1500.0},
            "total_liabilities": {"value": 500.0},
            "total_equity": {"value": 1000.0},
            "current_assets": {"value": 600.0},
            "current_liabilities": {"value": 300.0},
        }
        ratios = calculate_ratios(items)
        self.assertEqual(ratios["gross_margin_pct"], 40.0)
        self.assertEqual(ratios["operating_margin_pct"], 20.0)
        self.assertEqual(ratios["net_margin_pct"], 15.0)
        self.assertEqual(ratios["roe_pct"], 15.0)
        self.assertEqual(ratios["roa_pct"], 10.0)
        self.assertEqual(ratios["debt_to_equity"], 0.5)
        self.assertEqual(ratios["current_ratio"], 2.0)


class TestScaleMultiplierApplication(unittest.TestCase):
    """Fix 1: scale multiplier is applied to dollar-amount line items but NOT to EPS."""

    def test_revenue_scaled_by_millions(self):
        """A $1,234 cell in a table marked 'in millions' should become 1,234,000,000."""
        mock_table = {
            "page_number": 1,
            "statement_type": "INCOME",
            "scale": {"multiplier": 1_000_000.0, "scale": "millions", "display": "$ in millions"},
            "table_quality_score": 1.0,
            "rows": [
                ["", "2026"],
                ["Total revenue", "1,234"],
                ["Cost of revenue", "500"],
                ["Gross profit", "734"],
                ["Operating income", "300"],
                ["Net income", "200"],
                ["Diluted earnings per share", "2.34"],
            ],
        }
        items = extract_line_items([mock_table])
        self.assertEqual(items["revenue"]["value"], 1_234_000_000.0)
        self.assertEqual(items["revenue"]["scale_applied"], "millions")

    def test_eps_not_scaled(self):
        """EPS is per-share, should NOT be multiplied by the scale factor."""
        mock_table = {
            "page_number": 1,
            "statement_type": "INCOME",
            "scale": {"multiplier": 1_000_000.0, "scale": "millions"},
            "table_quality_score": 1.0,
            "rows": [
                ["", "2026"],
                ["Revenue", "1,234"],
                ["Cost of revenue", "500"],
                ["Gross profit", "734"],
                ["Operating income", "300"],
                ["Net income", "200"],
                ["Diluted earnings per share", "2.34"],
            ],
        }
        items = extract_line_items([mock_table])
        self.assertIn("eps_diluted", items)
        self.assertEqual(items["eps_diluted"]["value"], 2.34)
        # Also verify it is NOT 2_340_000
        self.assertNotEqual(items["eps_diluted"]["value"], 2_340_000.0)

    def test_scale_units_no_change(self):
        """When scale is 'units' (multiplier 1.0), values should pass through unchanged."""
        mock_table = {
            "page_number": 2,
            "statement_type": "INCOME",
            "scale": {"multiplier": 1.0, "scale": "units"},
            "table_quality_score": 1.0,
            "rows": [
                ["", "2026"],
                ["Revenue", "60,801"],
                ["Cost of revenue", "19,858"],
                ["Gross profit", "40,943"],
                ["Operating income", "22,653"],
                ["Net income", "18,271"],
            ],
        }
        items = extract_line_items([mock_table])
        self.assertEqual(items["revenue"]["value"], 60801.0)

    def test_thousands_scale(self):
        """Tables marked 'in thousands' should multiply values by 1000."""
        mock_table = {
            "page_number": 1,
            "statement_type": "INCOME",
            "scale": {"multiplier": 1_000.0, "scale": "thousands"},
            "table_quality_score": 1.0,
            "rows": [
                ["", "2026"],
                ["Revenue", "5,000"],
                ["Cost of revenue", "2,000"],
                ["Gross profit", "3,000"],
                ["Operating income", "1,500"],
                ["Net income", "1,000"],
            ],
        }
        items = extract_line_items([mock_table])
        self.assertEqual(items["revenue"]["value"], 5_000_000.0)
        self.assertEqual(items["net_income"]["value"], 1_000_000.0)


class TestMultiCandidateScoring(unittest.TestCase):
    """Fix 2: multi-candidate matching picks the best table, not just the first."""

    def test_higher_quality_table_wins(self):
        """Table with more periods and higher quality should be preferred over a first-seen match."""
        # Table 1: lower quality, 1 period column
        table_low = {
            "page_number": 3,
            "statement_type": "INCOME",
            "scale": {"multiplier": 1.0, "scale": "units"},
            "table_quality_score": 0.3,
            "rows": [
                ["", "2025"],
                ["Revenue", "40,000"],
                ["Cost of revenue", "15,000"],
                ["Gross profit", "25,000"],
                ["Operating income", "10,000"],
                ["Net income", "8,000"],
            ],
        }
        # Table 2: higher quality, 2 period columns
        table_high = {
            "page_number": 5,
            "statement_type": "INCOME",
            "scale": {"multiplier": 1.0, "scale": "units"},
            "table_quality_score": 0.9,
            "rows": [
                ["", "2026", "2025"],
                ["Revenue", "60,000", "45,000"],
                ["Cost of revenue", "20,000", "15,000"],
                ["Gross profit", "40,000", "30,000"],
                ["Operating income", "22,000", "18,000"],
                ["Net income", "15,000", "12,000"],
            ],
        }
        # Pass low-quality first — old code would lock it in
        items = extract_line_items([table_low, table_high])
        # Higher quality table should win
        self.assertEqual(items["revenue"]["value"], 60000.0)
        self.assertEqual(items["revenue"]["page"], 5)

    def test_conflicting_candidate_populated(self):
        """When top-2 candidates disagree by >2%, conflicting_candidate should be set."""
        table_a = {
            "page_number": 2,
            "statement_type": "INCOME",
            "scale": {"multiplier": 1.0, "scale": "units"},
            "table_quality_score": 0.5,
            "rows": [
                ["", "2026"],
                ["Revenue", "50,000"],
                ["Cost of revenue", "20,000"],
                ["Gross profit", "30,000"],
                ["Operating income", "10,000"],
                ["Net income", "7,500"],
            ],
        }
        table_b = {
            "page_number": 4,
            "statement_type": "INCOME",
            "scale": {"multiplier": 1.0, "scale": "units"},
            "table_quality_score": 0.8,
            "rows": [
                ["", "2026", "2025"],
                ["Revenue", "60,000", "45,000"],
                ["Cost of revenue", "20,000", "15,000"],
                ["Gross profit", "40,000", "30,000"],
                ["Operating income", "22,000", "18,000"],
                ["Net income", "15,000", "10,000"],
            ],
        }
        items = extract_line_items([table_a, table_b])
        # Revenue: 60,000 vs 50,000 — >2% difference — conflict should exist
        self.assertIn("conflicting_candidate", items["revenue"])
        self.assertEqual(items["revenue"]["conflicting_candidate"]["value"], 50000.0)


class TestDocxPageLabeling(unittest.TestCase):
    """Fix 3: DOCX tables should have page_number=None and a real table_index."""

    def test_docx_null_page_handling(self):
        """Tables from DOCX extraction (page_number=None) should work correctly in extract_line_items."""
        mock_docx_table = {
            "page_number": None,
            "table_index": 3,
            "statement_type": "INCOME",
            "scale": {"multiplier": 1.0, "scale": "units"},
            "rows": [
                ["", "2026"],
                ["Revenue", "100,000"],
                ["Cost of revenue", "40,000"],
                ["Gross profit", "60,000"],
                ["Operating income", "30,000"],
                ["Net income", "20,000"],
            ],
        }
        items = extract_line_items([mock_docx_table])
        self.assertIn("revenue", items)
        self.assertEqual(items["revenue"]["value"], 100000.0)
        # Page should be None (honest), table_index preserved
        self.assertIsNone(items["revenue"]["page"])
        self.assertEqual(items["revenue"]["table_index"], 3)


class TestLocaleAwareParsing(unittest.TestCase):
    """Fix 4: parse_number should handle European and Indian number formats."""

    def test_us_format_unchanged(self):
        """US format continues to work identically (backward compat)."""
        self.assertEqual(parse_number("$1,234", locale="en_US"), 1234.0)
        self.assertEqual(parse_number("(1,234.56)", locale="en_US"), -1234.56)
        self.assertEqual(parse_number("1,234.50", locale="en_US"), 1234.50)

    def test_european_decimal_comma(self):
        """German/European format: period as thousands separator, comma as decimal."""
        self.assertEqual(parse_number("1.234,56", locale="de_DE"), 1234.56)

    def test_indian_lakh_grouping(self):
        """Indian format: lakh-style grouping (12,34,567)."""
        self.assertEqual(parse_number("12,34,567", locale="en_IN"), 1234567.0)

    def test_default_locale_is_us(self):
        """When no locale is specified, default US behavior applies."""
        self.assertEqual(parse_number("1,234"), 1234.0)
        self.assertIsNone(parse_number("-"))
        self.assertIsNone(parse_number("N/A"))


# =============================================================================
# Tier 1 Fix Tests
# =============================================================================

class TestEpsSplit(unittest.TestCase):
    """Fix 1: EPS is split into eps_basic and eps_diluted as separate metrics."""

    def test_both_eps_extracted_separately(self):
        """Both basic and diluted EPS should appear as distinct metrics."""
        mock_table = {
            "page_number": 5,
            "statement_type": "INCOME",
            "rows": [
                ["", "2026", "2025"],
                ["Net income", "18,271", "14,017"],
                ["Basic earnings per share", "7.25", "5.50"],
                ["Diluted earnings per share", "7.17", "5.44"],
            ]
        }
        items = extract_line_items([mock_table])
        self.assertIn("eps_basic", items)
        self.assertIn("eps_diluted", items)
        self.assertEqual(items["eps_basic"]["value"], 7.25)
        self.assertEqual(items["eps_diluted"]["value"], 7.17)

    def test_eps_basic_excludes_diluted_rows(self):
        """eps_basic must not match a row labeled 'diluted earnings per share'."""
        mock_table = {
            "page_number": 5,
            "statement_type": "INCOME",
            "rows": [
                ["", "2026"],
                ["Net income", "18,271"],
                ["Diluted earnings per share", "7.17"],
            ]
        }
        items = extract_line_items([mock_table])
        self.assertNotIn("eps_basic", items)
        self.assertIn("eps_diluted", items)

    def test_eps_diluted_excludes_basic_rows(self):
        """eps_diluted must not match a row labeled 'basic earnings per share'."""
        mock_table = {
            "page_number": 5,
            "statement_type": "INCOME",
            "rows": [
                ["", "2026"],
                ["Net income", "18,271"],
                ["Basic earnings per share", "7.25"],
            ]
        }
        items = extract_line_items([mock_table])
        self.assertNotIn("eps_diluted", items)
        self.assertIn("eps_basic", items)

    def test_no_single_word_catchall(self):
        """Single words 'diluted' or 'basic' should NOT match as EPS."""
        mock_table = {
            "page_number": 5,
            "statement_type": "INCOME",
            "rows": [
                ["", "2026"],
                ["Net income", "18,271"],
                ["Diluted weighted-average shares outstanding", "2,548"],
            ]
        }
        items = extract_line_items([mock_table])
        self.assertNotIn("eps_basic", items)
        self.assertNotIn("eps_diluted", items)


class TestOrderAgnosticExclusion(unittest.TestCase):
    """Fix 2a: Combined liabilities+equity rows should not match as total_equity or total_liabilities."""

    def test_combined_row_not_matched_as_equity(self):
        self.assertTrue(_is_combined_liabilities_and_equity_row("total liabilities and stockholders equity"))
        self.assertTrue(_is_combined_liabilities_and_equity_row("total equity and liabilities"))

    def test_standalone_equity_not_blocked(self):
        self.assertFalse(_is_combined_liabilities_and_equity_row("total stockholders equity"))
        self.assertFalse(_is_combined_liabilities_and_equity_row("total equity"))

    def test_standalone_liabilities_not_blocked(self):
        self.assertFalse(_is_combined_liabilities_and_equity_row("total liabilities"))

    def test_real_world_combined_row_extraction(self):
        """The actual NVIDIA-style row should be excluded from total_equity matching."""
        mock_tables = [
            {
                "page_number": 6,
                "statement_type": "BALANCE",
                "rows": [
                    ["", "2026", "2025"],
                    ["Total assets", "449,956", "400,000"],
                    ["Total liabilities", "188,735", "160,000"],
                    ["Total stockholders' equity", "261,221", "240,000"],
                    ["Total liabilities and stockholders' equity", "449,956", "400,000"],
                ],
            }
        ]
        items = extract_line_items(mock_tables)
        # Equity must NOT equal assets — the combined row should be excluded
        self.assertEqual(items["total_equity"]["value"], 261221.0)
        self.assertNotEqual(items["total_equity"]["value"], items["total_assets"]["value"])


class TestDuplicateValueAnomalies(unittest.TestCase):
    """Fix 2b: Duplicate value detection catches equity=assets bug."""

    def test_flags_identical_values(self):
        found = {
            "total_assets": {"value": 449956.0},
            "total_equity": {"value": 449956.0},
            "total_liabilities": {"value": 188735.0},
        }
        warnings = detect_duplicate_value_anomalies(found)
        self.assertTrue(len(warnings) > 0)
        self.assertIn("SUSPECT", warnings[0])

    def test_no_flag_for_distinct_values(self):
        found = {
            "total_assets": {"value": 449956.0},
            "total_equity": {"value": 261221.0},
            "total_liabilities": {"value": 188735.0},
        }
        warnings = detect_duplicate_value_anomalies(found)
        self.assertEqual(len(warnings), 0)

    def test_zero_values_not_flagged(self):
        found = {
            "metric_a": {"value": 0},
            "metric_b": {"value": 0},
        }
        warnings = detect_duplicate_value_anomalies(found)
        self.assertEqual(len(warnings), 0)


class TestSymmetricReconciliation(unittest.TestCase):
    """Fix 3: When equity is wrong (equals assets), reconciliation should fix equity, not liabilities."""

    def test_equity_equals_assets_gets_fixed(self):
        """If E = A (a known extraction bug), the reconciler should recompute equity = A - L."""
        found = {
            "total_assets": {
                "value": 449956.0, "by_period": {"2026": 449956.0}, "confidence": 0.9
            },
            "total_liabilities": {
                "value": 188735.0, "by_period": {"2026": 188735.0}, "confidence": 0.9
            },
            "total_equity": {
                "value": 449956.0, "by_period": {"2026": 449956.0}, "confidence": 0.3
            },
        }
        result = reconcile_balance_sheet_identity(found)
        # Equity should be recomputed as A - L = 261221
        self.assertAlmostEqual(result["total_equity"]["value"], 261221.0, places=1)
        self.assertTrue(result["total_equity"].get("reconciled", False))

    def test_correct_identity_untouched(self):
        """When A = L + E holds, nothing should change."""
        found = {
            "total_assets": {"value": 100.0, "by_period": {}, "confidence": 0.9},
            "total_liabilities": {"value": 60.0, "by_period": {}, "confidence": 0.9},
            "total_equity": {"value": 40.0, "by_period": {}, "confidence": 0.9},
        }
        result = reconcile_balance_sheet_identity(found)
        self.assertEqual(result["total_assets"]["value"], 100.0)
        self.assertEqual(result["total_liabilities"]["value"], 60.0)
        self.assertEqual(result["total_equity"]["value"], 40.0)
        self.assertFalse(result["total_equity"].get("reconciled", False))

    def test_liabilities_wrong_gets_fixed(self):
        """If L is the weakest leg (e.g. combined total), it should be recomputed."""
        found = {
            "total_assets": {
                "value": 100.0, "by_period": {}, "confidence": 0.9
            },
            "total_liabilities": {
                "value": 100.0, "by_period": {}, "confidence": 0.2
            },
            "total_equity": {
                "value": 40.0, "by_period": {}, "confidence": 0.9
            },
        }
        result = reconcile_balance_sheet_identity(found)
        self.assertAlmostEqual(result["total_liabilities"]["value"], 60.0, places=1)
        self.assertTrue(result["total_liabilities"].get("reconciled", False))


class TestComputePeriodComparisons(unittest.TestCase):
    """Fix 4: Server-side period comparison computation."""

    def test_income_statement_comparison(self):
        line_items = {
            "revenue": {
                "value": 60801.0,
                "by_period": {"Q2_2026": 60801.0, "Q2_2025": 47516.0},
            }
        }
        comps = compute_period_comparisons(line_items)
        self.assertIn("revenue", comps)
        self.assertEqual(comps["revenue"]["current_period"], "Q2_2026")
        self.assertEqual(comps["revenue"]["prior_period"], "Q2_2025")
        self.assertAlmostEqual(comps["revenue"]["pct_change"], 27.96, places=1)

    def test_balance_sheet_bare_year_comparison(self):
        line_items = {
            "total_assets": {
                "value": 449956.0,
                "by_period": {"2026": 449956.0, "2025": 400000.0},
            }
        }
        comps = compute_period_comparisons(line_items)
        self.assertIn("total_assets", comps)
        self.assertEqual(comps["total_assets"]["current_period"], "2026")
        self.assertEqual(comps["total_assets"]["prior_period"], "2025")

    def test_single_period_no_comparison(self):
        line_items = {
            "revenue": {
                "value": 60801.0,
                "by_period": {"Q2_2026": 60801.0},
            }
        }
        comps = compute_period_comparisons(line_items)
        self.assertNotIn("revenue", comps)

    def test_mixed_period_keys(self):
        """Handles FY and quarterly keys together."""
        line_items = {
            "revenue": {
                "value": 100.0,
                "by_period": {"Q2_2026": 100.0, "YTD_2026": 180.0, "Q2_2025": 80.0},
            }
        }
        comps = compute_period_comparisons(line_items)
        self.assertIn("revenue", comps)
        # YTD_2026 (year=2026, quarter=4 fallback) is most recent, Q2_2026 is next
        self.assertEqual(comps["revenue"]["current_period"], "YTD_2026")
        self.assertEqual(comps["revenue"]["prior_period"], "Q2_2026")


class TestDuplicateValueInValidation(unittest.TestCase):
    """Verify duplicate-value detection is wired into validate_financial_data."""

    def test_validation_catches_duplicate_values(self):
        line_items = {
            "total_assets": {"value": 449956.0, "by_period": {}},
            "total_equity": {"value": 449956.0, "by_period": {}},
        }
        result = validate_financial_data(line_items)
        self.assertFalse(result["valid"])
        self.assertTrue(any("SUSPECT" in w and "identical values" in w for w in result["warnings"]))


class TestPhase1PeriodKeyedSchema(unittest.TestCase):
    """
    Phase 1: Validates the period-keyed structure, canonical internal dollar units,
    source/confidence tags, and separate audit metadata.
    """

    def test_period_keyed_structure_and_metadata(self):
        mock_table = {
            "page_number": 2,
            "statement_type": "INCOME",
            "scale": {"multiplier": 1_000_000.0, "scale": "millions", "display": "$ in millions"},
            "table_quality_score": 0.95,
            "rows": [
                ["", "Three Months Ended June 30,", ""],
                ["", "2026", "2025"],
                ["Total revenue", "60,801", "47,516"],
                ["Cost of revenue", "19,858", "16,000"],
                ["Gross profit", "40,943", "31,516"],
                ["Net income", "31,499", "25,000"],
                ["Diluted earnings per share", "7.17", "5.44"],
            ],
        }
        items = extract_line_items([mock_table])

        # 1. Must be a list of period objects
        self.assertIsInstance(items, list)
        self.assertEqual(len(items), 2)

        # 2. Check period metadata on primary period
        p_curr = items[0]
        self.assertEqual(p_curr["period_key"], "Q2_2026")
        self.assertEqual(p_curr["period_type"], "duration")
        self.assertEqual(p_curr["fiscal_year"], 2026)
        self.assertEqual(p_curr["quarter"], "Q2")
        self.assertIn("2026", p_curr["label"])

        # 3. Flat metric fields on period object with absolute canonical dollars
        self.assertIn("revenue", p_curr)
        self.assertEqual(p_curr["revenue"]["value"], 60_801_000_000.0)
        self.assertEqual(p_curr["revenue"]["source"], "extracted")
        self.assertEqual(p_curr["revenue"]["source_page"], 2)
        self.assertGreaterEqual(p_curr["revenue"]["confidence"], 0.5)

        # 4. EPS is not scaled by millions multiplier
        self.assertIn("eps_diluted", p_curr)
        self.assertEqual(p_curr["eps_diluted"]["value"], 7.17)
        self.assertEqual(p_curr["eps_diluted"]["source"], "extracted")

        # 5. Prior period also retained as distinct period object
        p_prior = items[1]
        self.assertEqual(p_prior["period_key"], "Q2_2025")
        self.assertEqual(p_prior["revenue"]["value"], 47_516_000_000.0)

        # 6. Audit metadata preserved separately, not as storage unit
        self.assertEqual(items.audit_metadata["source_scale"], "millions")
        self.assertEqual(items.audit_metadata["multiplier"], 1_000_000.0)
        self.assertEqual(items.audit_metadata["source_scale_display"], "$ in millions")

    def test_balance_sheet_point_in_time_period_type(self):
        mock_balance_table = {
            "page_number": 3,
            "statement_type": "BALANCE",
            "scale": {"multiplier": 1_000.0, "scale": "thousands", "display": "$ in thousands"},
            "table_quality_score": 0.9,
            "rows": [
                ["", "June 30, 2026", "December 31, 2025"],
                ["", "2026", "2025"],
                ["Total assets", "450,000", "400,000"],
                ["Total liabilities", "190,000", "160,000"],
                ["Total stockholders' equity", "260,000", "240,000"],
            ],
        }
        items = extract_line_items([mock_balance_table])
        self.assertIsInstance(items, list)
        self.assertGreaterEqual(len(items), 1)

        p = items[0]
        self.assertEqual(p["period_type"], "point_in_time")
        self.assertEqual(p["fiscal_year"], 2026)
        self.assertIsNotNone(p["as_of_date"])
        self.assertIn("2026", p["as_of_date"])
        # Canonical units: 450,000 * 1000 = 450,000,000
        self.assertEqual(p["total_assets"]["value"], 450_000_000.0)
        self.assertEqual(p["total_assets"]["source"], "extracted")


if __name__ == "__main__":
    unittest.main()
