"""Fetch altcoin price data via CCXT.

This module handles all data collection from a crypto exchange, including:
- Discovering top altcoins by USDT trading volume
- Downloading historical OHLCV data
- Saving data to both CSV and SQLite formats
- Resumable downloads with progress tracking
"""

import argparse
import csv
import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt
import pandas as pd
from tqdm import tqdm

from src.config import (
    DATA_DIR,
    DATABASE_PATH,
    EXCHANGE_ID,
    EXCLUDE_SYMBOLS,
    LOG_DIR,
    MAX_RETRIES,
    PRICES_CSV,
    QUOTE_CURRENCY,
    RATE_LIMIT_DELAY,
    RETRY_BACKOFF_BASE,
    START_DATE,
)

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure logging to both console and file."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "fetcher.log"

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    # Avoid duplicate handlers on repeated calls
    if not root_logger.handlers:
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)


def get_top_altcoins(exchange: ccxt.Exchange, limit: int = 200) -> list[dict[str, str]]:
    """Fetch top altcoins by USDT trading volume, excluding BTC/ETH/stablecoins.

    Args:
        exchange: CCXT exchange instance.
        limit: Number of altcoins to return.

    Returns:
        List of dicts with keys: id, symbol, name.
    """
    logger.info("Fetching all tickers to find top %d altcoins by volume...", limit)
    tickers = exchange.fetch_tickers()

    # Filter to USDT pairs and exclude unwanted symbols
    suffix = f"/{QUOTE_CURRENCY}"
    candidates = []
    for ticker_symbol, ticker in tickers.items():
        if not ticker_symbol.endswith(suffix):
            continue
        base = ticker_symbol.split("/")[0]
        if base in EXCLUDE_SYMBOLS:
            continue
        quote_volume = ticker.get("quoteVolume") or 0
        candidates.append((base, quote_volume))

    # Sort by quote volume descending
    candidates.sort(key=lambda x: x[1], reverse=True)

    coins = []
    for base, _ in candidates[:limit]:
        coins.append({
            "id": base,
            "symbol": base,
            "name": base,
        })

    logger.info("Found %d altcoins", len(coins))
    return coins


def fetch_historical_data(
    exchange: ccxt.Exchange,
    symbol: str,
    start_date: str = START_DATE,
    end_date: str | None = None,
) -> pd.DataFrame:
    """Fetch daily OHLCV data for a coin from Binance.

    Args:
        exchange: CCXT exchange instance.
        symbol: Trading pair symbol (e.g., "SOL/USDT").
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format (defaults to today).

    Returns:
        DataFrame with columns: date, price, market_cap, volume, high, low.
    """
    from_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    since_ms = int(from_dt.timestamp() * 1000)

    if end_date:
        to_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        to_dt = datetime.now(timezone.utc)
    end_ms = int(to_dt.timestamp() * 1000)

    all_candles: list[list] = []
    current_since = since_ms
    candle_limit = 500  # Binance max per request

    while current_since < end_ms:
        for attempt in range(MAX_RETRIES):
            try:
                candles = exchange.fetch_ohlcv(
                    symbol, "1d", since=current_since, limit=candle_limit
                )
                break
            except (ccxt.NetworkError, ccxt.ExchangeNotAvailable) as e:
                wait = RETRY_BACKOFF_BASE ** attempt * 5
                logger.warning(
                    "CCXT error fetching %s: %s. Retrying in %ds (attempt %d/%d)",
                    symbol, e, wait, attempt + 1, MAX_RETRIES,
                )
                time.sleep(wait)
        else:
            raise RuntimeError(
                f"Failed after {MAX_RETRIES} retries fetching {symbol}"
            )

        if not candles:
            break

        all_candles.extend(candles)

        # Move past the last candle we received
        last_ts = candles[-1][0]
        if last_ts <= current_since:
            break
        current_since = last_ts + 86_400_000  # next day

        time.sleep(RATE_LIMIT_DELAY)

    if not all_candles:
        return pd.DataFrame()

    rows = []
    seen_dates: set[str] = set()
    start_str = start_date

    for candle in all_candles:
        ts_ms, open_p, high_p, low_p, close_p, volume = candle
        d = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        if d in seen_dates or d < start_str:
            continue
        end_str = end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if d > end_str:
            continue
        seen_dates.add(d)
        rows.append({
            "date": d,
            "price": close_p,
            "market_cap": 0,
            "volume": volume,
            "high": high_p,
            "low": low_p,
        })

    return pd.DataFrame(rows)


def save_to_csv(df: pd.DataFrame, filepath: Path | str | None = None) -> None:
    """Save DataFrame to CSV file, appending if file exists.

    Args:
        df: Data to save.
        filepath: Target CSV path (defaults to PRICES_CSV).
    """
    filepath = Path(filepath) if filepath else PRICES_CSV
    filepath.parent.mkdir(parents=True, exist_ok=True)

    write_header = not filepath.exists() or filepath.stat().st_size == 0
    df.to_csv(filepath, mode="a", header=write_header, index=False)
    logger.info("Saved %d rows to %s", len(df), filepath)


