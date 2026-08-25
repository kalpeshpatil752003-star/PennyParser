import unittest

# 1. Test Number Parsing without regex dependencies
import re

def parse_number(raw: str):
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s in ("-", "—", "N/A", "n/a", "NA", "na", "nil", "null", "none", "..."):
        return None
    s = re.sub(r"\s*\*+$", "", s).strip()
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1].strip()
    elif s.startswith("-"):
        negative = True
        s = s[1:].strip()
    if s.endswith("%"):
        s = s[:-1].strip()
    s = s.replace("$", "").replace(",", "").strip()
    if not re.match(r"^\d+(\.\d+)?$", s):
        return None
    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return None

def calculate_ratios(items: dict) -> dict:
    def val(key):
        return items[key]["value"] if key in items else None
    revenue = val("revenue")
    cogs = val("cost_of_goods_sold")
    gross_profit = val("gross_profit") or (revenue - cogs if revenue and cogs else None)
    operating_income = val("operating_income")
    net_income = val("net_income")
    total_assets = val("total_assets")
    total_liabilities = val("total_liabilities")
    total_equity = val("total_equity")
    current_assets = val("current_assets")
    current_liabilities = val("current_liabilities")
    ratios = {}
    if revenue and gross_profit is not None:
        ratios["gross_margin_pct"] = round(gross_profit / revenue * 100, 2)
    if revenue and operating_income is not None:
        ratios["operating_margin_pct"] = round(operating_income / revenue * 100, 2)
    if revenue and net_income is not None:
        ratios["net_margin_pct"] = round(net_income / revenue * 100, 2)
    if total_equity and net_income is not None:
        ratios["roe_pct"] = round(net_income / total_equity * 100, 2)
    if total_assets and net_income is not None:
        ratios["roa_pct"] = round(net_income / total_assets * 100, 2)
    if total_equity and total_liabilities is not None:
        ratios["debt_to_equity"] = round(total_liabilities / total_equity, 2)
    if current_liabilities and current_assets is not None:
        ratios["current_ratio"] = round(current_assets / current_liabilities, 2)
    return ratios

class TestPurePythonLogic(unittest.TestCase):

    def test_parse_number_variations(self):
        self.assertEqual(parse_number("$1,234"), 1234.0)
        self.assertEqual(parse_number("(1,234)"), -1234.0)
        self.assertEqual(parse_number("1,234.50"), 1234.50)
        self.assertEqual(parse_number("12.5%"), 12.5)
        self.assertEqual(parse_number("1,234*"), 1234.0)
        self.assertIsNone(parse_number("-"))
        self.assertIsNone(parse_number("—"))
        self.assertIsNone(parse_number("N/A"))

    def test_ratio_calculations(self):
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
