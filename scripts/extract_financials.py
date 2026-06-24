#!/usr/bin/env python3
import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path


FIELDS = [
    "company_name",
    "ticker",
    "cik",
    "report_year",
    "report_date",
    "filing_type",
    "market_profile",
    "source_url",
    "revenue",
    "cost_of_sales",
    "gross_profit",
    "operating_income",
    "net_profit",
    "non_recurring_net_profit",
    "total_assets",
    "total_liabilities",
    "equity",
    "cash",
    "accounts_receivable",
    "inventory",
    "interest_bearing_debt",
    "current_assets",
    "current_liabilities",
    "operating_cash_flow",
    "investing_cash_flow",
    "financing_cash_flow",
    "capex",
    "goodwill",
    "intangibles",
    "stock_based_compensation",
]


CN_PATTERNS = {
    "revenue": [r"营业收入[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)", r"营业总收入[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)"],
    "cost_of_sales": [r"营业成本[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)", r"营业总成本[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)"],
    "net_profit": [r"归属于上市公司股东的净利润[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)", r"净利润[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)"],
    "non_recurring_net_profit": [r"扣除非经常性损益[^\d\-（(]*?净利润[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)", r"扣非净利润[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)"],
    "total_assets": [r"资产总计[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)", r"总资产[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)"],
    "total_liabilities": [r"负债合计[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)", r"总负债[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)"],
    "equity": [r"归属于上市公司股东的净资产[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)", r"所有者权益合计[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)", r"股东权益合计[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)"],
    "cash": [r"货币资金[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)"],
    "accounts_receivable": [r"应收账款[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)"],
    "inventory": [r"存货[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)"],
    "interest_bearing_debt": [r"有息负债[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)", r"短期借款[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)"],
    "current_assets": [r"流动资产合计[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)"],
    "current_liabilities": [r"流动负债合计[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)"],
    "operating_cash_flow": [r"经营活动产生的现金流量净额[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)"],
    "investing_cash_flow": [r"投资活动产生的现金流量净额[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)"],
    "financing_cash_flow": [r"筹资活动产生的现金流量净额[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)"],
    "capex": [r"购建固定资产、无形资产和其他长期资产支付的现金[^\d\-（(]*?([\-]?\d[\d,，]*\.?\d*)"],
}


