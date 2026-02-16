"""Test fixtures for altcoin analyzer tests."""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def sample_coin_list() -> list[dict]:
    """Sample coin list as returned by get_top_altcoins."""
    return [
        {"id": "SOL", "symbol": "SOL", "name": "SOL"},
        {"id": "ADA", "symbol": "ADA", "name": "ADA"},
        {"id": "DOGE", "symbol": "DOGE", "name": "DOGE"},
        {"id": "DOT", "symbol": "DOT", "name": "DOT"},
        {"id": "AVAX", "symbol": "AVAX", "name": "AVAX"},
    ]


@pytest.fixture
def sample_ohlcv_response() -> list[list]:
    """Sample CCXT OHLCV response (list of [timestamp, open, high, low, close, volume])."""
    base_ts = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    day_ms = 86_400_000

    candles = []
    for i in range(60):
        ts = base_ts + i * day_ms
        if i <= 30:
            close_p = 100 + i * 5  # 100 -> 250
        else:
            close_p = 250 - (i - 30) * 3  # 250 -> 160

        open_p = close_p - 1
        high_p = close_p + 2
        low_p = close_p - 3
        volume = close_p * 500_000

        candles.append([ts, open_p, high_p, low_p, close_p, volume])

    return candles


@pytest.fixture
def sample_tickers_response() -> dict:
    """Sample CCXT fetch_tickers response."""
    return {
        "BTC/USDT": {
            "symbol": "BTC/USDT",
            "quoteVolume": 10_000_000_000,
        },
        "ETH/USDT": {
            "symbol": "ETH/USDT",
            "quoteVolume": 5_000_000_000,
        },
        "SOL/USDT": {
            "symbol": "SOL/USDT",
            "quoteVolume": 2_000_000_000,
        },
        "ADA/USDT": {
            "symbol": "ADA/USDT",
            "quoteVolume": 1_000_000_000,
        },
        "DOGE/USDT": {
            "symbol": "DOGE/USDT",
            "quoteVolume": 800_000_000,
        },
        "DOT/USDT": {
            "symbol": "DOT/USDT",
            "quoteVolume": 500_000_000,
        },
        "AVAX/USDT": {
            "symbol": "AVAX/USDT",
            "quoteVolume": 400_000_000,
        },
        "USDC/USDT": {
            "symbol": "USDC/USDT",
            "quoteVolume": 3_000_000_000,
        },
        "SOL/BTC": {
            "symbol": "SOL/BTC",
            "quoteVolume": 100_000,
        },
    }


@pytest.fixture
def sample_prices_df() -> pd.DataFrame:
    """Sample price DataFrame with multiple coins."""
    rows = []
    base_date = datetime(2025, 1, 1)

    coins = [
        ("coin-a", "Coin A", "ca", 100, 250, 80),   # peak 250, current 80
        ("coin-b", "Coin B", "cb", 50, 200, 50),     # peak 200, current 50
        ("coin-c", "Coin C", "cc", 10, 50, 45),      # peak 50, current 45
        ("coin-d", "Coin D", "cd", 1, 5, 0.5),       # peak 5, current 0.5
    ]

    for coin_id, name, symbol, start, peak, end in coins:
        for day in range(60):
            date = base_date + timedelta(days=day)
            # Simple price trajectory: rise to peak at day 20, then decline
            if day <= 20:
                price = start + (peak - start) * (day / 20)
            else:
                price = peak - (peak - end) * ((day - 20) / 40)

            rows.append({
                "date": date,
                "coin_id": coin_id,
                "coin_name": name,
                "symbol": symbol,
                "price": round(price, 4),
                "market_cap": round(price * 1_000_000, 2),
                "volume": round(price * 500_000, 2),
                "high": round(price * 1.02, 4),
                "low": round(price * 0.98, 4),
            })

    return pd.DataFrame(rows)


@pytest.fixture
def sample_prices_csv(tmp_path: Path, sample_prices_df: pd.DataFrame) -> Path:
    """Write sample prices to a CSV file."""
    filepath = tmp_path / "altcoin_prices.csv"
    sample_prices_df.to_csv(filepath, index=False)
    return filepath


@pytest.fixture
def sample_sqlite_db(tmp_path: Path, sample_prices_df: pd.DataFrame) -> Path:
    """Create a sample SQLite database with price data."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    sample_prices_df.to_sql("prices", conn, index=False)
    conn.close()
    return db_path


@pytest.fixture
def empty_prices_df() -> pd.DataFrame:
    """Empty DataFrame with correct columns."""
    return pd.DataFrame(columns=[
        "date", "coin_id", "coin_name", "symbol", "price",
        "market_cap", "volume", "high", "low",
    ])


@pytest.fixture
def single_record_df() -> pd.DataFrame:
    """DataFrame with a single record."""
    return pd.DataFrame([{
        "date": datetime(2025, 3, 1),
        "coin_id": "test-coin",
        "coin_name": "Test Coin",
        "symbol": "tc",
        "price": 100.0,
        "market_cap": 100_000_000,
        "volume": 50_000_000,
        "high": 102.0,
        "low": 98.0,
    }])
