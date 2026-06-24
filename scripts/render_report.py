#!/usr/bin/env python3
import argparse
import html
import json
import os
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_DIR = SKILL_DIR / "templates"


def run_json(cmd):
    completed = subprocess.run(cmd, text=True, capture_output=True)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{detail}")
    return json.loads(completed.stdout)


def fmt_amount(value):
    if value is None:
        return "N/A"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if abs(value) >= 1e9:
        return f"{value / 1e9:.2f}B"
    if abs(value) >= 1e8:
        return f"{value / 1e8:.2f}亿元"
    if abs(value) >= 1e6:
        return f"{value / 1e6:.2f}M"
    if abs(value) >= 1e4:
        return f"{value / 1e4:.2f}万元"
    return f"{value:.2f}"


def fmt_pct(value):
    if value is None:
        return "N/A"
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "N/A"


def fmt_num(value):
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "N/A"


def missing_text(data):
    missing = data.get("_meta", {}).get("missing_fields", [])
    return "None" if not missing else ", ".join(missing)


def table_rows(data, ratios):
    rows = [
        ("Revenue / 营业收入", fmt_amount(data.get("revenue")), fmt_pct(ratios.get("revenue_growth"))),
        ("Cost of sales / 营业成本", fmt_amount(data.get("cost_of_sales")), "N/A"),
        ("Net income / 净利润", fmt_amount(data.get("net_profit")), fmt_pct(ratios.get("net_profit_growth"))),
        ("Non-recurring net profit / 扣非净利润", fmt_amount(data.get("non_recurring_net_profit")), "N/A"),
        ("Total assets / 总资产", fmt_amount(data.get("total_assets")), "N/A"),
        ("Total liabilities / 总负债", fmt_amount(data.get("total_liabilities")), "N/A"),
        ("Operating cash flow / 经营现金流", fmt_amount(data.get("operating_cash_flow")), fmt_pct(ratios.get("cfo_growth"))),
        ("Free cash flow / 自由现金流", fmt_amount(ratios.get("free_cash_flow")), "N/A"),
    ]
    return "\n".join(f"| {name} | {value} | {trend} |" for name, value, trend in rows)


def ratio_rows(ratios):
    rows = [
        ("Gross margin / 毛利率", fmt_pct(ratios.get("gross_margin"))),
        ("Net margin / 净利率", fmt_pct(ratios.get("net_margin"))),
        ("ROE", fmt_pct(ratios.get("roe"))),
        ("Debt/assets / 资产负债率", fmt_pct(ratios.get("debt_to_asset_ratio"))),
        ("Current ratio / 流动比率", fmt_num(ratios.get("current_ratio"))),
        ("Quick ratio / 速动比率", fmt_num(ratios.get("quick_ratio"))),
        ("CFO/net income / 净现比", fmt_num(ratios.get("cfo_to_net_profit"))),
        ("Accrual ratio / 应计利润率", fmt_pct(ratios.get("accrual_ratio"))),
        ("FCF conversion", fmt_pct(ratios.get("fcf_conversion"))),
        ("CapEx intensity", fmt_pct(ratios.get("capex_intensity"))),
        ("Net cash/debt", fmt_amount(ratios.get("net_cash_or_debt"))),
    ]
    return "\n".join(f"| {name} | {value} |" for name, value in rows)


def quality_rows(analysis):
    items = analysis.get("earnings_quality", {}).get("items", [])
    rows = []
    for item in items:
        score = "missing" if item.get("score") is None else f"{item.get('score')}/3"
        rows.append(f"| {item.get('name')} | {score} | {item.get('label')} | {item.get('reason')} |")
    return "\n".join(rows)


def red_flag_lines(analysis):
    lines = []
    for check in analysis.get("red_flags", {}).get("checks", []):
        mark = "[!]" if check.get("triggered") else "[x]"
        lines.append(f"- {mark} {check.get('name')} ({check.get('severity')}): {check.get('evidence')}")
    return "\n".join(lines)


def linkage_lines(analysis):
    return "\n".join(f"- {item.get('name')}: {item.get('status')}, {item.get('detail')}" for item in analysis.get("linkage_checks", []))


