"""Auto-fetch data from Binance when no local data exists.

Used by Streamlit pages to ensure data is available on first load
(e.g., when deployed to Streamlit Cloud).
"""

import logging

import streamlit as st

from src.config import PRICES_CSV, RESULTS_CSV

logger = logging.getLogger(__name__)

DEFAULT_NUM_COINS = 200


def ensure_data(num_coins: int = DEFAULT_NUM_COINS) -> bool:
    """Fetch data and run analysis if results don't exist yet.

    Shows a spinner in the Streamlit UI while fetching.

    Args:
        num_coins: Number of top altcoins to fetch.

    Returns:
        True if data is available, False if fetch failed.
    """
    if RESULTS_CSV.exists() and RESULTS_CSV.stat().st_size > 0:
        return True

    needs_fetch = not PRICES_CSV.exists() or PRICES_CSV.stat().st_size == 0
    needs_analysis = not RESULTS_CSV.exists() or RESULTS_CSV.stat().st_size == 0

    if not needs_fetch and not needs_analysis:
        return True

    st.info("No data found. Fetching from Binance — this may take a minute...")

    try:
        if needs_fetch:
            with st.spinner(f"Fetching OHLCV data for top {num_coins} altcoins..."):
                from src.data_fetcher import main as fetch_main
                fetch_main(num_coins=num_coins)

        if needs_analysis or needs_fetch:
            with st.spinner("Running analysis..."):
                from src.analyzer import run as run_analysis
                run_analysis()

        st.cache_data.clear()
        st.rerun()

    except Exception as e:
        logger.error("Auto-fetch failed: %s", e)
        st.error(f"Failed to fetch data: {e}")
        return False

    return True
