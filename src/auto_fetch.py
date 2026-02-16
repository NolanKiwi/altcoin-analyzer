"""Ensure analysis results exist, running the analyzer if needed.

Used by Streamlit pages to ensure data is available on first load.
If price data exists but analysis results don't, runs the analyzer.
"""

import logging

import streamlit as st

from src.config import PRICES_CSV, RESULTS_CSV

logger = logging.getLogger(__name__)


def ensure_data() -> bool:
    """Run analysis if price data exists but results don't.

    Returns:
        True if data is available, False otherwise.
    """
    if RESULTS_CSV.exists() and RESULTS_CSV.stat().st_size > 0:
        return True

    if not PRICES_CSV.exists() or PRICES_CSV.stat().st_size == 0:
        return False

    try:
        with st.spinner("Running analysis..."):
            from src.analyzer import run as run_analysis
            run_analysis()

        st.cache_data.clear()
        st.rerun()

    except Exception as e:
        logger.error("Analysis failed: %s", e)
        st.error(f"Failed to run analysis: {e}")
        return False

    return True
