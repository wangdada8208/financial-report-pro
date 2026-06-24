---
name: financial-report-pro
description: Local Codex skill for Chinese listed-company annual/quarterly financial report analysis from PDF, text, markdown, or structured JSON. Use for extracting three-statement data, calculating financial ratios, checking statement linkages, scoring earnings quality, running DuPont decomposition, identifying financial red flags, and generating investment-risk-focused Markdown/HTML reports.
---

# Financial Report Pro

Use this skill to turn a company financial report into a local, investment-risk-focused analysis package. Prefer the bundled scripts for deterministic extraction, ratio calculation, quality checks, charts, and report rendering.

## Standard Workflow

1. Run the end-to-end report renderer when the user gives a PDF/text/markdown/JSON report:

```bash
python scripts/render_report.py --input /path/to/report.pdf --output-dir /path/to/output --format both
```

2. Inspect the generated files before presenting conclusions:
   - `financial_data.json`: extracted or normalized statement data
   - `ratios.json`: calculated metrics
   - `quality_analysis.json`: linkage checks, earnings quality, DuPont, red flags
   - `report.md`: readable Markdown report
   - `report.html`: readable HTML report when `--format html` or `--format both`

3. If extraction confidence is low or required fields are missing, state the missing fields clearly. Do not invent financial values.

## Script Tasks

- Use `scripts/extract_financials.py` for PDF/text/markdown extraction or JSON normalization.
- Use `scripts/calculate_ratios.py` when the user already has structured financial JSON and only needs metrics.
- Use `scripts/analyze_quality.py` for three-statement linkage checks, earnings quality scoring, DuPont decomposition, cash-flow matrix, and red-flag detection.
- Use `scripts/generate_charts.py` to create PNG charts from structured JSON.
- Use `scripts/render_report.py` for the full pipeline and final report generation.

All scripts accept local filesystem paths and write local outputs. They do not rely on DB-GPT runtime tools such as `execute_skill_script_file` or `html_interpreter`.

## Data Contract

Use these normalized field names when preparing or editing JSON:

- Basic: `company_name`, `report_year`, `report_date`
- Income statement: `revenue`, `cost_of_sales`, `net_profit`, `non_recurring_net_profit`
- Balance sheet: `total_assets`, `total_liabilities`, `equity`, `cash`, `accounts_receivable`, `inventory`, `interest_bearing_debt`
- Cash flow statement: `operating_cash_flow`, `investing_cash_flow`, `financing_cash_flow`
- Optional comparison fields: prefix prior-period values with `prev_`, such as `prev_revenue`, `prev_net_profit`, `prev_accounts_receivable`

Amounts should be raw numeric currency units when possible. Ratios are stored as decimals, for example `0.125` for `12.5%`.

## Reference Files

- Read `references/financial_metrics.md` when ratio definitions or field formulas matter.
- Read `references/statement_analysis_framework.md` when writing narrative judgment for earnings quality, cash-flow quality, or DuPont drivers.
- Read `references/fraud_red_flags.md` when explaining red flags and risk levels.

## Reporting Rules

- Keep conclusions evidence-based and tied to extracted fields, calculated ratios, or explicitly named missing data.
- Treat banks, insurers, and other financial institutions as special cases; traditional current ratio, inventory, and operating-cash-flow heuristics may not apply.
- Prefer same-company multi-period trends over cross-industry thresholds.
- Include a short investment-risk conclusion, not investment advice.
