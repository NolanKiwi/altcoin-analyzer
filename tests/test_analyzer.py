"""Unit tests for analyzer module."""

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.analyzer import (
    calculate_drop_percentage,
    export_results,
    find_2025_peak,
    generate_summary,
    get_coin_stats,
    get_current_price,
    load_data,
    rank_by_drop,
)


class TestFindPeak:
    """Tests for find_2025_peak function."""

    def test_finds_correct_peak(self, sample_prices_df: pd.DataFrame) -> None:
        """Test peak detection with known data."""
        peak = find_2025_peak(sample_prices_df, "coin-a")
        assert peak["price"] == 250.0
        assert "date" in peak

    def test_empty_for_unknown_coin(self, sample_prices_df: pd.DataFrame) -> None:
        """Test returns empty dict for non-existent coin."""
        peak = find_2025_peak(sample_prices_df, "nonexistent")
        assert peak == {}

    def test_peak_date_format(self, sample_prices_df: pd.DataFrame) -> None:
        """Test that peak date is in YYYY-MM-DD format."""
        peak = find_2025_peak(sample_prices_df, "coin-a")
        # Validate date format
        datetime.strptime(peak["date"], "%Y-%m-%d")


class TestGetCurrentPrice:
    """Tests for get_current_price function."""

    def test_returns_latest_price(self, sample_prices_df: pd.DataFrame) -> None:
        """Test that the most recent price is returned."""
        price = get_current_price(sample_prices_df, "coin-a")
        # Day 59: peak - (peak - end) * (39/40) = 250 - 170*0.975 = 84.25
        assert price == pytest.approx(84.25, abs=0.01)

    def test_zero_for_unknown_coin(self, sample_prices_df: pd.DataFrame) -> None:
        """Test returns 0 for non-existent coin."""
        price = get_current_price(sample_prices_df, "nonexistent")
        assert price == 0.0


class TestCalculateDropPercentage:
    """Tests for calculate_drop_percentage function."""

    def test_basic_drop(self) -> None:
        """Test basic drop calculation."""
        result = calculate_drop_percentage(100.0, 50.0)
        assert result == -50.0

    def test_no_change(self) -> None:
        """Test zero change."""
        result = calculate_drop_percentage(100.0, 100.0)
        assert result == 0.0

    def test_increase(self) -> None:
        """Test price increase (positive %)."""
        result = calculate_drop_percentage(100.0, 150.0)
        assert result == 50.0

    def test_zero_peak(self) -> None:
        """Test zero peak price returns 0."""
        result = calculate_drop_percentage(0.0, 50.0)
        assert result == 0.0

    def test_negative_peak(self) -> None:
        """Test negative peak price returns 0."""
        result = calculate_drop_percentage(-10.0, 50.0)
        assert result == 0.0

    def test_ninety_percent_drop(self) -> None:
        """Test 90% drop accuracy."""
        result = calculate_drop_percentage(200.0, 20.0)
        assert result == -90.0

    def test_small_prices(self) -> None:
        """Test with very small prices."""
        result = calculate_drop_percentage(0.001, 0.0005)
        assert result == -50.0


class TestRankByDrop:
    """Tests for rank_by_drop function."""

    def test_ranks_correctly(self, sample_prices_df: pd.DataFrame) -> None:
        """Test that coins are ranked by biggest drop."""
        results = rank_by_drop(sample_prices_df, top_n=50)
        assert len(results) > 0
        # Verify sorted ascending (biggest drops first)
        pct_changes = results["pct_change"].tolist()
        assert pct_changes == sorted(pct_changes)

    def test_top_n_limit(self, sample_prices_df: pd.DataFrame) -> None:
        """Test top_n parameter limits results."""
        results = rank_by_drop(sample_prices_df, top_n=2)
        assert len(results) <= 2

    def test_excludes_coins_with_no_drop(self) -> None:
        """Test that coins without drops are excluded."""
        # Coin that only goes up
        rows = []
        base_date = datetime(2025, 1, 1)
        from datetime import timedelta
        for day in range(60):
            rows.append({
                "date": base_date + timedelta(days=day),
                "coin_id": "moon-coin",
                "coin_name": "Moon Coin",
                "symbol": "moon",
                "price": 100 + day,
                "market_cap": 1_000_000,
                "volume": 500_000,
            })
        df = pd.DataFrame(rows)
        results = rank_by_drop(df)
        assert len(results) == 0

    def test_skips_insufficient_data(self, single_record_df: pd.DataFrame) -> None:
        """Test coins with < MIN_DATA_DAYS are skipped."""
        results = rank_by_drop(single_record_df)
        assert len(results) == 0

    def test_skips_zero_price(self) -> None:
        """Test coins with zero prices are skipped."""
        rows = []
        base_date = datetime(2025, 1, 1)
        from datetime import timedelta
        for day in range(60):
            rows.append({
                "date": base_date + timedelta(days=day),
                "coin_id": "zero-coin",
                "coin_name": "Zero",
                "symbol": "zero",
                "price": 0,
                "market_cap": 0,
                "volume": 0,
            })
        df = pd.DataFrame(rows)
        results = rank_by_drop(df)
        assert len(results) == 0

    def test_one_based_ranking(self, sample_prices_df: pd.DataFrame) -> None:
        """Test that ranking starts at 1."""
        results = rank_by_drop(sample_prices_df)
        if not results.empty:
            assert results.index[0] == 1
            assert results.index.name == "rank"

    def test_empty_input(self, empty_prices_df: pd.DataFrame) -> None:
        """Test with empty DataFrame."""
        results = rank_by_drop(empty_prices_df)
        assert results.empty


