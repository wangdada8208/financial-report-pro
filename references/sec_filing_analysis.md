# SEC Filing Analysis

## Filing Types

| Filing | Signal |
| :--- | :--- |
| 10-K | Annual fundamentals, risk factors, MD&A, segment disclosures |
| 10-Q | Quarterly trend confirmation and inflection detection |
| 8-K | Material event catalyst or risk trigger |
| DEF 14A | Governance, executive compensation, board composition |
| Form 4 | Insider purchase and sale activity |
| 13F | Institutional ownership positioning, reported with lag |
| SC 13D/G | More-than-5% ownership, activist or strategic investor signal |

## Key Signals

- Financial health: revenue growth, margin trend, FCF conversion, balance sheet leverage.
- MD&A tone: positive, negative, and cautious language frequency.
- Risk factors: new or intensified risks, cybersecurity, internal controls, litigation.
- 8-K events: Item 4.02 restatement is high priority negative; Item 5.02 CEO/CFO departure is uncertainty; Item 2.02 earnings event is time-sensitive.
- Form 4: open-market insider purchases are usually more informative than planned sales.
- 13F and 13D/G: ownership data is useful but lagged and should not be treated as real time.

## Composite Signal

Score each dimension from `-2` to `+2`:

- `financial_health`
- `management_tone`
- `risk_factor_change`
- `event_catalyst`
- `insider_activity`
- `institutional_flow`

Interpretation:

- `> +6`: strong fundamental bullish
- `+2 to +6`: mild bullish
- `-2 to +2`: neutral
- `< -2`: fundamental caution

This framework is for research support only and is not investment advice.
