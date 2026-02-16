"""Main Streamlit dashboard entry point for the Altcoin Price Drop Analyzer.

Run with: streamlit run src/dashboard.py
"""

import sys
from pathlib import Path

import streamlit as st

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

st.set_page_config(
    page_title="Altcoin Analyzer",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar
st.sidebar.title("📉 Altcoin Analyzer")
st.sidebar.markdown("---")

if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("Data source: Binance via CCXT")

# Redirect to Home page
home = st.Page("pages/1_🏠_Home.py", title="Home", icon="🏠", default=True)
st.switch_page(home)
