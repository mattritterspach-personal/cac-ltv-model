"""
CAC / LTV Dashboard — Streamlit
Run: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
from cac_ltv_model import (
    UnitEconomics, build_cohort, multi_cohort_simulation, sensitivity_table,
    plot_cohort_retention, plot_cumulative_ltv, plot_sensitivity_heatmap, plot_unit_economics_gauge,
)

st.set_page_config(page_title="CAC / LTV Model", page_icon="💰", layout="wide")
st.title("💰 CAC / LTV Unit Economics Model")
st.caption("Model your customer acquisition cost, lifetime value, payback period, and growth efficiency.")

# ─── Inputs ───────────────────────────────────────────────────────────────────
st.sidebar.title("⚙️ Model Inputs")

st.sidebar.subheader("Revenue")
arpu = st.sidebar.number_input("Monthly ARPU ($)", value=500, step=50)
gm = st.sidebar.slider("Gross Margin", 0.0, 1.0, 0.72, 0.01, format="%.0f%%")

st.sidebar.subheader("Churn & Expansion")
churn = st.sidebar.slider("Monthly Churn Rate", 0.005, 0.10, 0.02, 0.005, format="%.1f%%")
expansion = st.sidebar.slider("Monthly Expansion Rate", 0.0, 0.05, 0.005, 0.001, format="%.1f%%")

st.sidebar.subheader("Acquisition")
sm_spend = st.sidebar.number_input("S&M Spend (period, $)", value=250_000, step=10_000)
new_custs = st.sidebar.number_input("New Customers (period)", value=100, step=10)
onboarding = st.sidebar.number_input("Onboarding Cost / Customer ($)", value=200, step=50)

st.sidebar.subheader("Cohort Simulation")
cohort_size = st.sidebar.number_input("Cohort Size", value=100, step=10)
periods = st.sidebar.slider("Simulation Months", 12, 60, 36)

discount_rate = st.sidebar.number_input("Annual Discount Rate (%)", value=10, step=1) / 100

ue = UnitEconomics(
    arpu_monthly=arpu,
    gross_margin_pct=gm,
    monthly_churn_rate=churn,
    monthly_expansion_rate=expansion,
    sales_marketing_spend=sm_spend,
    new_customers=new_custs,
    onboarding_cost_per_customer=onboarding,
    annual_discount_rate=discount_rate,
)

# ─── KPI Summary ──────────────────────────────────────────────────────────────
summary = ue.summary()
cols = st.columns(len(summary))
for col, (label, value) in zip(cols, summary.items()):
    col.metric(label, value)

st.divider()

# ─── Gauge Charts ─────────────────────────────────────────────────────────────
st.plotly_chart(plot_unit_economics_gauge(ue), use_container_width=True)

# ─── Cohort Analysis ──────────────────────────────────────────────────────────
st.subheader("📊 Cohort Analysis")

labels = ["Month 1", "Month 4", "Month 7", "Month 10"]
sizes = [cohort_size, int(cohort_size * 1.1), int(cohort_size * 0.9), int(cohort_size * 1.2)]
cohort_df = multi_cohort_simulation(ue, sizes, labels, periods)

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(plot_cohort_retention(cohort_df), use_container_width=True)
with col2:
    single_cohort = build_cohort(cohort_size, arpu, gm, churn, expansion, periods)
    single_cohort["cohort"] = "Base Cohort"
    single_cohort["cohort_size"] = cohort_size
    st.plotly_chart(plot_cumulative_ltv(single_cohort, ue.cac), use_container_width=True)

# ─── Sensitivity Analysis ─────────────────────────────────────────────────────
st.subheader("🔍 Sensitivity Analysis — LTV:CAC by Churn × ARPU")
churn_range = [0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05]
arpu_range = [200, 350, 500, 750, 1000, 1500, 2000]
pivot = sensitivity_table(ue, churn_range, arpu_range)
st.plotly_chart(plot_sensitivity_heatmap(pivot), use_container_width=True)

# ─── Raw Cohort Table ─────────────────────────────────────────────────────────
with st.expander("📋 Cohort Data Table"):
    st.dataframe(single_cohort.drop(columns=["cohort", "cohort_size"]), use_container_width=True, hide_index=True)
