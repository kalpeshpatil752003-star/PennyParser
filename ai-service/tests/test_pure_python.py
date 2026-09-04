import unittest

from app.services.normalize import parse_number, is_footnote_marker
from app.services.ratios import calculate_ratios
from app.services.financial_extraction import detect_scale, score_table
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
        self.assertIn("eps", items)
        self.assertEqual(items["eps"]["value"], 7.17)
        self.assertNotEqual(items["eps"]["value"], 2548.0)

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


if __name__ == "__main__":
    unittest.main()

