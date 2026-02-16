"""Unit tests for data_fetcher module."""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import ccxt
import pandas as pd
import pytest

from src.data_fetcher import (
    fetch_historical_data,
    get_top_altcoins,
    load_existing_data,
    save_to_csv,
    save_to_sqlite,
    validate_data,
)


@pytest.fixture
def mock_exchange(sample_tickers_response, sample_ohlcv_response):
    """Create a mock CCXT exchange."""
    exchange = MagicMock(spec=ccxt.binance)
    exchange.fetch_tickers.return_value = sample_tickers_response
    exchange.fetch_ohlcv.return_value = sample_ohlcv_response
    return exchange


class TestGetTopAltcoins:
    """Tests for get_top_altcoins function."""

    def test_fetches_correct_number(self, mock_exchange) -> None:
        """Test that we get the requested number of altcoins."""
        coins = get_top_altcoins(mock_exchange, limit=3)

        assert len(coins) == 3
        assert all("id" in c for c in coins)
        assert all("symbol" in c for c in coins)
        assert all("name" in c for c in coins)

    def test_excludes_btc_eth_stablecoins(self, mock_exchange) -> None:
        """Test BTC/ETH/stablecoin exclusion."""
        coins = get_top_altcoins(mock_exchange, limit=10)

        ids = [c["id"] for c in coins]
        assert "BTC" not in ids
        assert "ETH" not in ids
        assert "USDC" not in ids

    def test_sorted_by_volume(self, mock_exchange) -> None:
        """Test that results are sorted by volume descending."""
        coins = get_top_altcoins(mock_exchange, limit=5)

        # SOL has highest volume among non-excluded, then ADA, DOGE, DOT, AVAX
        assert coins[0]["id"] == "SOL"
        assert coins[1]["id"] == "ADA"

    def test_excludes_non_usdt_pairs(self, mock_exchange) -> None:
        """Test that non-USDT pairs are excluded."""
        coins = get_top_altcoins(mock_exchange, limit=10)
        # SOL/BTC should not produce an extra SOL entry issue
        ids = [c["id"] for c in coins]
        assert ids.count("SOL") == 1

    def test_empty_tickers(self) -> None:
        """Test handling of empty tickers response."""
        exchange = MagicMock(spec=ccxt.binance)
        exchange.fetch_tickers.return_value = {}
        coins = get_top_altcoins(exchange, limit=5)
        assert coins == []


