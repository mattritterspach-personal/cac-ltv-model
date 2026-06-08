"""
CAC / LTV Model — Core Library
Unit economics calculations for B2B SaaS and subscription businesses.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from dataclasses import dataclass, field
from typing import Optional


# ─── Data Model ───────────────────────────────────────────────────────────────

@dataclass
class UnitEconomics:
    """
    Core inputs for unit economics modeling.
    All monetary values in the same currency (e.g., USD).
    """
    # Revenue
    arpu_monthly: float           # Average Revenue Per User per month
    gross_margin_pct: float       # e.g., 0.72 for 72%

    # Churn / Retention
    monthly_churn_rate: float     # e.g., 0.02 for 2%
    monthly_expansion_rate: float = 0.0  # net expansion from upsells

    # Acquisition
    sales_marketing_spend: float = 0.0   # total S&M spend in period
    new_customers: int = 1               # new customers acquired in period
    onboarding_cost_per_customer: float = 0.0

    # Discounting (for NPV-based LTV)
    annual_discount_rate: float = 0.10   # WACC or hurdle rate

    @property
    def cac(self) -> float:
        """Customer Acquisition Cost (fully loaded)."""
        return (self.sales_marketing_spend / self.new_customers) + self.onboarding_cost_per_customer

    @property
    def monthly_net_churn(self) -> float:
        return self.monthly_churn_rate - self.monthly_expansion_rate

    @property
    def ltv_simple(self) -> float:
        """Simple LTV = ARPU × Gross Margin / Churn Rate."""
        if self.monthly_net_churn <= 0:
            return float("inf")
        return (self.arpu_monthly * self.gross_margin_pct) / self.monthly_net_churn

    @property
    def ltv_npv(self) -> float:
        """NPV-adjusted LTV using monthly discount rate."""
        monthly_discount = (1 + self.annual_discount_rate) ** (1 / 12) - 1
        survival_rate = 1 - self.monthly_churn_rate
        # Geometric series: sum of (survival * discount)^t
        r = survival_rate / (1 + monthly_discount)
        if r >= 1:
            return self.arpu_monthly * self.gross_margin_pct * 120  # cap at 10 years
        return (self.arpu_monthly * self.gross_margin_pct) * (r / (1 - r))

    @property
    def ltv_cac_ratio(self) -> float:
        return self.ltv_simple / self.cac if self.cac > 0 else float("inf")

    @property
    def payback_months(self) -> float:
        """Months to recover CAC from gross profit."""
        monthly_gross_profit = self.arpu_monthly * self.gross_margin_pct
        return self.cac / monthly_gross_profit if monthly_gross_profit > 0 else float("inf")

    @property
    def magic_number(self) -> float:
        """
        SaaS Magic Number: measures sales efficiency.
        = (New ARR) / (Prior Quarter S&M Spend)
        Calculated here as (New MRR × 12 × 4) / (Annual S&M).
        Healthy range: 0.75 – 1.5+
        """
        arr_added = self.arpu_monthly * self.new_customers * 12
        return arr_added / self.sales_marketing_spend if self.sales_marketing_spend > 0 else float("inf")

    def summary(self) -> dict:
        return {
            "CAC": round(self.cac, 2),
            "LTV (Simple)": round(self.ltv_simple, 2),
            "LTV (NPV-adjusted)": round(self.ltv_npv, 2),
            "LTV:CAC Ratio": round(self.ltv_cac_ratio, 2),
            "Payback Period (months)": round(self.payback_months, 1),
            "Magic Number": round(self.magic_number, 2),
            "Monthly Churn": f"{self.monthly_churn_rate:.2%}",
            "Gross Margin": f"{self.gross_margin_pct:.1%}",
        }


# ─── Cohort Modeling ──────────────────────────────────────────────────────────

def build_cohort(
    cohort_size: int,
    arpu_monthly: float,
    gross_margin_pct: float,
    monthly_churn_rate: float,
    monthly_expansion_rate: float = 0.0,
    periods: int = 36,
) -> pd.DataFrame:
    """
    Model a single acquisition cohort over `periods` months.
    Returns a DataFrame with customers retained, MRR, cumulative revenue.
    """
    records = []
    customers = cohort_size
    cumulative_revenue = 0.0

    for t in range(periods + 1):
        mrr = customers * arpu_monthly
        gp = mrr * gross_margin_pct
        cumulative_revenue += gp
        records.append({
            "month": t,
            "customers": round(customers),
            "mrr": round(mrr, 2),
            "gross_profit": round(gp, 2),
            "cumulative_gp": round(cumulative_revenue, 2),
            "retention_rate": round(customers / cohort_size, 4),
        })
        customers = customers * (1 - monthly_churn_rate + monthly_expansion_rate)

    return pd.DataFrame(records)


def cohort_payback_month(cohort_df: pd.DataFrame, cac: float, cohort_size: int) -> Optional[int]:
    """Return the month at which cumulative gross profit recovers total CAC spend."""
    total_cac = cac * cohort_size
    recovered = cohort_df[cohort_df["cumulative_gp"] >= total_cac]
    return int(recovered["month"].iloc[0]) if len(recovered) > 0 else None


def multi_cohort_simulation(
    ue: UnitEconomics,
    cohort_sizes: list[int],
    cohort_labels: Optional[list[str]] = None,
    periods: int = 36,
) -> pd.DataFrame:
    """Simulate multiple cohorts and return a combined DataFrame."""
    frames = []
    for i, size in enumerate(cohort_sizes):
        label = cohort_labels[i] if cohort_labels else f"Cohort {i+1}"
        df = build_cohort(size, ue.arpu_monthly, ue.gross_margin_pct, ue.monthly_churn_rate, ue.monthly_expansion_rate, periods)
        df["cohort"] = label
        df["cohort_size"] = size
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


# ─── Scenario Analysis ────────────────────────────────────────────────────────

def sensitivity_table(
    base: UnitEconomics,
    churn_range: list[float],
    arpu_range: list[float],
) -> pd.DataFrame:
    """
    Build an LTV:CAC sensitivity table varying churn and ARPU.
    Returns a pivot table suitable for heatmap visualization.
    """
    rows = []
    for churn in churn_range:
        for arpu in arpu_range:
            ue = UnitEconomics(
                arpu_monthly=arpu,
                gross_margin_pct=base.gross_margin_pct,
                monthly_churn_rate=churn,
                sales_marketing_spend=base.sales_marketing_spend,
                new_customers=base.new_customers,
            )
            rows.append({"churn": churn, "arpu": arpu, "ltv_cac": round(ue.ltv_cac_ratio, 2)})
    df = pd.DataFrame(rows)
    return df.pivot(index="churn", columns="arpu", values="ltv_cac")


# ─── Charts ───────────────────────────────────────────────────────────────────

def plot_cohort_retention(cohort_df: pd.DataFrame) -> go.Figure:
    """Line chart of retention curves for multiple cohorts."""
    fig = px.line(
        cohort_df, x="month", y="retention_rate", color="cohort",
        labels={"month": "Month", "retention_rate": "Retention Rate", "cohort": "Cohort"},
        title="Cohort Retention Curves",
    )
    fig.update_yaxes(tickformat=".0%")
    fig.update_layout(height=400)
    return fig


def plot_cumulative_ltv(cohort_df: pd.DataFrame, cac: float) -> go.Figure:
    """Cumulative gross profit per customer vs CAC payback line."""
    first_cohort = cohort_df[cohort_df["cohort"] == cohort_df["cohort"].iloc[0]].copy()
    first_cohort["ltv_per_customer"] = first_cohort["cumulative_gp"] / first_cohort["cohort_size"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=first_cohort["month"], y=first_cohort["ltv_per_customer"],
        mode="lines", name="Cumulative GP / Customer",
        line=dict(color="#4F46E5", width=3),
    ))
    fig.add_hline(y=cac, line_dash="dash", line_color="#EF4444",
                  annotation_text=f"CAC = ${cac:,.0f}", annotation_position="top right")
    fig.update_layout(
        title="Cumulative LTV vs CAC Payback",
        xaxis_title="Month", yaxis_title="$ per Customer",
        height=400,
    )
    return fig


def plot_sensitivity_heatmap(pivot: pd.DataFrame) -> go.Figure:
    """Heatmap of LTV:CAC across churn × ARPU scenarios."""
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"${v}" for v in pivot.columns],
        y=[f"{v:.1%}" for v in pivot.index],
        colorscale="RdYlGn",
        zmid=3,
        text=[[f"{v:.1f}x" for v in row] for row in pivot.values],
        texttemplate="%{text}",
    ))
    fig.update_layout(
        title="LTV:CAC Sensitivity — Churn Rate vs ARPU",
        xaxis_title="Monthly ARPU",
        yaxis_title="Monthly Churn Rate",
        height=420,
    )
    return fig


def plot_unit_economics_gauge(ue: UnitEconomics) -> go.Figure:
    """Gauge charts for key health metrics."""
    fig = make_subplots(rows=1, cols=3, specs=[[{"type": "indicator"}] * 3])

    fig.add_trace(go.Indicator(
        mode="gauge+number", value=round(ue.ltv_cac_ratio, 1),
        title={"text": "LTV:CAC Ratio"},
        gauge={"axis": {"range": [0, 10]}, "bar": {"color": "#4F46E5"},
               "steps": [{"range": [0, 1], "color": "#FEE2E2"},
                          {"range": [1, 3], "color": "#FEF9C3"},
                          {"range": [3, 10], "color": "#DCFCE7"}]},
    ), row=1, col=1)

    fig.add_trace(go.Indicator(
        mode="gauge+number", value=round(ue.payback_months, 1),
        title={"text": "Payback (months)"},
        gauge={"axis": {"range": [0, 36]}, "bar": {"color": "#7C3AED"},
               "steps": [{"range": [0, 12], "color": "#DCFCE7"},
                          {"range": [12, 18], "color": "#FEF9C3"},
                          {"range": [18, 36], "color": "#FEE2E2"}]},
    ), row=1, col=2)

    fig.add_trace(go.Indicator(
        mode="gauge+number", value=round(ue.magic_number, 2),
        title={"text": "Magic Number"},
        gauge={"axis": {"range": [0, 3]}, "bar": {"color": "#A855F7"},
               "steps": [{"range": [0, 0.75], "color": "#FEE2E2"},
                          {"range": [0.75, 1.5], "color": "#FEF9C3"},
                          {"range": [1.5, 3], "color": "#DCFCE7"}]},
    ), row=1, col=3)

    fig.update_layout(height=300, title="Unit Economics Health Check")
    return fig
