#!/usr/bin/env python3
import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path


FIELDS = [
    "company_name",
    "report_year",
    "report_date",
    "revenue",
    "cost_of_sales",
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
]


PATTERNS = {
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
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def parse_number(value):
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("，", "")
    negative = text.startswith("-") or (text.startswith("(") and text.endswith(")")) or (text.startswith("（") and text.endswith("）"))
    text = text.strip("-()（）")
    try:
        number = float(text)
    except ValueError:
        return None
    return -number if negative else number


def normalize_json(data):
    result = {field: None for field in FIELDS}
    aliases = {
        "operating_cash_flow": ["cfo", "net_cash_flow_from_operating_activities"],
        "investing_cash_flow": ["cfi", "net_cash_flow_from_investing_activities"],
        "financing_cash_flow": ["cff", "net_cash_flow_from_financing_activities"],
        "equity": ["shareholders_equity", "net_assets"],
        "cash": ["monetary_funds"],
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
    for key in list(result.keys()):
        if key not in {"company_name", "report_year", "report_date"} and result[key] is not None:
            result[key] = parse_number(result[key])
    return result


def extract_basic(text):
    result = {field: None for field in FIELDS}
    company_patterns = [
        r"公司名称[：:\s]*([\u4e00-\u9fa5A-Za-z0-9（）()]{2,}(?:股份有限公司|有限责任公司|有限公司|集团|公司))",
        r"([\u4e00-\u9fa5A-Za-z0-9（）()]{2,}(?:股份有限公司|有限责任公司|有限公司))\s*\d{4}\s*年",
    ]
    for pattern in company_patterns:
        match = re.search(pattern, text[:5000])
        if match:
            result["company_name"] = match.group(1).strip()
            break
    for pattern in [r"(\d{4})\s*年\s*(?:年度|半年度|第[一二三四]季度)?\s*报告", r"(\d{4})\s*年度"]:
        match = re.search(pattern, text[:5000])
        if match:
            result["report_year"] = match.group(1)
            break
    for pattern in [r"报告期[末：:\s]*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)", r"(\d{4}年\d{1,2}月\d{1,2}日)", r"(\d{4}-\d{2}-\d{2})"]:
        match = re.search(pattern, text[:8000])
        if match:
            result["report_date"] = match.group(1)
            break
    return result


def extract_from_text(text):
    result = extract_basic(text)
    for field, patterns in PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                result[field] = parse_number(match.group(1))
                if result[field] is not None:
                    break
    return result


def extract(path):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    content = read_content(path)
    data = normalize_json(content) if isinstance(content, dict) else extract_from_text(content)
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
    args = parser.parse_args()
    result = extract(args.input)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
