# Financial Report Pro

`financial-report-pro` is a local Codex skill for Chinese listed-company financial report analysis. It extracts three-statement data, calculates ratios, evaluates earnings quality, runs DuPont decomposition, checks red-flag risks, generates charts, and renders Markdown/HTML reports.

## Usage

```bash
python scripts/render_report.py \
  --input /path/to/report.pdf \
  --output-dir /path/to/output \
  --format both
```

The pipeline writes:

- `financial_data.json`
- `ratios.json`
- `quality_analysis.json`
- `charts.json`
- `report.md`
- `report.html`

## Attribution

This project includes adapted material from:

- DB-GPT `financial-report-analyzer`: https://github.com/eosphoros-ai/DB-GPT/tree/main/skills/financial-report-analyzer
- Vibe-Trading `financial-statement`: https://github.com/HKUDS/Vibe-Trading/tree/main/agent/src/skills/financial-statement

Both upstream projects are licensed under the MIT License. See `NOTICE.md` and `THIRD_PARTY_LICENSES.md` for copyright notices and license text.

## Disclaimer

This tool is for research and risk-screening support only. It is not investment advice, accounting advice, legal advice, or a substitute for reviewing original filings and audit opinions.
