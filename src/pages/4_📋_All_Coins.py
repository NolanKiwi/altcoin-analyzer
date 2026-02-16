"""All coins ranked by price drop from 2025 peak."""

import sys
from pathlib import Path

import plotly.express as px
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.analyzer import rank_by_drop
from src.config import CACHE_TTL, PRICES_CSV

st.set_page_config(page_title="All Coins - Altcoin Analyzer", page_icon="📋", layout="wide")


@st.cache_data(ttl=CACHE_TTL)
def load_all_drops() -> pd.DataFrame:
    """Load price data and rank ALL coins by drop (no top-N limit)."""
    if not PRICES_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(PRICES_CSV, parse_dates=["date"])
    return rank_by_drop(df, top_n=len(df["coin_id"].unique()))


st.title("📋 All Coins")
st.markdown("Every tracked altcoin ranked by percentage drop from their 2025 peak price.")

results = load_all_drops()
if results.empty:
    st.warning("No data available. Run the data pipeline first.")
    st.stop()

# Filters
col_filter1, col_filter2 = st.columns(2)
with col_filter1:
    search = st.text_input("🔍 Search by name or symbol", "", key="all_coins_search")
with col_filter2:
    drop_range = st.slider(
        "Drop % range",
        min_value=int(results["pct_change"].min()) - 1,
        max_value=0,
        value=(int(results["pct_change"].min()) - 1, 0),
    )

filtered = results.copy()
if search:
    name_match = filtered["coin_name"].str.contains(search, case=False, na=False)
    sym_match = filtered["symbol"].str.contains(search, case=False, na=False)
    filtered = filtered[name_match | sym_match]
filtered = filtered[
    (filtered["pct_change"] >= drop_range[0]) & (filtered["pct_change"] <= drop_range[1])
]


# Color-code by drop severity
def drop_color(val: float) -> str:
    """Return CSS color based on drop severity."""
    if val <= -80:
        return "color: #ff4444; font-weight: bold"
    elif val <= -60:
        return "color: #ff8800"
    else:
        return "color: #ffcc00"


# Summary metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Coins", len(filtered))
col2.metric("Avg Drop", f"{filtered['pct_change'].mean():.1f}%")
col3.metric("Median Drop", f"{filtered['pct_change'].median():.1f}%")
col4.metric("Worst Drop", f"{filtered['pct_change'].min():.1f}%")

st.markdown("---")

# Interactive table
st.subheader(f"Showing {len(filtered)} coins")

display_cols = ["coin_name", "symbol", "peak_price", "peak_date",
                "current_price", "current_date", "pct_change", "volume"]
available_cols = [c for c in display_cols if c in filtered.columns]

styled = filtered[available_cols].style.format({
    "peak_price": "${:.4f}",
    "current_price": "${:.4f}",
    "pct_change": "{:+.2f}%",
    "volume": "${:,.0f}",
}).map(drop_color, subset=["pct_change"] if "pct_change" in available_cols else [])

st.dataframe(styled, width="stretch", height=600)

# Download buttons
col_dl1, col_dl2, _ = st.columns([1, 1, 4])
with col_dl1:
    csv_data = filtered.to_csv(index=False)
    st.download_button(
        "📥 Download CSV",
        csv_data,
        "altcoin_drops_all.csv",
        "text/csv",
    )
with col_dl2:
    json_data = filtered.to_json(orient="records", indent=2)
    st.download_button(
        "📥 Download JSON",
        json_data,
        "altcoin_drops_all.json",
        "application/json",
    )

st.markdown("---")

# Distribution chart
st.subheader("Drop Distribution")
fig_hist = px.histogram(
    filtered,
    x="pct_change",
    nbins=30,
    labels={"pct_change": "% Drop from Peak"},
    color_discrete_sequence=["#667eea"],
)
fig_hist.update_layout(height=350)
st.plotly_chart(fig_hist, width="stretch")
