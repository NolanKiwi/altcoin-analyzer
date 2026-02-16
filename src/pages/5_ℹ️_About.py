"""About page with project information and methodology."""

import streamlit as st

st.set_page_config(page_title="About - Altcoin Analyzer", page_icon="ℹ️", layout="wide")

st.title("ℹ️ About")

st.markdown("""
## Altcoin Price Drop Analyzer

This dashboard tracks the biggest price drops among top altcoins (excluding Bitcoin
and Ethereum) from their 2025 peak prices to the present day.

### Data Source

All price data is sourced from a crypto exchange (default: Bybit) via the
[CCXT](https://github.com/ccxt/ccxt) library. The exchange provides:

- Real-time and historical prices
- Full OHLCV (Open, High, Low, Close, Volume) candle data
- No API key required for public market data

### Methodology

1. **Data Collection**: We fetch daily OHLCV data for the top 200 altcoins by USDT
   trading volume from January 1, 2025 to the present day.

2. **Peak Detection**: For each coin, we identify the highest price recorded during
   the 2025 period.

3. **Drop Calculation**: The percentage drop is calculated as:
   ```
   drop_% = ((current_price - peak_price) / peak_price) × 100
   ```

4. **Ranking**: Coins are ranked by the magnitude of their price drop, with the
   biggest losers at the top.

5. **Filtering**: We exclude:
   - Bitcoin (BTC) and Ethereum (ETH)
   - Stablecoins (USDT, USDC, DAI, etc.)
   - Coins with fewer than 30 days of data
   - Coins with zero or invalid prices

### Statistics

- **Volatility**: Calculated as the standard deviation of prices over the last 30 days
- **Average Volume**: Mean daily trading volume over the last 30 days

### Limitations

- Data accuracy depends on Binance's reporting
- Market cap data is not available from Binance OHLCV endpoints
- Some newly listed or delisted coins may have incomplete data
- Coins are ranked by trading volume rather than market cap

### Disclaimer

**This tool is for informational and educational purposes only.** It does not
constitute financial advice. Cryptocurrency investments carry significant risk.
Always do your own research (DYOR) before making investment decisions. Past price
performance does not guarantee future results.

---

### Technologies Used

- **Python 3.10+** - Core programming language
- **Pandas & NumPy** - Data analysis and manipulation
- **Streamlit** - Web dashboard framework
- **Plotly** - Interactive charting
- **SQLite** - Local data storage
- **CCXT / Binance** - Cryptocurrency data source

### License

This project is open source under the MIT License.
""")
