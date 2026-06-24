#!/usr/bin/env python3
import argparse
import html
import json
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_DIR = SKILL_DIR / "templates"


def run_json(cmd):
    completed = subprocess.run(cmd, check=True, text=True, capture_output=True)
    return json.loads(completed.stdout)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fmt_amount(value):
    if value is None:
        return "N/A"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if abs(value) >= 1e8:
        return f"{value / 1e8:.2f}亿元"
    if abs(value) >= 1e4:
        return f"{value / 1e4:.2f}万元"
    return f"{value:.2f}元"


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
    return "无" if not missing else "、".join(missing)


def table_rows(data, ratios):
    rows = [
        ("营业收入", fmt_amount(data.get("revenue")), fmt_pct(ratios.get("revenue_growth"))),
        ("营业成本", fmt_amount(data.get("cost_of_sales")), "N/A"),
        ("净利润", fmt_amount(data.get("net_profit")), fmt_pct(ratios.get("net_profit_growth"))),
        ("扣非净利润", fmt_amount(data.get("non_recurring_net_profit")), "N/A"),
        ("总资产", fmt_amount(data.get("total_assets")), "N/A"),
        ("总负债", fmt_amount(data.get("total_liabilities")), "N/A"),
        ("经营现金流", fmt_amount(data.get("operating_cash_flow")), fmt_pct(ratios.get("cfo_growth"))),
    ]
    return "\n".join(f"| {name} | {value} | {trend} |" for name, value, trend in rows)


def ratio_rows(ratios):
    rows = [
        ("毛利率", fmt_pct(ratios.get("gross_margin"))),
        ("净利率", fmt_pct(ratios.get("net_margin"))),
        ("ROE", fmt_pct(ratios.get("roe"))),
        ("资产负债率", fmt_pct(ratios.get("debt_to_asset_ratio"))),
        ("流动比率", "N/A" if ratios.get("current_ratio") is None else f"{ratios.get('current_ratio'):.2f}"),
        ("速动比率", "N/A" if ratios.get("quick_ratio") is None else f"{ratios.get('quick_ratio'):.2f}"),
        ("净现比", "N/A" if ratios.get("cfo_to_net_profit") is None else f"{ratios.get('cfo_to_net_profit'):.2f}"),
        ("应计利润率", fmt_pct(ratios.get("accrual_ratio"))),
    ]
    return "\n".join(f"| {name} | {value} |" for name, value in rows)


def quality_rows(analysis):
    items = analysis.get("earnings_quality", {}).get("items", [])
    rows = []
    for item in items:
        score = "缺失" if item.get("score") is None else f"{item.get('score')}/3"
        rows.append(f"| {item.get('name')} | {score} | {item.get('label')} | {item.get('reason')} |")
    return "\n".join(rows)


def red_flag_lines(analysis):
    lines = []
    for check in analysis.get("red_flags", {}).get("checks", []):
        mark = "[!]" if check.get("triggered") else "[x]"
        lines.append(f"- {mark} {check.get('name')}（{check.get('severity')}）：{check.get('evidence')}")
    return "\n".join(lines)


def linkage_lines(analysis):
    return "\n".join(f"- {item.get('name')}：{item.get('status')}，{item.get('detail')}" for item in analysis.get("linkage_checks", []))


def render_markdown(data, ratios, analysis, charts):
    template = (TEMPLATE_DIR / "report_template.md").read_text(encoding="utf-8")
    quality = analysis.get("earnings_quality", {})
    red_flags = analysis.get("red_flags", {})
    cash_matrix = analysis.get("cash_flow_matrix", {})
    dupont = analysis.get("dupont", {})
    replacements = {
        "COMPANY_NAME": data.get("company_name") or "未知公司",
        "REPORT_YEAR": str(data.get("report_year") or "N/A"),
        "REPORT_DATE": str(data.get("report_date") or "N/A"),
        "SUMMARY": f"盈利质量：{quality.get('label', '无法判断')}；红旗风险等级：{red_flags.get('risk_level', '无法判断')}；现金流状态：{cash_matrix.get('state', '无法判断')}。",
        "STATEMENT_TABLE_ROWS": table_rows(data, ratios),
        "RATIO_TABLE_ROWS": ratio_rows(ratios),
        "QUALITY_SCORE": "N/A" if quality.get("score") is None else f"{quality.get('score'):.2f}/3",
        "QUALITY_LABEL": quality.get("label", "无法判断"),
        "QUALITY_TABLE_ROWS": quality_rows(analysis),
        "DUPONT_TEXT": f"ROE={fmt_pct(dupont.get('roe'))}，净利率={fmt_pct(dupont.get('net_margin'))}，资产周转率={fmt_num(dupont.get('asset_turnover'))}，权益乘数={fmt_num(dupont.get('equity_multiplier'))}。",
        "CASH_FLOW_TEXT": f"{cash_matrix.get('state', '无法判断')}：{cash_matrix.get('reason', '现金流字段不足')}",
        "LINKAGE_LINES": linkage_lines(analysis),
        "RED_FLAG_LEVEL": red_flags.get("risk_level", "无法判断"),
        "RED_FLAG_LINES": red_flag_lines(analysis),
        "MISSING_FIELDS": missing_text(data),
        "CHARTS": "\n".join(f"![{name}]({path})" for name, path in charts.items()) if charts else "未生成图表",
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
    parser.add_argument("--input", required=True)
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

    data = run_json([sys.executable, str(SCRIPT_DIR / "extract_financials.py"), "--input", args.input, "--output", str(data_path)])
    ratios = run_json([sys.executable, str(SCRIPT_DIR / "calculate_ratios.py"), "--input", str(data_path), "--output", str(ratios_path)])
    analysis = run_json([sys.executable, str(SCRIPT_DIR / "analyze_quality.py"), "--data", str(data_path), "--ratios", str(ratios_path), "--output", str(analysis_path)])
    charts = {}
    if not args.skip_charts:
        try:
            charts = run_json([sys.executable, str(SCRIPT_DIR / "generate_charts.py"), "--data", str(data_path), "--ratios", str(ratios_path), "--output-dir", str(output_dir / "charts"), "--output", str(charts_path)])
        except Exception as exc:
            charts = {"chart_generation_error": str(exc)}
            charts_path.write_text(json.dumps(charts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    title = f"{data.get('company_name') or '未知公司'} {data.get('report_year') or ''} 财报投研风控分析"
    markdown_text = render_markdown(data, ratios, analysis, charts)
    if args.format in {"md", "both"}:
        (output_dir / "report.md").write_text(markdown_text + "\n", encoding="utf-8")
    if args.format in {"html", "both"}:
        (output_dir / "report.html").write_text(markdown_to_html(markdown_text, title), encoding="utf-8")

    manifest = {
        "financial_data": str(data_path),
        "ratios": str(ratios_path),
        "quality_analysis": str(analysis_path),
        "charts": str(charts_path),
        "report_md": str(output_dir / "report.md") if args.format in {"md", "both"} else None,
        "report_html": str(output_dir / "report.html") if args.format in {"html", "both"} else None,
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
