# Financial Report Pro

`financial-report-pro` is a local Codex skill for cross-market financial report and disclosure analysis. It supports Chinese listed-company reports and US SEC EDGAR filings, extracts three-statement data, calculates ratios, evaluates earnings quality, runs DuPont decomposition, checks red-flag risks, analyzes SEC filing signals, generates charts, and renders Markdown/HTML reports.

## Local file usage

```bash
python scripts/render_report.py \
  --input /path/to/report.pdf \
  --output-dir /path/to/output \
  --profile auto \
  --format both
```

## SEC EDGAR usage

SEC requests require a descriptive User-Agent. Set `EDGAR_USER_AGENT` or pass `--user-agent`; the repository does not hard-code personal contact details.

```bash
EDGAR_USER_AGENT="Your Name your.email@example.com" \
python scripts/render_report.py \
  --ticker AAPL \
  --filing-type 10-K \
  --fetch-sec \
  --output-dir /path/to/output \
  --profile us \
  --format both
```

The pipeline can write:

- `financial_data.json`
- `ratios.json`
- `quality_analysis.json`
- `sec_metadata.json`
- `sec_filing_analysis.json`
- `composite_signal.json`
- `charts.json`
- `report.md`
- `report.html`

## Supported profiles

- `cn`: Chinese listed-company annual/quarterly reports.
- `us`: SEC filings including 10-K, 10-Q, 8-K, DEF 14A, Form 4, 13F, and SC 13D/G.
- `auto`: content-based profile detection.

## Attribution

This project includes adapted material from:

- DB-GPT `financial-report-analyzer`: https://github.com/eosphoros-ai/DB-GPT/tree/main/skills/financial-report-analyzer
- Vibe-Trading `financial-statement`: https://github.com/HKUDS/Vibe-Trading/tree/main/agent/src/skills/financial-statement
- Vibe-Trading `edgar-sec-filings`: https://github.com/HKUDS/Vibe-Trading/tree/main/agent/src/skills/edgar-sec-filings

The upstream projects are licensed under the MIT License. See `NOTICE.md` and `THIRD_PARTY_LICENSES.md` for copyright notices and license text.

## Disclaimer

This tool is for research and risk-screening support only. It is not investment advice, accounting advice, legal advice, or a substitute for reviewing original filings and audit opinions.