class TestGetCoinStats:
    """Tests for get_coin_stats function."""

    def test_returns_all_fields(self, sample_prices_df: pd.DataFrame) -> None:
        """Test that all expected fields are returned."""
        stats = get_coin_stats(sample_prices_df, "coin-a")
        expected_keys = [
            "coin_id", "coin_name", "symbol", "peak_price", "peak_date",
            "current_price", "current_date", "drop_percentage",
            "volatility_30d", "avg_volume_30d", "market_cap",
            "market_cap_change_pct", "data_points",
        ]
        for key in expected_keys:
            assert key in stats, f"Missing key: {key}"

    def test_correct_peak(self, sample_prices_df: pd.DataFrame) -> None:
        """Test peak price is correct."""
        stats = get_coin_stats(sample_prices_df, "coin-a")
        assert stats["peak_price"] == 250.0

    def test_correct_current(self, sample_prices_df: pd.DataFrame) -> None:
        """Test current price is correct."""
        stats = get_coin_stats(sample_prices_df, "coin-a")
        assert stats["current_price"] == pytest.approx(84.25, abs=0.01)

    def test_volatility_is_positive(self, sample_prices_df: pd.DataFrame) -> None:
        """Test that volatility is non-negative."""
        stats = get_coin_stats(sample_prices_df, "coin-a")
        assert stats["volatility_30d"] >= 0

    def test_empty_for_unknown_coin(self, sample_prices_df: pd.DataFrame) -> None:
        """Test returns empty dict for unknown coin."""
        stats = get_coin_stats(sample_prices_df, "nonexistent")
        assert stats == {}

    def test_data_points_count(self, sample_prices_df: pd.DataFrame) -> None:
        """Test data points count is correct."""
        stats = get_coin_stats(sample_prices_df, "coin-a")
        assert stats["data_points"] == 60


class TestGenerateSummary:
    """Tests for generate_summary function."""

    def test_summary_fields(self, sample_prices_df: pd.DataFrame) -> None:
        """Test summary contains expected fields."""
        results = rank_by_drop(sample_prices_df)
        summary = generate_summary(results)
        assert "total_coins" in summary
        assert "avg_drop_pct" in summary
        assert "median_drop_pct" in summary
        assert "worst_drop_pct" in summary
        assert "biggest_loser" in summary

    def test_empty_summary(self) -> None:
        """Test summary with empty results."""
        summary = generate_summary(pd.DataFrame())
        assert summary["total_coins"] == 0


class TestExportResults:
    """Tests for export_results function."""

    def test_export_csv(self, tmp_path: Path, sample_prices_df: pd.DataFrame) -> None:
        """Test CSV export."""
        results = rank_by_drop(sample_prices_df)
        filepath = tmp_path / "results.csv"
        export_results(results, "csv", filepath)
        assert filepath.exists()
        loaded = pd.read_csv(filepath)
        assert len(loaded) == len(results)

    def test_export_json(self, tmp_path: Path, sample_prices_df: pd.DataFrame) -> None:
        """Test JSON export."""
        results = rank_by_drop(sample_prices_df)
        filepath = tmp_path / "results.json"
        export_results(results, "json", filepath)
        assert filepath.exists()

    def test_export_returns_path(
        self, tmp_path: Path, sample_prices_df: pd.DataFrame
    ) -> None:
        """Test that export returns the filepath."""
        results = rank_by_drop(sample_prices_df)
        filepath = tmp_path / "results.csv"
        result_path = export_results(results, "csv", filepath)
        assert result_path == filepath


class TestRun:
    """Tests for the run() function."""

    def test_run_produces_results(
        self, sample_prices_csv: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that run() produces ranked results."""
        from src.analyzer import run

        monkeypatch.setattr("src.analyzer.PRICES_CSV", sample_prices_csv)
        monkeypatch.setattr("src.analyzer.DATABASE_PATH", tmp_path / "nonexistent.db")
        monkeypatch.setattr("src.analyzer.RESULTS_CSV", tmp_path / "results.csv")
        monkeypatch.setattr("src.analyzer.DATA_DIR", tmp_path)

        import logging
        logging.basicConfig(level=logging.INFO)

        results = run()
        assert not results.empty
        assert (tmp_path / "results.csv").exists()


class TestLoadData:
    """Tests for load_data function."""

    def test_load_from_csv(
        self, sample_prices_csv: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test loading data from CSV."""
        import src.config
        monkeypatch.setattr(src.config, "PRICES_CSV", sample_prices_csv)
        monkeypatch.setattr("src.analyzer.PRICES_CSV", sample_prices_csv)
        # Make sure sqlite path doesn't exist
        import tempfile
        fake_db = Path(tempfile.mktemp(suffix=".db"))
        monkeypatch.setattr(src.config, "DATABASE_PATH", fake_db)
        monkeypatch.setattr("src.analyzer.DATABASE_PATH", fake_db)

        df = load_data(source="csv")
        assert not df.empty
        assert "coin_id" in df.columns

    def test_file_not_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test FileNotFoundError when no data exists."""
        fake_csv = tmp_path / "nonexistent.csv"
        fake_db = tmp_path / "nonexistent.db"
        monkeypatch.setattr("src.analyzer.PRICES_CSV", fake_csv)
        monkeypatch.setattr("src.analyzer.DATABASE_PATH", fake_db)

        with pytest.raises(FileNotFoundError):
            load_data()
