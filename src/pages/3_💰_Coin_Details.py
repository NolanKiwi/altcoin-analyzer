"""Individual coin detail view with price charts and statistics."""

import sys
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.auto_fetch import ensure_data
from src.config import CACHE_TTL, PRICES_CSV, RESULTS_CSV

st.set_page_config(page_title="Coin Details - Altcoin Analyzer", page_icon="💰",
                   layout="wide")


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


st.title("💰 Coin Details")

if not ensure_data():
    st.stop()

results = load_results()
prices = load_prices()

if results.empty:
    st.warning("No data available. Run the data pipeline first.")
    st.stop()

# Coin selector
coin_options = results["coin_id"].tolist()
coin_names = {row["coin_id"]: f"{row['coin_name']} ({row['symbol'].upper()})"
              for _, row in results.iterrows()}

selected = st.selectbox(
    "Select a coin",
    coin_options,
    format_func=lambda x: coin_names.get(x, x),
)

if not selected:
    st.stop()

coin_info = results[results["coin_id"] == selected].iloc[0]

# Header with metrics
st.markdown(f"## {coin_info['coin_name']} ({coin_info['symbol'].upper()})")

col1, col2, col3, col4 = st.columns(4)
col1.metric("2025 Peak Price", f"${coin_info['peak_price']:.4f}")
col2.metric("Current Price", f"${coin_info['current_price']:.4f}")
col3.metric("Drop from Peak", f"{coin_info['pct_change']:+.2f}%")
col4.metric("Market Cap", f"${coin_info.get('market_cap', 0):,.0f}")

st.markdown("---")

# Price history chart
if not prices.empty:
    coin_prices = prices[prices["coin_id"] == selected].sort_values("date").copy()

    if not coin_prices.empty:
        # Line chart with peak marker
        st.subheader("Price History (2025 - Present)")

        peak_date = pd.to_datetime(coin_info["peak_date"])
        peak_price = coin_info["peak_price"]

        fig_line = px.line(
            coin_prices,
            x="date",
            y="price",
            labels={"price": "Price (USD)", "date": "Date"},
        )
        fig_line.add_trace(go.Scatter(
            x=[peak_date],
            y=[peak_price],
            mode="markers+text",
            marker=dict(size=12, color="red", symbol="star"),
            text=[f"Peak: ${peak_price:.4f}"],
            textposition="top center",
            name="2025 Peak",
            showlegend=True,
        ))
        fig_line.update_layout(height=450, hovermode="x unified")
        st.plotly_chart(fig_line, width="stretch")

        # Last 30 days candlestick
        st.subheader("Last 30 Days")
        last_30 = coin_prices.tail(30)

        if len(last_30) >= 2:
            fig_candle = go.Figure(data=[go.Candlestick(
                x=last_30["date"],
                open=last_30["price"].shift(1).fillna(last_30["price"]),
                high=last_30.get("high", last_30["price"]),
                low=last_30.get("low", last_30["price"]),
                close=last_30["price"],
                name="Price",
            )])
            fig_candle.update_layout(height=400, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_candle, width="stretch")

        # Volume chart
        if "volume" in coin_prices.columns:
            st.subheader("Trading Volume")
            fig_vol = px.bar(
                coin_prices,
                x="date",
                y="volume",
                labels={"volume": "Volume (USD)", "date": "Date"},
                color_discrete_sequence=["#667eea"],
            )
            fig_vol.update_layout(height=300)
            st.plotly_chart(fig_vol, width="stretch")

        # Statistics table
        st.subheader("Statistics")
        stats_col1, stats_col2 = st.columns(2)

        with stats_col1:
            volatility = coin_prices.tail(30)["price"].std()
            avg_price = coin_prices["price"].mean()
            min_price = coin_prices["price"].min()
            max_price = coin_prices["price"].max()

            st.markdown(f"""
            | Metric | Value |
            |--------|-------|
            | 30-Day Volatility | ${volatility:.6f} |
            | Average Price | ${avg_price:.6f} |
            | Minimum Price | ${min_price:.6f} |
            | Maximum Price | ${max_price:.6f} |
            | Data Points | {len(coin_prices)} |
            """)

        with stats_col2:
            if "volume" in coin_prices.columns:
                avg_vol = coin_prices.tail(30)["volume"].mean()
                max_vol = coin_prices["volume"].max()
            else:
                avg_vol = 0
                max_vol = 0

            st.markdown(f"""
            | Metric | Value |
            |--------|-------|
            | 30-Day Avg Volume | ${avg_vol:,.0f} |
            | Max Volume | ${max_vol:,.0f} |
            | Peak Date | {coin_info['peak_date']} |
            | Current Date | {coin_info.get('current_date', 'N/A')} |
            | Market Cap | ${coin_info.get('market_cap', 0):,.0f} |
            """)

        # Compare with market average
        st.markdown("---")
        st.subheader("Compare with Market Average")
        avg_drop = results["pct_change"].mean()
        coin_drop = coin_info["pct_change"]

        comparison_df = pd.DataFrame({
            "Category": ["This Coin", "Market Average"],
            "Drop %": [coin_drop, avg_drop],
        })
        fig_compare = px.bar(
            comparison_df,
            x="Category",
            y="Drop %",
            color="Category",
            color_discrete_map={"This Coin": "#ff4444", "Market Average": "#667eea"},
            text="Drop %",
        )
        fig_compare.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_compare.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig_compare, width="stretch")
    else:
        st.info("No price history available for this coin.")
else:
    st.info("Price history data not loaded. Run the data fetcher first.")
