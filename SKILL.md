---
name: financial-report-pro
description: Local Codex skill for cross-market financial report and disclosure analysis. Use for Chinese listed-company reports, US SEC EDGAR filings, 10-K, 10-Q, 8-K, DEF 14A, Form 4, 13F, SC 13D/G, PDF/text/HTML/JSON extraction, three-statement data normalization, ratio calculation, earnings-quality scoring, DuPont decomposition, red-flag review, SEC filing signals, charts, and Markdown/HTML reports.
---

# Financial Report Pro

Use this skill to turn company financial reports and public-company disclosures into a local, investment-risk-focused analysis package. Prefer the bundled scripts for deterministic extraction, ratio calculation, quality checks, EDGAR retrieval, filing-signal analysis, charts, and report rendering.

## Standard Workflows

Analyze a local filing or financial report:

```bash
python scripts/render_report.py --input /path/to/report.pdf --output-dir /path/to/output --profile auto --format both
```

Fetch and analyze a SEC EDGAR filing:

```bash
EDGAR_USER_AGENT="Your Name your.email@example.com" \
python scripts/render_report.py --ticker AAPL --filing-type 10-K --fetch-sec --output-dir /path/to/output --profile us --format both
```

SEC requests require either `EDGAR_USER_AGENT` or `--user-agent`. Do not send anonymous SEC requests.

## Profiles

- `auto`: Detect Chinese-language reports vs US/SEC filings from the content.
- `cn`: Chinese listed-company report mode for A-share and Chinese-language Hong Kong filings.
- `us`: US SEC filing mode for 10-K, 10-Q, 8-K, DEF 14A, Form 4, 13F, and SC 13D/G.

## Outputs

Inspect generated files before presenting conclusions:

- `financial_data.json`: extracted or normalized statement data
- `ratios.json`: calculated metrics, including FCF metrics when available
- `quality_analysis.json`: linkage checks, earnings quality, DuPont, red flags
- `sec_metadata.json`: SEC filing retrieval metadata when `--fetch-sec` is used
- `sec_filing_analysis.json`: SEC filing signals for US/SEC inputs
- `composite_signal.json`: composite SEC signal summary
- `report.md` and `report.html`: readable reports

## Script Tasks

- Use `scripts/extract_financials.py` for PDF/text/HTML/markdown extraction or JSON normalization.
- Use `scripts/fetch_sec_filings.py` to retrieve public SEC filings by ticker or CIK.
- Use `scripts/calculate_ratios.py` when structured financial JSON already exists.
- Use `scripts/analyze_quality.py` for three-statement linkage checks, earnings quality scoring, DuPont decomposition, cash-flow matrix, and red-flag detection.
- Use `scripts/analyze_sec_filings.py` for 10-K/10-Q/8-K/proxy/Form 4/13F/13D/G filing-signal analysis.
- Use `scripts/render_report.py` for the full pipeline and final report generation.

## Data Contract

Use these normalized field names when preparing or editing JSON:

- Basic: `company_name`, `ticker`, `cik`, `report_year`, `report_date`, `filing_type`, `market_profile`, `source_url`
- Income statement: `revenue`, `cost_of_sales`, `gross_profit`, `operating_income`, `net_profit`, `non_recurring_net_profit`
- Balance sheet: `total_assets`, `total_liabilities`, `equity`, `cash`, `accounts_receivable`, `inventory`, `interest_bearing_debt`, `goodwill`, `intangibles`
- Cash flow statement: `operating_cash_flow`, `investing_cash_flow`, `financing_cash_flow`, `capex`, `stock_based_compensation`
- Optional comparison fields: prefix prior-period values with `prev_`, such as `prev_revenue`, `prev_net_profit`, `prev_accounts_receivable`

Amounts should be raw numeric currency units when possible. Ratios are stored as decimals, for example `0.125` for `12.5%`.

## Reference Files

- Read `references/financial_metrics.md` when ratio definitions or field formulas matter.
- Read `references/statement_analysis_framework.md` when writing narrative judgment for earnings quality, cash-flow quality, or DuPont drivers.
- Read `references/fraud_red_flags.md` when explaining red flags and risk levels.
- Read `references/sec_filing_analysis.md` when explaining SEC filing types, EDGAR limitations, 8-K event signals, insider activity, institutional positioning, or composite filing signals.

## Reporting Rules

- Keep conclusions evidence-based and tied to extracted fields, calculated ratios, filing text, or explicitly named missing data.
- Treat banks, insurers, and other financial institutions as special cases; traditional current ratio, inventory, and operating-cash-flow heuristics may not apply.
- Prefer same-company multi-period trends over cross-industry thresholds.
- Include a short investment-risk conclusion, not investment advice.