class TestFetchHistoricalData:
    """Tests for fetch_historical_data function."""

    def test_returns_dataframe(self, mock_exchange, sample_ohlcv_response) -> None:
        """Test that historical data is returned as DataFrame."""
        df = fetch_historical_data(
            mock_exchange, "SOL/USDT", "2025-01-01", "2025-03-01"
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 60
        assert "price" in df.columns
        assert "volume" in df.columns
        assert "high" in df.columns
        assert "low" in df.columns
        assert "date" in df.columns
        assert "market_cap" in df.columns

    def test_market_cap_is_zero(self, mock_exchange) -> None:
        """Test that market_cap is set to 0 (not available from Binance)."""
        df = fetch_historical_data(
            mock_exchange, "SOL/USDT", "2025-01-01", "2025-03-01"
        )
        assert (df["market_cap"] == 0).all()

    def test_high_low_from_ohlcv(self, mock_exchange) -> None:
        """Test that high/low come from real OHLCV data."""
        df = fetch_historical_data(
            mock_exchange, "SOL/USDT", "2025-01-01", "2025-03-01"
        )
        # High should be different from close (price)
        assert not (df["high"] == df["price"]).all()
        assert not (df["low"] == df["price"]).all()

    def test_deduplicates_dates(self) -> None:
        """Test that duplicate dates are removed."""
        exchange = MagicMock(spec=ccxt.binance)
        ts1 = 1735689600000  # 2025-01-01
        ts2 = 1735776000000  # 2025-01-02
        exchange.fetch_ohlcv.return_value = [
            [ts1, 99, 102, 97, 100, 1000],
            [ts1, 99, 103, 96, 101, 1100],  # duplicate
            [ts2, 104, 107, 103, 105, 1200],
        ]
        df = fetch_historical_data(exchange, "TEST/USDT", "2025-01-01", "2025-01-03")
        assert len(df) == 2

    def test_empty_response(self) -> None:
        """Test handling empty response."""
        exchange = MagicMock(spec=ccxt.binance)
        exchange.fetch_ohlcv.return_value = []
        df = fetch_historical_data(exchange, "EMPTY/USDT", "2025-01-01", "2025-03-01")
        assert df.empty

    def test_pagination(self) -> None:
        """Test that pagination works for >500 candles."""
        exchange = MagicMock(spec=ccxt.binance)
        base_ts = 1735689600000  # 2025-01-01
        day_ms = 86_400_000

        # First call returns 500 candles, second returns 100, third returns empty
        batch1 = [
            [base_ts + i * day_ms, 99, 102, 97, 100 + i * 0.1, 1000]
            for i in range(500)
        ]
        batch2 = [
            [base_ts + (500 + i) * day_ms, 99, 102, 97, 150 + i * 0.1, 1000]
            for i in range(100)
        ]
        exchange.fetch_ohlcv.side_effect = [batch1, batch2, []]

        with patch("src.data_fetcher.time.sleep"):
            df = fetch_historical_data(exchange, "SOL/USDT", "2025-01-01", "2027-01-01")

        assert len(df) == 600
        assert exchange.fetch_ohlcv.call_count == 3

    def test_retry_on_network_error(self) -> None:
        """Test retry on CCXT network error."""
        exchange = MagicMock(spec=ccxt.binance)
        exchange.fetch_ohlcv.side_effect = [
            ccxt.NetworkError("timeout"),
            [[1735689600000, 99, 102, 97, 100, 1000]],
        ]

        with patch("src.data_fetcher.time.sleep"):
            df = fetch_historical_data(
                exchange, "SOL/USDT", "2025-01-01", "2025-01-02"
            )

        assert len(df) == 1

    def test_all_retries_exhausted(self) -> None:
        """Test RuntimeError after all retries fail."""
        exchange = MagicMock(spec=ccxt.binance)
        exchange.fetch_ohlcv.side_effect = ccxt.NetworkError("timeout")

        with patch("src.data_fetcher.time.sleep"):
            with pytest.raises(RuntimeError, match="Failed after"):
                fetch_historical_data(
                    exchange, "SOL/USDT", "2025-01-01", "2025-01-02"
                )


class TestSaveToCsv:
    """Tests for save_to_csv function."""

    def test_creates_new_file(self, tmp_path: Path) -> None:
        """Test creating a new CSV file."""
        filepath = tmp_path / "test.csv"
        df = pd.DataFrame([{"date": "2025-01-01", "price": 100}])

        save_to_csv(df, filepath)

        assert filepath.exists()
        result = pd.read_csv(filepath)
        assert len(result) == 1
        assert result.iloc[0]["price"] == 100

    def test_appends_to_existing(self, tmp_path: Path) -> None:
        """Test appending to existing CSV."""
        filepath = tmp_path / "test.csv"
        df1 = pd.DataFrame([{"date": "2025-01-01", "price": 100}])
        df2 = pd.DataFrame([{"date": "2025-01-02", "price": 105}])

        save_to_csv(df1, filepath)
        save_to_csv(df2, filepath)

        result = pd.read_csv(filepath)
        assert len(result) == 2


class TestSaveToSqlite:
    """Tests for save_to_sqlite function."""

    def test_creates_database(self, tmp_path: Path) -> None:
        """Test creating a new SQLite database."""
        db_path = tmp_path / "test.db"
        df = pd.DataFrame([{
            "date": "2025-01-01", "coin_id": "test", "price": 100,
        }])

        save_to_sqlite(df, db_path)

        assert db_path.exists()
        conn = sqlite3.connect(str(db_path))
        result = pd.read_sql("SELECT * FROM prices", conn)
        conn.close()
        assert len(result) == 1

    def test_appends_data(self, tmp_path: Path) -> None:
        """Test appending data to existing database."""
        db_path = tmp_path / "test.db"
        df1 = pd.DataFrame([{"date": "2025-01-01", "coin_id": "a", "price": 100}])
        df2 = pd.DataFrame([{"date": "2025-01-02", "coin_id": "a", "price": 105}])

        save_to_sqlite(df1, db_path)
        save_to_sqlite(df2, db_path)

        conn = sqlite3.connect(str(db_path))
        result = pd.read_sql("SELECT * FROM prices", conn)
        conn.close()
        assert len(result) == 2


class TestLoadExistingData:
    """Tests for load_existing_data function."""

    def test_empty_when_no_file(self, tmp_path: Path) -> None:
        """Test returns empty dict when file doesn't exist."""
        result = load_existing_data(tmp_path / "nonexistent.csv")
        assert result == {}

    def test_loads_existing_pairs(self, sample_prices_csv: Path) -> None:
        """Test loading existing coin_id/date pairs."""
        result = load_existing_data(sample_prices_csv)
        assert "coin-a" in result
        assert len(result["coin-a"]) == 60


class TestValidateData:
    """Tests for validate_data function."""

    def test_removes_zero_prices(self) -> None:
        """Test that zero prices are removed."""
        df = pd.DataFrame([
            {"date": "2025-01-01", "price": 100},
            {"date": "2025-01-02", "price": 0},
            {"date": "2025-01-03", "price": -5},
        ])
        result = validate_data(df)
        assert len(result) == 1
        assert result.iloc[0]["price"] == 100

    def test_removes_duplicate_dates(self) -> None:
        """Test that duplicate dates are removed."""
        df = pd.DataFrame([
            {"date": "2025-01-01", "price": 100},
            {"date": "2025-01-01", "price": 101},
        ])
        result = validate_data(df)
        assert len(result) == 1

    def test_handles_empty_df(self) -> None:
        """Test handling empty DataFrame."""
        df = pd.DataFrame(columns=["date", "price"])
        result = validate_data(df)
        assert result.empty


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_creates_log_dir(self, tmp_path: Path) -> None:
        """Test that log directory is created."""
        import logging
        from src.data_fetcher import setup_logging
        with patch("src.data_fetcher.LOG_DIR", tmp_path / "logs"):
            root = logging.getLogger()
            root.handlers.clear()
            setup_logging()
            assert (tmp_path / "logs").exists()
            root.handlers.clear()


class TestMainFunction:
    """Tests for the main() function."""

    def _patch_main(self, tmp_path, mock_exchange):
        """Return a context manager that patches main's dependencies."""
        from contextlib import contextmanager

        @contextmanager
        def _ctx():
            with patch("src.data_fetcher.ccxt") as mock_ccxt, \
                 patch("src.data_fetcher.PRICES_CSV", tmp_path / "prices.csv"), \
                 patch("src.data_fetcher.DATABASE_PATH", tmp_path / "test.db"), \
                 patch("src.data_fetcher.DATA_DIR", tmp_path), \
                 patch("src.data_fetcher.time.sleep"), \
                 patch("src.data_fetcher.LOG_DIR", tmp_path / "logs"):
                mock_ccxt.bybit.return_value = mock_exchange
                mock_ccxt.NetworkError = ccxt.NetworkError
                mock_ccxt.ExchangeNotAvailable = ccxt.ExchangeNotAvailable
                mock_ccxt.ExchangeError = ccxt.ExchangeError
                import logging
                logging.getLogger().handlers.clear()
                yield
        return _ctx()

    def test_main_with_specific_coins(
        self, tmp_path: Path, sample_ohlcv_response
    ) -> None:
        """Test main with specific coin list."""
        from src.data_fetcher import main

        mock_exchange = MagicMock()
        mock_exchange.fetch_ohlcv.return_value = sample_ohlcv_response

        with self._patch_main(tmp_path, mock_exchange):
            main(coins=["SOL"])

        assert (tmp_path / "prices.csv").exists()

    def test_main_handles_fetch_failure(self, tmp_path: Path) -> None:
        """Test main gracefully handles fetch failures."""
        from src.data_fetcher import main

        mock_exchange = MagicMock()
        mock_exchange.fetch_ohlcv.side_effect = ccxt.ExchangeError("bad symbol")

        with self._patch_main(tmp_path, mock_exchange):
            # Should not raise
            main(coins=["BADCOIN"])

    def test_main_no_new_data(self, tmp_path: Path) -> None:
        """Test main when there's no new data to save."""
        from src.data_fetcher import main

        mock_exchange = MagicMock()
        mock_exchange.fetch_ohlcv.return_value = []

        with self._patch_main(tmp_path, mock_exchange):
            main(coins=["EMPTY"])
