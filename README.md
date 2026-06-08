# CAC / LTV Model

A rigorous unit-economics toolkit for B2B and B2C businesses. Includes an Excel model for finance teams and a Python library for data teams — both producing identical outputs.

## What's Inside

| File | Description |
|------|-------------|
| `cac_ltv_model.py` | Python library: CAC, LTV, payback, cohort analysis |
| `dashboard.py` | Streamlit interactive unit-economics dashboard |
| `cac_ltv_workbook.xlsx` | Excel model with formulas, charts, and scenario tabs |
| `requirements.txt` | Python dependencies |

## Key Metrics

| Metric | Formula |
|--------|---------|
| **CAC** | Total Sales & Marketing Spend / New Customers Acquired |
| **Blended CAC** | (S&M Spend + Product CAC) / New Customers |
| **LTV** | ARPU × Gross Margin % × (1 / Churn Rate) |
| **LTV:CAC Ratio** | LTV / CAC — healthy benchmark: > 3× |
| **CAC Payback Period** | CAC / (ARPU × Gross Margin %) — benchmark: < 12 months |
| **Net Revenue Retention** | (Starting MRR + Expansion − Churn) / Starting MRR |

## Cohort Analysis

The model tracks monthly acquisition cohorts and plots:
- Revenue retained over time
- Cumulative LTV curves
- Payback period heatmap by cohort
- Churn curves by acquisition channel

## Quick Start

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

## Excel Model Tabs

1. **Inputs** — enter your spend, customer, and revenue data here
2. **CAC Analysis** — blended and channel-specific CAC over time
3. **LTV Model** — LTV curves, retention schedules, discount rates
4. **Unit Economics** — LTV:CAC, payback, magic number, efficiency ratio
5. **Scenarios** — best/base/worst case sensitivity analysis
6. **Charts** — auto-updating visuals for board presentations

## License

MIT
