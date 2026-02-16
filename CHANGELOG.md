# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-02-16

### Added
- Initial release
- CoinGecko API data fetcher with rate limiting and retry logic
- Price analysis engine: peak detection, drop ranking, statistics
- Streamlit multi-page dashboard
  - Home page with overview metrics
  - Top 50 ranking with interactive table and charts
  - Individual coin detail view with price history
  - About page with methodology
- Dual storage: CSV and SQLite
- Comprehensive test suite (67 tests, 95%+ coverage)
- GitHub Actions CI/CD pipeline
- CLI arguments for data fetcher (--update, --coins, --num-coins)
- CSV/JSON export of analysis results
- Resumable data downloads
