#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def val(data, key):
    value = data.get(key)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt_pct(value):
    return "N/A" if value is None else f"{value * 100:.1f}%"


def score_item(value, good, fair, higher_is_better=True):
    if value is None:
        return {"score": None, "label": "缺失", "reason": "缺少可计算字段"}
    if higher_is_better:
        if value >= good:
            return {"score": 3, "label": "优秀", "reason": f"{fmt_pct(value)} 达到优秀阈值"}
        if value >= fair:
            return {"score": 2, "label": "一般", "reason": f"{fmt_pct(value)} 处于关注区间"}
        return {"score": 1, "label": "较差", "reason": f"{fmt_pct(value)} 低于关注阈值"}
    if value <= good:
        return {"score": 3, "label": "优秀", "reason": f"{fmt_pct(value)} 低于风险阈值"}
    if value <= fair:
        return {"score": 2, "label": "一般", "reason": f"{fmt_pct(value)} 处于关注区间"}
    return {"score": 1, "label": "较差", "reason": f"{fmt_pct(value)} 高于风险阈值"}


def weighted_score(items):
    total_weight = 0
    total_score = 0
    for item in items:
        if item["score"] is None:
            continue
        total_weight += item["weight"]
        total_score += item["score"] * item["weight"]
    if not total_weight:
        return None
    return total_score / total_weight


def cash_flow_matrix(cfo, cfi, cff):
    if cfo is None or cfi is None or cff is None:
        return {"state": "无法判断", "reason": "现金流三项不完整"}
    signs = ("+" if cfo >= 0 else "-", "+" if cfi >= 0 else "-", "+" if cff >= 0 else "-")
    mapping = {
        ("+", "-", "-"): ("优秀", "赚钱、投资、还债或分红"),
        ("+", "-", "+"): ("扩张", "经营造血为正，同时融资支持扩张"),
        ("+", "+", "-"): ("稳健", "经营现金流为正，并回收投资或压缩资产"),
        ("-", "-", "+"): ("危险", "经营失血，投资仍扩张，依赖融资"),
        ("-", "+", "+"): ("困境", "卖资产并融资维持现金"),
        ("-", "+", "-"): ("衰退", "卖资产还债，经营现金流为负"),
    }
    state, reason = mapping.get(signs, ("混合", "现金流组合需要结合业务背景判断"))
    return {"state": state, "signs": "".join(signs), "reason": reason}


def red_flags(data, ratios):
    revenue = val(data, "revenue")
    cash = val(data, "cash")
    debt = val(data, "interest_bearing_debt")
    net_profit = val(data, "net_profit")
    cfo = val(data, "operating_cash_flow")
    receivables_growth = ratios.get("receivables_growth")
    revenue_growth = ratios.get("revenue_growth")
    inventory_to_revenue = ratios.get("inventory_to_revenue")
    accrual_ratio = ratios.get("accrual_ratio")
    non_recurring_ratio = ratios.get("non_recurring_profit_ratio")
    debt_to_assets = ratios.get("interest_bearing_debt_to_assets")
    fcf_conversion = ratios.get("fcf_conversion")
    net_cash_or_debt = ratios.get("net_cash_or_debt")
    goodwill_intangibles_to_assets = ratios.get("goodwill_intangibles_to_assets")
    sbc_to_revenue = ratios.get("sbc_to_revenue")

    checks = []

    def add(name, triggered, severity, evidence):
        checks.append({"name": name, "triggered": bool(triggered), "severity": severity, "evidence": evidence})

    add(
        "存贷双高",
        revenue and cash and debt and cash > revenue * 0.3 and debt > revenue * 0.3,
        "高",
        f"货币资金/营收={fmt_pct(None if not revenue or cash is None else cash / revenue)}, 有息负债/营收={fmt_pct(None if not revenue or debt is None else debt / revenue)}",
    )
    add(
        "应收增速显著高于营收",
        receivables_growth is not None and revenue_growth is not None and receivables_growth > max(revenue_growth * 1.5, revenue_growth + 0.1),
        "高",
        f"应收增速={fmt_pct(receivables_growth)}, 营收增速={fmt_pct(revenue_growth)}",
    )
    add("存货占营收偏高", inventory_to_revenue is not None and inventory_to_revenue > 0.5, "高", f"存货/营收={fmt_pct(inventory_to_revenue)}")
    add("利润为正但经营现金流为负", net_profit is not None and cfo is not None and net_profit > 0 and cfo < 0, "高", f"净利润={net_profit}, CFO={cfo}")
    add("应计利润占比高", accrual_ratio is not None and accrual_ratio > 0.1, "中", f"应计利润率={fmt_pct(accrual_ratio)}")
    add("扣非贡献偏低", non_recurring_ratio is not None and non_recurring_ratio < 0.7, "中", f"扣非/净利润={fmt_pct(non_recurring_ratio)}")
    add("有息负债率偏高", debt_to_assets is not None and debt_to_assets > 0.3, "中", f"有息负债/总资产={fmt_pct(debt_to_assets)}")
    if data.get("market_profile") == "us":
        add("FCF conversion 偏弱", fcf_conversion is not None and fcf_conversion < 0.3, "高", f"FCF/净利润={fmt_pct(fcf_conversion)}")
        add("净债务状态", net_cash_or_debt is not None and net_cash_or_debt < 0, "中", f"净现金/净债务={net_cash_or_debt}")
        add("商誉和无形资产占比高", goodwill_intangibles_to_assets is not None and goodwill_intangibles_to_assets > 0.3, "中", f"商誉+无形资产/总资产={fmt_pct(goodwill_intangibles_to_assets)}")
        add("SBC 占收入偏高", sbc_to_revenue is not None and sbc_to_revenue > 0.1, "中", f"SBC/收入={fmt_pct(sbc_to_revenue)}")

    triggered = [check for check in checks if check["triggered"]]
    count = len(triggered)
    if count <= 1:
        level = "低"
    elif count <= 3:
        level = "中"
    elif count <= 5:
        level = "高"
    else:
        level = "极高"
    return {"risk_level": level, "triggered_count": count, "checks": checks}


