#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def num(data, key):
    value = data.get(key)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def div(a, b):
    if a is None or b in (None, 0):
        return None
    return a / b


def ratio_change(data, key):
    current = num(data, key)
    previous = num(data, f"prev_{key}")
    if current is None or previous in (None, 0):
        return None
    return (current - previous) / abs(previous)


def calculate(data):
    revenue = num(data, "revenue")
    cost = num(data, "cost_of_sales")
    net_profit = num(data, "net_profit")
    non_recurring = num(data, "non_recurring_net_profit")
    total_assets = num(data, "total_assets")
    total_liabilities = num(data, "total_liabilities")
    equity = num(data, "equity")
    cash = num(data, "cash")
    receivables = num(data, "accounts_receivable")
    inventory = num(data, "inventory")
    debt = num(data, "interest_bearing_debt")
    current_assets = num(data, "current_assets")
    current_liabilities = num(data, "current_liabilities")
    cfo = num(data, "operating_cash_flow")

    gross_profit = None if revenue is None or cost is None else revenue - cost
    average_assets = total_assets
    average_equity = equity

    ratios = {
        "gross_margin": div(gross_profit, revenue),
        "net_margin": div(net_profit, revenue),
        "roe": div(net_profit, average_equity),
        "debt_to_asset_ratio": div(total_liabilities, total_assets),
        "current_ratio": div(current_assets, current_liabilities),
        "quick_ratio": div(None if current_assets is None or inventory is None else current_assets - inventory, current_liabilities),
        "cfo_to_net_profit": div(cfo, net_profit),
        "accrual_ratio": div(None if net_profit is None or cfo is None else net_profit - cfo, total_assets),
        "asset_turnover": div(revenue, average_assets),
        "equity_multiplier": div(total_assets, equity),
        "non_recurring_profit_ratio": div(non_recurring, net_profit),
        "receivables_to_revenue": div(receivables, revenue),
        "inventory_to_revenue": div(inventory, revenue),
        "cash_to_revenue": div(cash, revenue),
        "interest_bearing_debt_to_assets": div(debt, total_assets),
        "revenue_growth": ratio_change(data, "revenue"),
        "net_profit_growth": ratio_change(data, "net_profit"),
        "receivables_growth": ratio_change(data, "accounts_receivable"),
        "inventory_growth": ratio_change(data, "inventory"),
        "cfo_growth": ratio_change(data, "operating_cash_flow"),
    }
    ratios["dupont"] = {
        "roe": ratios["roe"],
        "net_margin": ratios["net_margin"],
        "asset_turnover": ratios["asset_turnover"],
        "equity_multiplier": ratios["equity_multiplier"],
    }
    ratios["_meta"] = {"missing_ratio_keys": [key for key, value in ratios.items() if value is None]}
    return ratios


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = calculate(data)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
