"""Analyze altcoin price data: compute peak-to-current drops and statistics.

This module provides comprehensive analysis of altcoin price data including:
- Finding 2025 peak prices for each coin
- Calculating percentage drops from peak to current
- Ranking coins by biggest drops
- Computing statistical measures (volatility, volume averages)
- Exporting results to CSV and JSON
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import (
    DATABASE_PATH,
    DATA_DIR,
    MIN_DATA_DAYS,
    PRICES_CSV,
    RESULTS_CSV,
    TOP_N_RANKING,
)

logger = logging.getLogger(__name__)


def load_data(source: str = "csv") -> pd.DataFrame:
    """Load price data from CSV or SQLite.

    Args:
        source: Data source, either 'csv' or 'sqlite'.

    Returns:
        DataFrame with price data sorted by coin_id and date.

    Raises:
        FileNotFoundError: If the data source does not exist.
    """
    if source == "sqlite" and DATABASE_PATH.exists():
        conn = sqlite3.connect(str(DATABASE_PATH))
        try:
            df = pd.read_sql("SELECT * FROM prices", conn, parse_dates=["date"])
        finally:
            conn.close()
    elif PRICES_CSV.exists():
        df = pd.read_csv(PRICES_CSV, parse_dates=["date"])
    else:
        raise FileNotFoundError(
            f"No data found. Run the data fetcher first. "
            f"Checked: {PRICES_CSV}, {DATABASE_PATH}"
        )

    df.sort_values(["coin_id", "date"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    logger.info("Loaded %d rows for %d coins", len(df), df["coin_id"].nunique())
    return df


def find_2025_peak(df: pd.DataFrame, coin_id: str) -> dict[str, Any]:
    """Find the 2025 peak price for a given coin.

    Args:
        df: Full price DataFrame.
        coin_id: CoinGecko coin identifier.

    Returns:
        Dict with 'price' and 'date' of the peak, or empty dict if no data.
    """
    coin_data = df[df["coin_id"] == coin_id]
    if coin_data.empty:
        return {}

    peak_idx = coin_data["price"].idxmax()
    peak_row = coin_data.loc[peak_idx]
    return {
        "price": float(peak_row["price"]),
        "date": peak_row["date"].strftime("%Y-%m-%d")
        if hasattr(peak_row["date"], "strftime")
        else str(peak_row["date"])[:10],
    }


def get_current_price(df: pd.DataFrame, coin_id: str) -> float:
    """Get the most recent price for a coin.

    Args:
        df: Full price DataFrame.
        coin_id: CoinGecko coin identifier.

    Returns:
        Latest price as float, or 0.0 if no data.
    """
    coin_data = df[df["coin_id"] == coin_id]
    if coin_data.empty:
        return 0.0
    latest = coin_data.loc[coin_data["date"].idxmax()]
    return float(latest["price"])


def calculate_drop_percentage(peak_price: float, current_price: float) -> float:
    """Calculate percentage drop from peak to current.

    Args:
        peak_price: The peak (highest) price.
        current_price: The current (latest) price.

    Returns:
        Percentage change (negative means drop).
    """
    if peak_price <= 0:
        return 0.0
    return round(((current_price - peak_price) / peak_price) * 100, 2)


def get_coin_stats(df: pd.DataFrame, coin_id: str) -> dict[str, Any]:
    """Compute comprehensive statistics for a coin.

    Args:
        df: Full price DataFrame.
        coin_id: CoinGecko coin identifier.

    Returns:
        Dict with peak info, current price, drop %, volatility,
        avg volume, and market cap change.
    """
    coin_data = df[df["coin_id"] == coin_id].copy()
    if coin_data.empty:
        return {}

    coin_data = coin_data.sort_values("date")

    peak_idx = coin_data["price"].idxmax()
    peak_row = coin_data.loc[peak_idx]
    latest_row = coin_data.iloc[-1]

    peak_price = float(peak_row["price"])
    current_price = float(latest_row["price"])
    drop_pct = calculate_drop_percentage(peak_price, current_price)

    # 30-day statistics
    last_30 = coin_data.tail(30)
    volatility = float(last_30["price"].std()) if len(last_30) >= 2 else 0.0

    avg_volume = float(last_30["volume"].mean()) if "volume" in last_30.columns else 0.0

    # Market cap change
    first_mc = float(coin_data.iloc[0]["market_cap"]) if "market_cap" in coin_data.columns else 0
    latest_mc = float(latest_row["market_cap"]) if "market_cap" in coin_data.columns else 0
    mc_change = 0.0
    if first_mc > 0:
        mc_change = round(((latest_mc - first_mc) / first_mc) * 100, 2)

    return {
        "coin_id": coin_id,
        "coin_name": str(peak_row.get("coin_name", coin_id)),
        "symbol": str(peak_row.get("symbol", "")),
        "peak_price": peak_price,
        "peak_date": peak_row["date"].strftime("%Y-%m-%d")
        if hasattr(peak_row["date"], "strftime")
        else str(peak_row["date"])[:10],
        "current_price": current_price,
        "current_date": latest_row["date"].strftime("%Y-%m-%d")
        if hasattr(latest_row["date"], "strftime")
        else str(latest_row["date"])[:10],
        "drop_percentage": drop_pct,
        "volatility_30d": round(volatility, 6),
        "avg_volume_30d": round(avg_volume, 2),
        "market_cap": latest_mc,
        "market_cap_change_pct": mc_change,
        "data_points": len(coin_data),
    }


def rank_by_drop(df: pd.DataFrame, top_n: int = TOP_N_RANKING) -> pd.DataFrame:
    """Rank coins by biggest price drop from 2025 peak.

    Args:
        df: Full price DataFrame.
        top_n: Number of top losers to return.

    Returns:
        DataFrame ranked by drop percentage (biggest drops first).
    """
    results = []

    for coin_id in df["coin_id"].unique():
        coin_data = df[df["coin_id"] == coin_id]

        # Skip coins with insufficient data
        if len(coin_data) < MIN_DATA_DAYS:
            logger.debug("Skipping %s: only %d data points", coin_id, len(coin_data))
            continue

        peak_row = coin_data.loc[coin_data["price"].idxmax()]
        latest_row = coin_data.loc[coin_data["date"].idxmax()]

        peak_price = float(peak_row["price"])
        current_price = float(latest_row["price"])

        # Skip zero-price coins
        if peak_price <= 0 or current_price <= 0:
            continue

        pct_drop = calculate_drop_percentage(peak_price, current_price)

        # Only include coins that have actually dropped
        if pct_drop >= 0:
            continue

        results.append({
            "coin_id": coin_id,
            "coin_name": str(peak_row.get("coin_name", coin_id)),
            "symbol": str(peak_row.get("symbol", "")),
            "peak_price": peak_price,
            "peak_date": peak_row["date"].strftime("%Y-%m-%d")
            if hasattr(peak_row["date"], "strftime")
            else str(peak_row["date"])[:10],
            "current_price": current_price,
            "current_date": latest_row["date"].strftime("%Y-%m-%d")
            if hasattr(latest_row["date"], "strftime")
            else str(latest_row["date"])[:10],
            "pct_change": pct_drop,
            "market_cap": float(latest_row.get("market_cap", 0)),
            "volume": float(latest_row.get("volume", 0)),
        })

    results_df = pd.DataFrame(results)
    if results_df.empty:
        return results_df

    results_df.sort_values("pct_change", ascending=True, inplace=True)
    results_df = results_df.head(top_n)
    results_df.reset_index(drop=True, inplace=True)
    results_df.index += 1
    results_df.index.name = "rank"
    return results_df


def generate_summary(results_df: pd.DataFrame) -> dict[str, Any]:
    """Generate summary statistics from the ranked results.

    Args:
        results_df: Ranked results from rank_by_drop().

    Returns:
        Dict with summary statistics.
    """
    if results_df.empty:
        return {"total_coins": 0}

    return {
        "total_coins": len(results_df),
        "avg_drop_pct": round(float(results_df["pct_change"].mean()), 2),
        "median_drop_pct": round(float(results_df["pct_change"].median()), 2),
        "worst_drop_pct": round(float(results_df["pct_change"].min()), 2),
        "best_drop_pct": round(float(results_df["pct_change"].max()), 2),
        "total_market_cap": round(float(results_df["market_cap"].sum()), 2),
        "biggest_loser": str(results_df.iloc[0]["coin_name"]),
        "biggest_loser_drop": round(float(results_df.iloc[0]["pct_change"]), 2),
    }


def export_results(
    results_df: pd.DataFrame,
    fmt: str = "csv",
    filepath: Path | str | None = None,
) -> Path:
    """Export analysis results to file.

    Args:
        results_df: Results DataFrame.
        fmt: Export format ('csv' or 'json').
        filepath: Output path (auto-generated if None).

    Returns:
        Path to the exported file.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if filepath is None:
        filepath = RESULTS_CSV if fmt == "csv" else DATA_DIR / "analysis_results.json"
    filepath = Path(filepath)

    if fmt == "json":
        results_df.to_json(filepath, orient="records", indent=2)
    else:
        results_df.to_csv(filepath)

    logger.info("Exported results to %s", filepath)
    return filepath


def run() -> pd.DataFrame:
    """Main analysis pipeline: load data, compute drops, save results.

    Returns:
        DataFrame with ranked results.
    """
    logger.info("Starting analysis pipeline")

    df = load_data()
    logger.info("Loaded %d rows for %d coins",
                len(df), df["coin_id"].nunique())

    results = rank_by_drop(df)
    logger.info("Ranked %d coins by drop percentage", len(results))

    if not results.empty:
        export_results(results, "csv")
        export_results(results, "json")

        summary = generate_summary(results)
        logger.info("Summary: %s", summary)

        print(f"\nTop {len(results)} biggest drops from 2025 peak:")
        for rank, row in results.head(20).iterrows():
            print(f"  {rank:>3d}. {row['symbol'].upper():>8s}  {row['pct_change']:+7.1f}%  "
                  f"peak ${row['peak_price']:.4f} -> now ${row['current_price']:.4f}")
    else:
        logger.warning("No coins with price drops found")

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
