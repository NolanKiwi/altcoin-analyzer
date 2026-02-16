"""Main Streamlit dashboard entry point for the Altcoin Price Drop Analyzer.

Run with: streamlit run src/dashboard.py
"""

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import CACHE_TTL, PRICES_CSV, RESULTS_CSV

st.set_page_config(
    page_title="Altcoin Analyzer",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
    }
    .stMetric > div {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=CACHE_TTL)
def load_results() -> pd.DataFrame:
    """Load analysis results with caching."""
    if not RESULTS_CSV.exists():
        return pd.DataFrame()
    return pd.read_csv(RESULTS_CSV)


@st.cache_data(ttl=CACHE_TTL)
def load_prices() -> pd.DataFrame:
    """Load price history data with caching."""
    if not PRICES_CSV.exists():
        return pd.DataFrame()
    return pd.read_csv(PRICES_CSV, parse_dates=["date"])


# Sidebar
st.sidebar.title("📉 Altcoin Analyzer")
st.sidebar.markdown("---")

if RESULTS_CSV.exists():
    last_modified = os.path.getmtime(RESULTS_CSV)
    from datetime import datetime
    last_update = datetime.fromtimestamp(last_modified).strftime("%Y-%m-%d %H:%M")
    st.sidebar.info(f"Last updated: {last_update}")

if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Navigation**: Use the pages in the sidebar to explore different views."
)
st.sidebar.markdown("---")
st.sidebar.caption("Data source: Binance via CCXT")

# Main content - redirect to Home
st.markdown('<p class="main-header">📉 Altcoin Price Drop Analyzer</p>',
            unsafe_allow_html=True)
st.markdown('<p class="sub-header">'
            'Tracking the biggest altcoin price drops from their 2025 peaks'
            '</p>', unsafe_allow_html=True)

results = load_results()

if results.empty:
    st.warning(
        "No analysis results found. Run the data pipeline first:\n\n"
        "```bash\n"
        "python -m src.data_fetcher\n"
        "python -m src.analyzer\n"
        "```"
    )
    st.stop()

# Quick metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Coins Tracked", len(results))
col2.metric("Avg Drop", f"{results['pct_change'].mean():.1f}%")
col3.metric("Biggest Loser", results.iloc[0]["symbol"].upper())
col4.metric("Worst Drop", f"{results['pct_change'].min():.1f}%")

st.markdown("---")
st.subheader("Quick Preview: Top 10 Biggest Drops")

top10 = results.head(10)
st.dataframe(
    top10[["coin_name", "symbol", "peak_price", "current_price", "pct_change"]].style.format({
        "peak_price": "${:.4f}",
        "current_price": "${:.4f}",
        "pct_change": "{:+.2f}%",
    }),
    width="stretch",
)

st.info("👈 Use the sidebar to navigate to detailed views: Top 50 rankings, "
        "individual coin details, and more.")
