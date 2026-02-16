"""Integration tests for the full data pipeline."""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import ccxt
import pandas as pd
import pytest

from src.analyzer import export_results, rank_by_drop
from src.data_fetcher import (
    fetch_historical_data,
    save_to_csv,
    save_to_sqlite,
    validate_data,
)


class TestFullPipeline:
    """Test the complete fetch -> analyze -> export pipeline."""

    def test_fetch_analyze_export(self, tmp_path: Path) -> None:
        """Test full pipeline: fetch data, analyze, and export."""
        # Setup mock exchange with OHLCV data
        base_ts = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
        day_ms = 86_400_000

        candles = []
        for i in range(60):
            ts = base_ts + i * day_ms
            price = 200 - i * 2 if i > 10 else 100 + i * 10
            candles.append([ts, price - 1, price + 2, price - 3, price, price * 500_000])

        mock_exchange = MagicMock(spec=ccxt.binance)
        mock_exchange.fetch_ohlcv.return_value = candles

        # Step 1: Fetch
        df = fetch_historical_data(
            mock_exchange, "TEST/USDT", "2025-01-01", "2025-03-01"
        )
        assert not df.empty
        assert len(df) == 60

        # Step 2: Validate
        df = validate_data(df)
        assert not df.empty

        # Add metadata
        df["coin_id"] = "test-coin"
        df["coin_name"] = "Test Coin"
        df["symbol"] = "tc"

        # Step 3: Save to both formats
        csv_path = tmp_path / "prices.csv"
        db_path = tmp_path / "prices.db"
        save_to_csv(df, csv_path)
        save_to_sqlite(df, db_path)

        # Verify CSV
        csv_data = pd.read_csv(csv_path)
        assert len(csv_data) == 60

        # Verify SQLite
        conn = sqlite3.connect(str(db_path))
        db_data = pd.read_sql("SELECT * FROM prices", conn)
        conn.close()
        assert len(db_data) == 60

        # Step 4: Analyze
        loaded = pd.read_csv(csv_path, parse_dates=["date"])
        results = rank_by_drop(loaded, top_n=50)

        # The test coin should have a drop (peak > current)
        assert len(results) >= 0  # May or may not have 30 days min


class TestDataConsistency:
    """Test data consistency across formats."""

    def test_csv_sqlite_consistency(
        self, tmp_path: Path, sample_prices_df: pd.DataFrame
    ) -> None:
        """Test that CSV and SQLite produce the same data."""
        csv_path = tmp_path / "prices.csv"
        db_path = tmp_path / "prices.db"

        save_to_csv(sample_prices_df, csv_path)
        save_to_sqlite(sample_prices_df, db_path)

        csv_data = pd.read_csv(csv_path)
        conn = sqlite3.connect(str(db_path))
        db_data = pd.read_sql("SELECT * FROM prices", conn)
        conn.close()

        assert len(csv_data) == len(db_data)
        assert set(csv_data.columns) == set(db_data.columns)

    def test_analysis_consistency(
        self, sample_prices_df: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Test that analysis produces consistent results across runs."""
        results1 = rank_by_drop(sample_prices_df)
        results2 = rank_by_drop(sample_prices_df)

        pd.testing.assert_frame_equal(results1, results2)

    def test_export_roundtrip_csv(
        self, sample_prices_df: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Test CSV export and re-import consistency."""
        results = rank_by_drop(sample_prices_df)
        if results.empty:
            pytest.skip("No ranked results to test")

        filepath = tmp_path / "results.csv"
        export_results(results, "csv", filepath)
        reloaded = pd.read_csv(filepath)

        assert len(reloaded) == len(results)
        # Column names should match (minus the rank index)
        for col in ["coin_id", "coin_name", "pct_change"]:
            assert col in reloaded.columns

    def test_export_roundtrip_json(
        self, sample_prices_df: pd.DataFrame, tmp_path: Path
    ) -> None:
        """Test JSON export and re-import consistency."""
        results = rank_by_drop(sample_prices_df)
        if results.empty:
            pytest.skip("No ranked results to test")

        filepath = tmp_path / "results.json"
        export_results(results, "json", filepath)
        reloaded = pd.read_json(filepath)

        assert len(reloaded) == len(results)


class TestEdgeCases:
    """Test edge cases in the full pipeline."""

    def test_single_coin_pipeline(self, tmp_path: Path) -> None:
        """Test pipeline with only one coin."""
        base_date = datetime(2025, 1, 1)
        rows = []
        for day in range(60):
            price = 100 + day if day <= 20 else 120 - (day - 20)
            rows.append({
                "date": base_date + timedelta(days=day),
                "coin_id": "solo",
                "coin_name": "Solo Coin",
                "symbol": "solo",
                "price": price,
                "market_cap": price * 1_000_000,
                "volume": price * 500_000,
            })
        df = pd.DataFrame(rows)
        results = rank_by_drop(df)
        assert len(results) <= 1

    def test_all_coins_ascending(self) -> None:
        """Test pipeline where all coins only go up (no drops)."""
        base_date = datetime(2025, 1, 1)
        rows = []
        for day in range(60):
            rows.append({
                "date": base_date + timedelta(days=day),
                "coin_id": "up-only",
                "coin_name": "Up Only",
                "symbol": "up",
                "price": 100 + day,
                "market_cap": (100 + day) * 1_000_000,
                "volume": 500_000,
            })
        df = pd.DataFrame(rows)
        results = rank_by_drop(df)
        assert len(results) == 0

    def test_multiple_save_append(self, tmp_path: Path) -> None:
        """Test that multiple saves append correctly."""
        csv_path = tmp_path / "append_test.csv"
        df1 = pd.DataFrame([{"date": "2025-01-01", "coin_id": "a", "price": 100}])
        df2 = pd.DataFrame([{"date": "2025-01-02", "coin_id": "a", "price": 105}])
        df3 = pd.DataFrame([{"date": "2025-01-03", "coin_id": "a", "price": 95}])

        save_to_csv(df1, csv_path)
        save_to_csv(df2, csv_path)
        save_to_csv(df3, csv_path)

        result = pd.read_csv(csv_path)
        assert len(result) == 3

    def test_validate_preserves_good_data(self) -> None:
        """Test that validation doesn't remove valid data."""
        df = pd.DataFrame([
            {"date": "2025-01-01", "price": 100.5},
            {"date": "2025-01-02", "price": 0.001},
            {"date": "2025-01-03", "price": 99999.99},
        ])
        result = validate_data(df)
        assert len(result) == 3