def linkage_checks(data):
    checks = []
    assets = val(data, "total_assets")
    liabilities = val(data, "total_liabilities")
    equity = val(data, "equity")
    if assets is None or liabilities is None or equity is None:
        checks.append({"name": "资产=负债+权益", "status": "缺失", "detail": "资产、负债或权益字段不完整"})
    else:
        diff = abs(assets - liabilities - equity)
        tolerance = max(abs(assets) * 0.02, 1)
        checks.append({"name": "资产=负债+权益", "status": "通过" if diff <= tolerance else "异常", "detail": f"差额={diff:.2f}, 容忍={tolerance:.2f}"})
    return checks


def analyze(data, ratios):
    cfo_to_profit = ratios.get("cfo_to_net_profit")
    accrual = ratios.get("accrual_ratio")
    receivables_growth = ratios.get("receivables_growth")
    revenue_growth = ratios.get("revenue_growth")
    non_recurring = ratios.get("non_recurring_profit_ratio")
    cfo_growth = ratios.get("cfo_growth")
    inventory_growth = ratios.get("inventory_growth")
    fcf_conversion = ratios.get("fcf_conversion")

    receivable_gap = None if receivables_growth is None or revenue_growth is None else receivables_growth - revenue_growth
    items = [
        {"name": "CFO/净利润", "weight": 0.25, **score_item(cfo_to_profit, 1.2, 0.8)},
        {"name": "应收增速 vs 营收", "weight": 0.20, **score_item(receivable_gap, 0.0, 0.1, higher_is_better=False)},
        {"name": "扣非/净利润", "weight": 0.20, **score_item(non_recurring, 0.9, 0.7)},
        {"name": "经营现金流趋势", "weight": 0.20, **score_item(cfo_growth, 0.0, -0.1)},
        {"name": "存货增长压力", "weight": 0.15, **score_item(inventory_growth, 0.0, 0.2, higher_is_better=False)},
    ]
    if data.get("market_profile") == "us":
        items.append({"name": "FCF/净利润", "weight": 0.25, **score_item(fcf_conversion, 0.8, 0.3)})
    score = weighted_score(items)
    if score is None:
        label = "无法评分"
    elif score >= 2.5:
        label = "盈利质量优秀"
    elif score >= 1.5:
        label = "需要关注"
    else:
        label = "盈利质量差"

    result = {
        "earnings_quality": {"score": score, "label": label, "items": items},
        "cash_flow_matrix": cash_flow_matrix(val(data, "operating_cash_flow"), val(data, "investing_cash_flow"), val(data, "financing_cash_flow")),
        "dupont": {
            "roe": ratios.get("roe"),
            "net_margin": ratios.get("net_margin"),
            "asset_turnover": ratios.get("asset_turnover"),
            "equity_multiplier": ratios.get("equity_multiplier"),
            "judgment": "ROE 由净利率、资产周转率和权益乘数共同驱动；缺失项需谨慎解读。",
        },
        "linkage_checks": linkage_checks(data),
        "red_flags": red_flags(data, ratios),
    }
    result["_meta"] = {"missing_fields": data.get("_meta", {}).get("missing_fields", [])}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--ratios", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    ratios = json.loads(Path(args.ratios).read_text(encoding="utf-8"))
    result = analyze(data, ratios)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
