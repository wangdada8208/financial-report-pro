#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


POSITIVE_WORDS = ["growth", "improvement", "strong", "exceeded", "momentum", "opportunity", "record", "expanded"]
NEGATIVE_WORDS = ["challenging", "decline", "uncertainty", "headwind", "pressure", "risk", "decrease", "impairment"]
CAUTIOUS_WORDS = ["moderate", "cautious", "prudent", "measured", "selective", "may", "could", "expect"]


def strip_tags(text):
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def read_text(path):
    return strip_tags(Path(path).read_text(encoding="utf-8", errors="ignore"))


def count_words(text, words):
    lower = text.lower()
    return sum(lower.count(word) for word in words)


def filing_summary(text, metadata):
    filing_type = metadata.get("filing_type")
    if not filing_type:
        match = re.search(r"FORM\s+(10-K|10-Q|8-K|DEF\s+14A|4|13F|SC\s+13D|SC\s+13G)", text, flags=re.I)
        filing_type = match.group(1).upper() if match else "unknown"
    items = sorted(set(re.findall(r"Item\s+(\d+\.\d+)", text, flags=re.I)))
    return {
        "company_name": metadata.get("company_name"),
        "ticker": metadata.get("ticker"),
        "cik": metadata.get("cik"),
        "filing_type": filing_type,
        "filing_date": metadata.get("filing_date"),
        "report_date": metadata.get("report_date"),
        "source_url": metadata.get("source_url"),
        "items_detected": items,
    }


def financial_health(ratios):
    score = 0
    basis = []
    revenue_growth = ratios.get("revenue_growth")
    gross_margin = ratios.get("gross_margin")
    fcf_conversion = ratios.get("fcf_conversion")
    net_cash = ratios.get("net_cash_or_debt")
    debt_ratio = ratios.get("debt_to_asset_ratio")
    if revenue_growth is not None:
        score += 1 if revenue_growth > 0.05 else -1 if revenue_growth < -0.05 else 0
        basis.append(f"revenue growth={revenue_growth:.1%}")
    if gross_margin is not None:
        score += 1 if gross_margin > 0.35 else -1 if gross_margin < 0.15 else 0
        basis.append(f"gross margin={gross_margin:.1%}")
    if fcf_conversion is not None:
        score += 1 if fcf_conversion > 0.8 else -1 if fcf_conversion < 0.3 else 0
        basis.append(f"FCF conversion={fcf_conversion:.1%}")
    if net_cash is not None:
        score += 1 if net_cash > 0 else -1
        basis.append(f"net cash/debt={net_cash:.0f}")
    elif debt_ratio is not None:
        score += 1 if debt_ratio < 0.4 else -1 if debt_ratio > 0.7 else 0
        basis.append(f"debt/assets={debt_ratio:.1%}")
    score = max(-2, min(2, score))
    return {"score": score, "basis": "; ".join(basis) if basis else "insufficient structured financial data"}


def tone_analysis(text):
    positive = count_words(text, POSITIVE_WORDS)
    negative = count_words(text, NEGATIVE_WORDS)
    cautious = count_words(text, CAUTIOUS_WORDS)
    raw = positive - negative - cautious * 0.25
    score = 2 if raw > 20 else 1 if raw > 5 else -2 if raw < -20 else -1 if raw < -5 else 0
    return {"score": score, "positive_words": positive, "negative_words": negative, "cautious_words": cautious, "basis": f"positive={positive}, negative={negative}, cautious={cautious}"}


def risk_factor_analysis(text):
    risk_section_present = bool(re.search(r"Item\s+1A\.?\s+Risk\s+Factors", text, flags=re.I))
    cybersecurity = bool(re.search(r"cybersecurity|cyber security|data breach", text, flags=re.I))
    restatement = bool(re.search(r"restatement|material weakness|internal control", text, flags=re.I))
    litigation = bool(re.search(r"litigation|regulatory investigation|antitrust|subpoena", text, flags=re.I))
    flags = []
    if cybersecurity:
        flags.append("cybersecurity/data breach risk language")
    if restatement:
        flags.append("restatement/material weakness/internal control language")
    if litigation:
        flags.append("litigation/regulatory risk language")
    score = -2 if restatement else -1 if flags else 0
    return {"score": score, "risk_section_present": risk_section_present, "flags": flags, "basis": "; ".join(flags) if flags else "no high-priority keyword risk flags detected"}


