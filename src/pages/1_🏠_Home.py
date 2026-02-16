"""Home page with overview metrics and quick preview."""

import sys
from pathlib import Path

import plotly.express as px
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.auto_fetch import ensure_data
from src.config import CACHE_TTL, PRICES_CSV, RESULTS_CSV

st.set_page_config(page_title="Home - Altcoin Analyzer", page_icon="🏠", layout="wide")


@st.cache_data(ttl=CACHE_TTL)
def load_results() -> pd.DataFrame:
    """Load analysis results."""
    if not RESULTS_CSV.exists():
        return pd.DataFrame()
    return pd.read_csv(RESULTS_CSV)


@st.cache_data(ttl=CACHE_TTL)
def load_prices() -> pd.DataFrame:
    """Load price data."""
    if not PRICES_CSV.exists():
        return pd.DataFrame()
    return pd.read_csv(PRICES_CSV, parse_dates=["date"])


st.title("🏠 Dashboard Home")
st.markdown("Overview of altcoin price drops from 2025 peaks.")

if not ensure_data():
    st.stop()

results = load_results()
if results.empty:
    st.warning("No data available. Run the data pipeline first.")
    st.stop()

# Metric cards
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Coins Tracked", len(results))
col2.metric("Avg Drop %", f"{results['pct_change'].mean():.1f}%")
col3.metric(
    "Biggest Loser",
    results.iloc[0]["symbol"].upper(),
    f"{results.iloc[0]['pct_change']:.1f}%",
)

import os  # noqa: E402
if RESULTS_CSV.exists():
    from datetime import datetime  # noqa: E402
    mtime = os.path.getmtime(RESULTS_CSV)
    col4.metric("Last Updated", datetime.fromtimestamp(mtime).strftime("%b %d, %H:%M"))

st.markdown("---")

# Top 10 preview table
st.subheader("Top 10 Biggest Drops")
top10 = results.head(10).copy()
top10["rank"] = range(1, len(top10) + 1)

fmt = {
    "peak_price": "${:.4f}",
    "current_price": "${:.4f}",
    "pct_change": "{:+.2f}%",
    "market_cap": "${:,.0f}",
}
st.dataframe(
    top10[["rank", "coin_name", "symbol", "peak_price", "current_price",
           "pct_change", "market_cap"]].style.format(fmt),
    width="stretch",
    hide_index=True,
)

# Quick stats bar chart
st.subheader("Top 10 by Drop Percentage")
fig = px.bar(
    top10,
    x="symbol",
    y="pct_change",
    color="pct_change",
    color_continuous_scale="RdYlGn",
    labels={"pct_change": "% Change from Peak", "symbol": "Coin"},
    hover_data=["coin_name", "peak_price", "current_price"],
    text="pct_change",
)
fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
fig.update_layout(
    height=450,
    xaxis_tickangle=-45,
    showlegend=False,
)
st.plotly_chart(fig, width="stretch")

st.markdown("---")
st.page_link("pages/2_📊_Top_50.py", label="📊 View Full Top 50 Rankings →",
             icon="📊")
