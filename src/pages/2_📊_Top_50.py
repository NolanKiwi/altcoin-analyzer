"""Top 50 altcoins ranked by biggest price drop from 2025 peak."""

import sys
from pathlib import Path

import plotly.express as px
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.auto_fetch import ensure_data
from src.config import CACHE_TTL, RESULTS_CSV

st.set_page_config(page_title="Top 50 - Altcoin Analyzer", page_icon="📊", layout="wide")


@st.cache_data(ttl=CACHE_TTL)
def load_results() -> pd.DataFrame:
    """Load analysis results."""
    if not RESULTS_CSV.exists():
        return pd.DataFrame()
    return pd.read_csv(RESULTS_CSV)


st.title("📊 Top 50 Biggest Drops")
st.markdown("Altcoins ranked by largest percentage drop from their 2025 peak price.")

if not ensure_data():
    st.stop()

results = load_results()
if results.empty:
    st.warning("No data available. Run the data pipeline first.")
    st.stop()

# Filters
col_filter1, col_filter2 = st.columns(2)
with col_filter1:
    search = st.text_input("🔍 Search by name or symbol", "")
with col_filter2:
    min_mcap = st.number_input("Min Market Cap ($)", value=0, step=1_000_000,
                               format="%d")

filtered = results.copy()
if search:
    name_match = filtered["coin_name"].str.contains(search, case=False, na=False)
    sym_match = filtered["symbol"].str.contains(search, case=False, na=False)
    mask = name_match | sym_match
    filtered = filtered[mask]
if min_mcap > 0:
    filtered = filtered[filtered["market_cap"] >= min_mcap]


# Color-code by drop severity
def drop_color(val: float) -> str:
    """Return CSS color based on drop severity."""
    if val <= -80:
        return "color: #ff4444; font-weight: bold"
    elif val <= -60:
        return "color: #ff8800"
    else:
        return "color: #ffcc00"


# Interactive table
st.subheader(f"Showing {len(filtered)} coins")

display_cols = ["coin_name", "symbol", "peak_price", "peak_date",
                "current_price", "current_date", "pct_change", "market_cap"]

available_cols = [c for c in display_cols if c in filtered.columns]

styled = filtered[available_cols].style.format({
    "peak_price": "${:.4f}",
    "current_price": "${:.4f}",
    "pct_change": "{:+.2f}%",
    "market_cap": "${:,.0f}",
}).map(drop_color, subset=["pct_change"] if "pct_change" in available_cols else [])

st.dataframe(styled, width="stretch", height=600)

# Download buttons
col_dl1, col_dl2, _ = st.columns([1, 1, 4])
with col_dl1:
    csv_data = filtered.to_csv(index=False)
    st.download_button(
        "📥 Download CSV",
        csv_data,
        "altcoin_drops_top50.csv",
        "text/csv",
    )
with col_dl2:
    json_data = filtered.to_json(orient="records", indent=2)
    st.download_button(
        "📥 Download JSON",
        json_data,
        "altcoin_drops_top50.json",
        "application/json",
    )

st.markdown("---")

# Bar chart - Top 20
st.subheader("Top 20 by Drop Percentage")
chart_data = filtered.head(20)

fig = px.bar(
    chart_data,
    x="symbol",
    y="pct_change",
    color="pct_change",
    color_continuous_scale="RdYlGn",
    labels={"pct_change": "% Drop from Peak", "symbol": "Coin"},
    hover_data=["coin_name", "peak_price", "current_price", "peak_date"],
    text="pct_change",
)
fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
fig.update_layout(
    height=500,
    xaxis_tickangle=-45,
    showlegend=False,
)
st.plotly_chart(fig, width="stretch")

# Distribution chart
st.subheader("Drop Distribution")
fig_hist = px.histogram(
    filtered,
    x="pct_change",
    nbins=20,
    labels={"pct_change": "% Drop from Peak"},
    color_discrete_sequence=["#667eea"],
)
fig_hist.update_layout(height=350)
st.plotly_chart(fig_hist, width="stretch")