def event_catalyst(text, summary):
    filing_type = (summary.get("filing_type") or "").upper()
    items = set(summary.get("items_detected") or [])
    score = 0
    basis = []
    if filing_type == "8-K":
        if "4.02" in items or re.search(r"not\s+be\s+relied\s+upon|restatement", text, flags=re.I):
            score = -2
            basis.append("Item 4.02/restatement style language")
        elif "5.02" in items and re.search(r"chief\s+executive|chief\s+financial|CEO|CFO|resign|departure", text, flags=re.I):
            score = -1
            basis.append("C-suite departure/change language")
        elif "2.02" in items:
            basis.append("earnings release/pre-release event")
        elif "1.01" in items:
            basis.append("material agreement/M&A style event")
    return {"score": score, "basis": "; ".join(basis) if basis else "no high-priority event catalyst detected"}


def insider_activity(text, summary):
    filing_type = (summary.get("filing_type") or "").upper()
    if filing_type != "4":
        return {"score": 0, "basis": "not a Form 4 filing"}
    purchases = len(re.findall(r"\bPurchase\b|\bP\b", text, flags=re.I))
    sales = len(re.findall(r"\bSale\b|\bS\b", text, flags=re.I))
    score = 2 if purchases >= 3 and purchases > sales else -1 if sales > purchases * 2 else 0
    return {"score": score, "basis": f"purchase markers={purchases}, sale markers={sales}"}


def institutional_flow(text, summary):
    filing_type = (summary.get("filing_type") or "").upper()
    if filing_type not in {"13F", "SC 13D", "SC 13G"}:
        return {"score": 0, "basis": "not a 13F/13D/13G ownership filing"}
    activist = bool(re.search(r"purpose\s+of\s+transaction|plans\s+or\s+proposals|Item\s+4", text, flags=re.I))
    score = 1 if activist else 0
    return {"score": score, "basis": "activist/strategic ownership language detected" if activist else "ownership filing detected without activist keyword signal"}


def label(total):
    if total > 6:
        return "strong fundamental bullish"
    if total > 2:
        return "mild bullish"
    if total < -2:
        return "fundamental caution"
    return "neutral"


def analyze(filing_path, data=None, ratios=None, metadata=None):
    text = read_text(filing_path)
    metadata = metadata or {}
    ratios = ratios or {}
    summary = filing_summary(text, metadata)
    dimensions = {
        "financial_health": financial_health(ratios),
        "management_tone": tone_analysis(text),
        "risk_factor_change": risk_factor_analysis(text),
        "event_catalyst": event_catalyst(text, summary),
        "insider_activity": insider_activity(text, summary),
        "institutional_flow": institutional_flow(text, summary),
    }
    total = sum(item.get("score", 0) for item in dimensions.values())
    return {
        "filing_summary": summary,
        "dimensions": dimensions,
        "composite_filing_signal": {
            "total_score": total,
            "label": label(total),
            "scale": "-12 to +12",
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--filing", required=True)
    parser.add_argument("--data")
    parser.add_argument("--ratios")
    parser.add_argument("--metadata")
    parser.add_argument("--output")
    args = parser.parse_args()
    data = json.loads(Path(args.data).read_text(encoding="utf-8")) if args.data else {}
    ratios = json.loads(Path(args.ratios).read_text(encoding="utf-8")) if args.ratios else {}
    metadata = json.loads(Path(args.metadata).read_text(encoding="utf-8")) if args.metadata else {}
    result = analyze(args.filing, data, ratios, metadata)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
