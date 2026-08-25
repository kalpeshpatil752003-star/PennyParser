import unittest

from app.services.normalize import parse_number
from app.services.ratios import calculate_ratios
from app.services.line_items import (
    reconstruct_label,
    validate_and_reconcile_balance_sheet,
    extract_line_items,
    _detect_period_headers,
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
        self.assertIsNone(parse_number("-"))
        self.assertIsNone(parse_number("—"))
        self.assertIsNone(parse_number("N/A"))


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
    Tests _detect_period_headers which maps table columns to period keys.
    This is the core fix: income statements with 'Three Months Ended' and 'Six Months Ended'
    column groups must produce Q2_YEAR and YTD_YEAR keys, not just YEAR.
    """

    def test_income_statement_multi_period_headers(self):
        """Simulates a Meta-style income statement with 4 data columns:
        Three Months Ended June 30, [2026, 2025]  |  Six Months Ended June 30, [2026, 2025]
        """
        rows = [
            ["", "Three Months Ended June 30,", "", "Six Months Ended June 30,", ""],
            ["", "2026", "2025", "2026", "2025"],
        ]
        period_map = _detect_period_headers(rows)

        self.assertEqual(period_map[1], "Q2_2026")
        self.assertEqual(period_map[2], "Q2_2025")
        self.assertEqual(period_map[3], "YTD_2026")
        self.assertEqual(period_map[4], "YTD_2025")

    def test_balance_sheet_plain_years(self):
        """Balance sheets typically have plain year columns without period qualifiers."""
        rows = [
            ["", "June 30, 2026", "December 31, 2025"],
            ["", "2026", "2025"],
        ]
        period_map = _detect_period_headers(rows)
        # No period qualifier phrases → plain year keys
        self.assertIn("2026", period_map.values())
        self.assertIn("2025", period_map.values())
        self.assertNotIn("Q2_2026", period_map.values())
        self.assertNotIn("YTD_2026", period_map.values())


class TestIncomeStatementExtraction(unittest.TestCase):
    """
    Regression test for the Meta Q2 2026 bug.
    Revenue must have DISTINCT values for Q2_2026 vs YTD_2026.
    """

    def _make_meta_income_table(self):
        return {
            "page_number": 5,
            "statement_type": "INCOME",
            "rows": [
                # Header row 1: period qualifiers spanning column groups
                ["", "Three Months Ended June 30,", "", "Six Months Ended June 30,", ""],
                # Header row 2: year numbers under each qualifier
                ["", "2026", "2025", "2026", "2025"],
                # Data rows
                ["Revenue", "60,801", "47,516", "117,111", "89,830"],
                ["Cost of revenue", "19,858", "14,857", "38,205", "28,478"],
                ["Gross profit", "40,943", "32,659", "78,906", "61,352"],
                ["Operating income", "22,653", "18,389", "41,498", "31,634"],
                ["Net income", "18,271", "14,017", "32,835", "24,120"],
            ],
        }

    def test_revenue_period_distinction(self):
        """
        CRITICAL REGRESSION TEST:
        Revenue for Q2_2026 = 60,801 and YTD_2026 = 117,111.
        These MUST be different values. If they are the same, extraction is broken.
        """
        tables = [self._make_meta_income_table()]
        items = extract_line_items(tables)

        self.assertIn("revenue", items)
        by_period = items["revenue"]["by_period"]

        self.assertIn("Q2_2026", by_period)
        self.assertIn("YTD_2026", by_period)
        self.assertEqual(by_period["Q2_2026"], 60801.0)
        self.assertEqual(by_period["YTD_2026"], 117111.0)

        # The FAILING assertion from the original bug:
        # six_month_revenue must NOT equal three_month_revenue
        self.assertNotEqual(by_period["Q2_2026"], by_period["YTD_2026"])

    def test_all_periods_extracted(self):
        tables = [self._make_meta_income_table()]
        items = extract_line_items(tables)

        revenue_periods = items["revenue"]["by_period"]
        self.assertEqual(revenue_periods["Q2_2026"], 60801.0)
        self.assertEqual(revenue_periods["Q2_2025"], 47516.0)
        self.assertEqual(revenue_periods["YTD_2026"], 117111.0)
        self.assertEqual(revenue_periods["YTD_2025"], 89830.0)

    def test_net_income_periods(self):
        tables = [self._make_meta_income_table()]
        items = extract_line_items(tables)

        self.assertIn("net_income", items)
        ni = items["net_income"]["by_period"]
        self.assertEqual(ni["Q2_2026"], 18271.0)
        self.assertEqual(ni["YTD_2026"], 32835.0)


class TestFinancialReasoning(unittest.TestCase):
    """
    Tests the deterministic reasoning engine with structured period data.
    """

    def test_period_comparison_math(self):
        """Regression: compute_financial_reasoning_insights must produce correct
        Q1 = YTD - Q2 = 117111 - 60801 = 56310."""
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

        question = (
            "What was the revenue for the three months ended June 30, 2026 "
            "compared with six months ended June 30, 2026?"
        )
        insights = compute_financial_reasoning_insights(question, line_items)

        self.assertIn("60,801", insights)
        self.assertIn("117,111", insights)
        self.assertIn("56,310", insights)
        self.assertIn("NOT simply twice", insights)
        self.assertIn("1.926", insights)
        # Must NOT produce identical values
        self.assertNotIn("$60,801.00\n• Six Months Ended Figure (YTD): $60,801.00", insights)

    def test_validation_catches_identical_q2_ytd(self):
        """If Q2 and YTD have the same value, validation must flag it."""
        line_items = {
            "revenue": {
                "value": 60801.0,
                "by_period": {
                    "Q2_2026": 60801.0,
                    "YTD_2026": 60801.0,  # WRONG - should be 117111
                },
                "page": 5,
            }
        }
        result = validate_financial_data(line_items)
        self.assertFalse(result["valid"])
        self.assertTrue(any("identical Q2 and YTD" in w for w in result["warnings"]))


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

    def test_reconciliation_fallback(self):
        found = {
            "total_assets": {"value": 449956.0, "by_period": {}, "page": 6},
            "total_liabilities": {"value": 449956.0, "by_period": {}, "page": 6},
            "total_equity": {"value": 261221.0, "by_period": {}, "page": 6},
        }
        reconciled = validate_and_reconcile_balance_sheet(found)
        self.assertEqual(reconciled["total_liabilities"]["value"], 188735.0)


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


if __name__ == "__main__":
    unittest.main()
