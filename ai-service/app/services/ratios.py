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