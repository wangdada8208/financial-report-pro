# Notices and Attribution

This repository contains `financial-report-pro`, a local Codex skill for financial report extraction, three-statement analysis, earnings-quality checks, DuPont decomposition, red-flag risk review, chart generation, and Markdown/HTML report rendering.

## Third-party sources

This skill includes code structure, formulas, workflow ideas, and analysis patterns adapted from the following MIT-licensed projects:

1. DB-GPT `financial-report-analyzer`
   - Source: https://github.com/eosphoros-ai/DB-GPT/tree/main/skills/financial-report-analyzer
   - License: MIT License
   - Copyright: Copyright (c) 2023 magic.chen

2. Vibe-Trading `financial-statement`
   - Source: https://github.com/HKUDS/Vibe-Trading/tree/main/agent/src/skills/financial-statement
   - License: MIT License
   - Copyright: Copyright (c) 2026 Vibe-Trading Contributors

The combined skill has been modified for local Codex usage and does not depend on DB-GPT runtime tools such as `execute_skill_script_file` or `html_interpreter`.

## License compliance

The upstream projects are MIT-licensed. Their copyright notices and permission notices are preserved in `THIRD_PARTY_LICENSES.md`.

This repository is not affiliated with, endorsed by, or sponsored by DB-GPT, eosphoros-ai, HKUDS, or Vibe-Trading.

## Financial disclaimer

Generated reports are for research and risk-screening support only. They are not investment advice, accounting advice, legal advice, or a substitute for reviewing original filings and audit opinions.