def save_to_sqlite(df: pd.DataFrame, db_path: Path | str | None = None) -> None:
    """Save DataFrame to SQLite database.

    Args:
        df: Data to save.
        db_path: Database file path (defaults to DATABASE_PATH).
    """
    db_path = Path(db_path) if db_path else DATABASE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        df.to_sql("prices", conn, if_exists="append", index=False)
        # Create index for faster queries
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_prices_coin_date "
            "ON prices(coin_id, date)"
        )
        conn.commit()
        logger.info("Saved %d rows to SQLite: %s", len(df), db_path)
    finally:
        conn.close()


def load_existing_data(filepath: Path | str | None = None) -> dict[str, set[str]]:
    """Load already-fetched (coin_id, date) pairs for resumable downloads.

    Args:
        filepath: CSV file to check (defaults to PRICES_CSV).

    Returns:
        Dict mapping coin_id to set of date strings.
    """
    filepath = Path(filepath) if filepath else PRICES_CSV
    fetched: dict[str, set[str]] = {}
    if not filepath.exists():
        return fetched

    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fetched.setdefault(row["coin_id"], set()).add(row["date"])

    return fetched


def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and clean price data.

    Args:
        df: Raw price data.

    Returns:
        Cleaned DataFrame with invalid rows removed.
    """
    initial_len = len(df)

    # Remove rows with zero or negative prices
    df = df[df["price"] > 0].copy()

    # Remove rows with missing dates
    df = df.dropna(subset=["date"])

    # Remove duplicate dates
    df = df.drop_duplicates(subset=["date"])

    removed = initial_len - len(df)
    if removed > 0:
        logger.info("Validation removed %d invalid rows", removed)

    return df


def main(update: bool = False, coins: list[str] | None = None,
         num_coins: int = 200) -> None:
    """Main fetch pipeline.

    Args:
        update: If True, only fetch new data since last download.
        coins: Optional list of specific coin symbols to fetch (e.g., ["SOL", "ADA"]).
        num_coins: Number of top altcoins to fetch (default 200).
    """
    setup_logging()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    exchange_class = getattr(ccxt, EXCHANGE_ID)
    exchange = exchange_class({"enableRateLimit": True})

    logger.info("Starting data fetch pipeline (%s via CCXT)", EXCHANGE_ID)
    logger.info("Date range: %s to now", START_DATE)

    if coins:
        coin_list = [{"id": c.upper(), "symbol": c.upper(), "name": c.upper()}
                     for c in coins]
        logger.info("Fetching %d specified coins", len(coin_list))
    else:
        logger.info("Fetching top %d altcoins by volume...", num_coins)
        coin_list = get_top_altcoins(exchange, num_coins)
        logger.info("Got %d altcoins", len(coin_list))

    existing = load_existing_data() if update else {}

    all_rows: list[pd.DataFrame] = []

    for coin in tqdm(coin_list, desc="Fetching coins"):
        cid = coin["id"]
        pair = f"{cid}/{QUOTE_CURRENCY}"
        already = existing.get(cid, set())

        try:
            df = fetch_historical_data(exchange, pair)
        except Exception as e:
            logger.error("Failed to fetch %s: %s", pair, e)
            continue

        if df.empty:
            logger.warning("No data returned for %s", pair)
            continue

        df = validate_data(df)

        # Filter out already-fetched dates if updating
        if already:
            df = df[~df["date"].isin(already)]

        if df.empty:
            continue

        # Add coin metadata
        df["coin_id"] = cid
        df["coin_name"] = coin["name"]
        df["symbol"] = coin["symbol"]

        # Reorder columns
        df = df[["date", "coin_id", "coin_name", "symbol", "price",
                 "market_cap", "volume", "high", "low"]]

        all_rows.append(df)
        time.sleep(RATE_LIMIT_DELAY)

    if all_rows:
        combined = pd.concat(all_rows, ignore_index=True)
        save_to_csv(combined)
        save_to_sqlite(combined)
        logger.info("Pipeline complete. Total new rows: %d", len(combined))
    else:
        logger.info("No new data to save")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch altcoin price data")
    parser.add_argument("--update", action="store_true",
                        help="Only fetch new data since last download")
    parser.add_argument("--coins", nargs="+",
                        help="Specific coin symbols to fetch (e.g., SOL ADA)")
    parser.add_argument("--num-coins", type=int, default=200,
                        help="Number of top altcoins to fetch")
    args = parser.parse_args()
    main(update=args.update, coins=args.coins, num_coins=args.num_coins)