US_PATTERNS = {
    "revenue": [r"(?:Total\s+)?(?:Net\s+sales|Revenue|Revenues|Sales)[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "cost_of_sales": [r"(?:Cost\s+of\s+revenue|Cost\s+of\s+sales|Cost\s+of\s+goods\s+sold)[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "gross_profit": [r"Gross\s+profit[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "operating_income": [r"(?:Operating\s+income|Income\s+from\s+operations)[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "net_profit": [r"(?:Net\s+income|Net\s+earnings)[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "total_assets": [r"Total\s+assets[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "total_liabilities": [r"Total\s+liabilities[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "equity": [r"(?:Total\s+)?(?:stockholders'|shareholders')\s+equity[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "cash": [r"Cash\s+and\s+cash\s+equivalents[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "accounts_receivable": [r"Accounts\s+receivable[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "inventory": [r"Inventor(?:y|ies)[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "interest_bearing_debt": [r"(?:Total\s+debt|Long-term\s+debt|Short-term\s+borrowings)[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "current_assets": [r"Total\s+current\s+assets[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "current_liabilities": [r"Total\s+current\s+liabilities[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "operating_cash_flow": [r"(?:Net\s+cash\s+provided\s+by\s+operating\s+activities|Operating\s+cash\s+flow)[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "investing_cash_flow": [r"Net\s+cash\s+(?:provided\s+by|used\s+in)\s+investing\s+activities[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "financing_cash_flow": [r"Net\s+cash\s+(?:provided\s+by|used\s+in)\s+financing\s+activities[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "capex": [r"(?:Capital\s+expenditures|Payments\s+for\s+property,\s+plant\s+and\s+equipment|Purchases\s+of\s+property\s+and\s+equipment)[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "goodwill": [r"Goodwill[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "intangibles": [r"(?:Intangible\s+assets|Acquired\s+intangible\s+assets)[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
    "stock_based_compensation": [r"Stock[-\s]based\s+compensation[^\d\-\(]{0,80}(\(?-?\$?\d[\d,]*\.?\d*\)?)"],
}


def read_content(path):
    suffix = Path(path).suffix.lower()
    if suffix == ".json":
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    if suffix == ".pdf":
        try:
            import pdfplumber
        except ImportError as exc:
            raise RuntimeError("PDF extraction requires pdfplumber: pip install pdfplumber") from exc
        parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if text:
                    parts.append(text)
        return "\n".join(parts)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def strip_tags(text):
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def parse_number(value):
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("，", "").replace("$", "")
    negative = text.startswith("-") or (text.startswith("(") and text.endswith(")")) or (text.startswith("（") and text.endswith("）"))
    text = text.strip("-()（）")
    try:
        number = float(text)
    except ValueError:
        return None
    return -number if negative else number


def detect_profile(text, requested):
    if requested in {"cn", "us"}:
        return requested
    sample = text[:50000]
    cn_hits = sum(sample.count(term) for term in ["营业收入", "资产总计", "经营活动产生的现金流量净额", "扣非净利润"])
    us_hits = sum(1 for term in ["FORM 10-K", "FORM 10-Q", "UNITED STATES SECURITIES", "Item 7.", "Net income", "Total assets"] if term.lower() in sample.lower())
    return "cn" if cn_hits >= us_hits else "us"


def normalize_json(data, profile):
    result = {field: None for field in FIELDS}
    aliases = {
        "operating_cash_flow": ["cfo", "net_cash_flow_from_operating_activities", "net_cash_provided_by_operating_activities"],
        "investing_cash_flow": ["cfi", "net_cash_flow_from_investing_activities"],
        "financing_cash_flow": ["cff", "net_cash_flow_from_financing_activities"],
        "equity": ["shareholders_equity", "stockholders_equity", "net_assets"],
        "cash": ["monetary_funds", "cash_and_cash_equivalents"],
        "net_profit": ["net_income", "net_earnings"],
        "cost_of_sales": ["cost_of_revenue", "cost_of_sales"],
        "interest_bearing_debt": ["total_debt", "debt"],
    }
    for field in FIELDS:
        candidates = [field] + aliases.get(field, [])
        for key in candidates:
            if key in data and data[key] is not None:
                result[field] = data[key]
                break
    for key, value in data.items():
        if key.startswith("prev_"):
            result[key] = value
    result["market_profile"] = data.get("market_profile") or profile
    for key in list(result.keys()):
        if key not in {"company_name", "ticker", "cik", "report_year", "report_date", "filing_type", "market_profile", "source_url"} and result[key] is not None:
            result[key] = parse_number(result[key])
    return result


def extract_basic(text, profile):
    result = {field: None for field in FIELDS}
    result["market_profile"] = profile
    if profile == "cn":
        company_patterns = [
            r"公司名称[：:\s]*([\u4e00-\u9fa5A-Za-z0-9（）()]{2,}(?:股份有限公司|有限责任公司|有限公司|集团|公司))",
            r"([\u4e00-\u9fa5A-Za-z0-9（）()]{2,}(?:股份有限公司|有限责任公司|有限公司))\s*\d{4}\s*年",
        ]
        year_patterns = [r"(\d{4})\s*年\s*(?:年度|半年度|第[一二三四]季度)?\s*报告", r"(\d{4})\s*年度"]
        date_patterns = [r"报告期[末：:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)", r"(\d{4}年\d{1,2}月\d{1,2}日)", r"(\d{4}-\d{2}-\d{2})"]
    else:
        company_patterns = [
            r"COMPANY\s+CONFORMED\s+NAME:\s*([A-Za-z0-9&., '\-]+?)(?:\s+CENTRAL\s+INDEX\s+KEY|\s+FORM\s+10-[KQ]|\s+For\s+the\s+fiscal|\s+Item\s+\d|$)",
            r"Exact\s+name\s+of\s+registrant[^\n\r]*\s+([A-Z][A-Za-z0-9&., '\-]+)",
        ]
        year_patterns = [r"for\s+the\s+fiscal\s+year\s+ended\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", r"(\d{4})\s+FORM\s+10-[KQ]"]
        date_patterns = [r"FILED\s+AS\s+OF\s+DATE:\s*(\d{8})", r"for\s+the\s+fiscal\s+year\s+ended\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})"]
        filing_match = re.search(r"FORM\s+(10-K|10-Q|8-K|DEF\s+14A|4|13F|SC\s+13D|SC\s+13G)", text, flags=re.I)
        if filing_match:
            result["filing_type"] = filing_match.group(1).upper()
        cik_match = re.search(r"CENTRAL\s+INDEX\s+KEY:\s*(\d+)", text, flags=re.I)
        if cik_match:
            result["cik"] = cik_match.group(1).lstrip("0") or cik_match.group(1)

    for pattern in company_patterns:
        match = re.search(pattern, text[:30000], flags=re.I)
        if match:
            result["company_name"] = match.group(1).strip()
            break
    for pattern in year_patterns:
        match = re.search(pattern, text[:30000], flags=re.I)
        if match:
            result["report_year"] = match.group(1).strip()
            break
    for pattern in date_patterns:
        match = re.search(pattern, text[:30000], flags=re.I)
        if match:
            result["report_date"] = match.group(1).strip()
            break
    return result


def extract_with_patterns(text, patterns):
    result = {}
    for field, regexes in patterns.items():
        for regex in regexes:
            match = re.search(regex, text, flags=re.I | re.S)
            if match:
                result[field] = parse_number(match.group(1))
                if result[field] is not None:
                    break
    return result


def extract_from_text(text, requested_profile):
    clean = strip_tags(text)
    profile = detect_profile(clean, requested_profile)
    result = extract_basic(clean, profile)
    result.update(extract_with_patterns(clean, CN_PATTERNS if profile == "cn" else US_PATTERNS))
    if result.get("gross_profit") is None and result.get("revenue") is not None and result.get("cost_of_sales") is not None:
        result["gross_profit"] = result["revenue"] - result["cost_of_sales"]
    return result


def extract(path, profile="auto"):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    content = read_content(path)
    if isinstance(content, dict):
        detected = content.get("market_profile") or profile
        data = normalize_json(content, detected if detected in {"cn", "us"} else "us")
    else:
        data = extract_from_text(content, profile)
    missing = [field for field in FIELDS if data.get(field) is None]
    data["_meta"] = {
        "source_file": os.path.basename(path),
        "extracted_at": datetime.now().isoformat(timespec="seconds"),
        "missing_fields": missing,
        "extracted_fields": [field for field in FIELDS if data.get(field) is not None],
    }
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    parser.add_argument("--profile", choices=["auto", "cn", "us"], default="auto")
    args = parser.parse_args()
    result = extract(args.input, args.profile)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