def sec_dimension_rows(sec_analysis):
    dimensions = sec_analysis.get("dimensions", {}) if sec_analysis else {}
    if not dimensions:
        return "| N/A | N/A | No SEC filing analysis available |"
    rows = []
    for name, item in dimensions.items():
        rows.append(f"| {name} | {item.get('score')} | {item.get('basis')} |")
    return "\n".join(rows)


def sec_summary_text(sec_analysis):
    if not sec_analysis:
        return "No SEC filing analysis was generated."
    summary = sec_analysis.get("filing_summary", {})
    signal = sec_analysis.get("composite_filing_signal", {})
    return (
        f"Filing type: {summary.get('filing_type', 'unknown')}; "
        f"filing date: {summary.get('filing_date', 'N/A')}; "
        f"composite signal: {signal.get('label', 'N/A')} ({signal.get('total_score', 'N/A')})."
    )


def render_markdown(data, ratios, analysis, charts, sec_analysis=None):
    template = (TEMPLATE_DIR / "report_template.md").read_text(encoding="utf-8")
    quality = analysis.get("earnings_quality", {})
    red_flags = analysis.get("red_flags", {})
    cash_matrix = analysis.get("cash_flow_matrix", {})
    dupont = analysis.get("dupont", {})
    profile = data.get("market_profile") or "auto"
    replacements = {
        "COMPANY_NAME": data.get("company_name") or data.get("ticker") or "Unknown Company",
        "REPORT_YEAR": str(data.get("report_year") or "N/A"),
        "REPORT_DATE": str(data.get("report_date") or "N/A"),
        "PROFILE": profile,
        "SUMMARY": f"Earnings quality: {quality.get('label', 'unknown')}; red-flag risk: {red_flags.get('risk_level', 'unknown')}; cash-flow state: {cash_matrix.get('state', 'unknown')}.",
        "STATEMENT_TABLE_ROWS": table_rows(data, ratios),
        "RATIO_TABLE_ROWS": ratio_rows(ratios),
        "QUALITY_SCORE": "N/A" if quality.get("score") is None else f"{quality.get('score'):.2f}/3",
        "QUALITY_LABEL": quality.get("label", "unknown"),
        "QUALITY_TABLE_ROWS": quality_rows(analysis),
        "DUPONT_TEXT": f"ROE={fmt_pct(dupont.get('roe'))}, net margin={fmt_pct(dupont.get('net_margin'))}, asset turnover={fmt_num(dupont.get('asset_turnover'))}, equity multiplier={fmt_num(dupont.get('equity_multiplier'))}.",
        "CASH_FLOW_TEXT": f"{cash_matrix.get('state', 'unknown')}: {cash_matrix.get('reason', 'cash-flow fields are incomplete')}",
        "LINKAGE_LINES": linkage_lines(analysis),
        "RED_FLAG_LEVEL": red_flags.get("risk_level", "unknown"),
        "RED_FLAG_LINES": red_flag_lines(analysis),
        "SEC_SUMMARY": sec_summary_text(sec_analysis),
        "SEC_DIMENSION_ROWS": sec_dimension_rows(sec_analysis),
        "MISSING_FIELDS": missing_text(data),
        "CHARTS": "\n".join(f"![{name}]({path})" for name, path in charts.items()) if charts else "No charts generated.",
    }
    for key, value in replacements.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def markdown_to_html(markdown_text, title):
    try:
        import markdown

        body = markdown.markdown(markdown_text, extensions=["tables"])
    except Exception:
        body = "<pre>" + html.escape(markdown_text) + "</pre>"
    template = (TEMPLATE_DIR / "report_template.html").read_text(encoding="utf-8")
    return template.replace("{{TITLE}}", html.escape(title)).replace("{{BODY}}", body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input")
    parser.add_argument("--ticker")
    parser.add_argument("--cik")
    parser.add_argument("--filing-type", default="10-K")
    parser.add_argument("--fetch-sec", action="store_true")
    parser.add_argument("--user-agent")
    parser.add_argument("--profile", choices=["auto", "cn", "us"], default="auto")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--format", choices=["md", "html", "both"], default="both")
    parser.add_argument("--skip-charts", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    data_path = output_dir / "financial_data.json"
    ratios_path = output_dir / "ratios.json"
    analysis_path = output_dir / "quality_analysis.json"
    charts_path = output_dir / "charts.json"
    sec_analysis_path = output_dir / "sec_filing_analysis.json"
    composite_path = output_dir / "composite_signal.json"

    input_path = args.input
    sec_metadata_path = None
    if args.fetch_sec:
        if not args.user_agent and not os.environ.get("EDGAR_USER_AGENT"):
            raise SystemExit("SEC fetch requires --user-agent or EDGAR_USER_AGENT. Example: EDGAR_USER_AGENT='Your Name your.email@example.com'")
        metadata = run_json([
            sys.executable,
            str(SCRIPT_DIR / "fetch_sec_filings.py"),
            *(["--ticker", args.ticker] if args.ticker else []),
            *(["--cik", args.cik] if args.cik else []),
            "--filing-type",
            args.filing_type,
            "--output-dir",
            str(output_dir),
            *(["--user-agent", args.user_agent] if args.user_agent else []),
        ])
        input_path = metadata["local_filing"]
        sec_metadata_path = output_dir / "sec_metadata.json"
    if not input_path:
        raise SystemExit("Provide --input for local analysis or --fetch-sec with --ticker/--cik for SEC retrieval")

    effective_profile = "us" if args.fetch_sec else args.profile
    data = run_json([sys.executable, str(SCRIPT_DIR / "extract_financials.py"), "--input", input_path, "--profile", effective_profile, "--output", str(data_path)])
    if sec_metadata_path and sec_metadata_path.exists():
        metadata = json.loads(sec_metadata_path.read_text(encoding="utf-8"))
        data.update({k: v for k, v in metadata.items() if k in {"ticker", "cik", "company_name", "filing_type", "source_url", "report_date"}})
        data["market_profile"] = "us"
        data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ratios = run_json([sys.executable, str(SCRIPT_DIR / "calculate_ratios.py"), "--input", str(data_path), "--output", str(ratios_path)])
    analysis = run_json([sys.executable, str(SCRIPT_DIR / "analyze_quality.py"), "--data", str(data_path), "--ratios", str(ratios_path), "--output", str(analysis_path)])

    sec_analysis = None
    if data.get("market_profile") == "us" or str(data.get("filing_type") or "").upper() in {"10-K", "10-Q", "8-K", "DEF 14A", "4", "13F", "SC 13D", "SC 13G"}:
        sec_args = [sys.executable, str(SCRIPT_DIR / "analyze_sec_filings.py"), "--filing", input_path, "--data", str(data_path), "--ratios", str(ratios_path), "--output", str(sec_analysis_path)]
        if sec_metadata_path and sec_metadata_path.exists():
            sec_args.extend(["--metadata", str(sec_metadata_path)])
        sec_analysis = run_json(sec_args)
        composite_path.write_text(json.dumps(sec_analysis.get("composite_filing_signal", {}), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    charts = {}
    if not args.skip_charts:
        try:
            charts = run_json([sys.executable, str(SCRIPT_DIR / "generate_charts.py"), "--data", str(data_path), "--ratios", str(ratios_path), "--output-dir", str(output_dir / "charts"), "--output", str(charts_path)])
        except Exception as exc:
            charts = {"chart_generation_error": str(exc)}
            charts_path.write_text(json.dumps(charts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    title = f"{data.get('company_name') or data.get('ticker') or 'Unknown Company'} Financial Report & Disclosure Risk Analysis"
    markdown_text = render_markdown(data, ratios, analysis, charts, sec_analysis)
    if args.format in {"md", "both"}:
        (output_dir / "report.md").write_text(markdown_text + "\n", encoding="utf-8")
    if args.format in {"html", "both"}:
        (output_dir / "report.html").write_text(markdown_to_html(markdown_text, title), encoding="utf-8")

    manifest = {
        "financial_data": str(data_path),
        "ratios": str(ratios_path),
        "quality_analysis": str(analysis_path),
        "charts": str(charts_path),
        "sec_metadata": str(output_dir / "sec_metadata.json") if (output_dir / "sec_metadata.json").exists() else None,
        "sec_filing_analysis": str(sec_analysis_path) if sec_analysis else None,
        "composite_signal": str(composite_path) if sec_analysis else None,
        "report_md": str(output_dir / "report.md") if args.format in {"md", "both"} else None,
        "report_html": str(output_dir / "report.html") if args.format in {"html", "both"} else None,
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
