# Altcoin Price Drop Analyzer

A production-ready dashboard that tracks the biggest price drops among top altcoins (excluding BTC/ETH) from their 2025 peak prices. Fetches data from Binance via CCXT, performs analysis, and presents results in an interactive Streamlit dashboard.

## Features

- Fetches historical OHLCV data for top 200 altcoins by trading volume
- Analyzes 2025 peak prices vs current prices
- Ranks top 50 altcoins by biggest price drops
- Interactive Streamlit dashboard with Plotly charts
- Multi-page dashboard: Home, Top 50, Coin Details, About
- Dual storage: CSV and SQLite
- Resumable data fetching with rate limiting
- Comprehensive test suite (95%+ coverage)
- CI/CD with GitHub Actions
- No API key required — uses Binance public endpoints

## Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd altcoin-analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# For development (includes testing tools)
pip install -r requirements-dev.txt
```

## Configuration

Copy the example environment file and configure:

```bash
cp .env.example .env
```

No API key is required. Binance public endpoints are used via CCXT.

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_PATH` | SQLite database path | `data/altcoins.db` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DATA_DIR` | Data storage directory | `data` |

## Usage

### 1. Fetch Data

```bash
# Fetch top 200 altcoins (fast — Binance has high rate limits)
python -m src.data_fetcher

# Fetch specific coins only
python -m src.data_fetcher --coins SOL ADA DOGE

# Update existing data (skip already-fetched dates)
python -m src.data_fetcher --update

# Fetch fewer coins
python -m src.data_fetcher --num-coins 50
```

### 2. Run Analysis

```bash
python -m src.analyzer
```

### 3. Launch Dashboard

```bash
streamlit run src/dashboard.py
```

The dashboard will open at `http://localhost:8501`.

## Testing

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_analyzer.py

# Run with verbose output
pytest -v

# Generate HTML coverage report
pytest --cov-report=html
# Open htmlcov/index.html in browser
```

## Project Structure

```
altcoin-analyzer/
├── .github/workflows/
│   └── test.yml                 # GitHub Actions CI/CD
├── data/                        # Data storage (gitignored)
├── src/
│   ├── __init__.py
│   ├── config.py                # Configuration and constants
│   ├── data_fetcher.py          # Binance OHLCV data collection via CCXT
│   ├── analyzer.py              # Price analysis and ranking
│   ├── dashboard.py             # Main Streamlit app entry
│   └── pages/
│       ├── 1_🏠_Home.py          # Dashboard home with overview
│       ├── 2_📊_Top_50.py        # Top 50 drops ranking
│       ├── 3_💰_Coin_Details.py  # Individual coin analysis
│       └── 4_ℹ️_About.py         # Project information
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Test fixtures
│   ├── test_data_fetcher.py     # Data fetcher unit tests
│   ├── test_analyzer.py         # Analyzer unit tests
│   └── test_integration.py      # Integration tests
├── .coveragerc                  # Coverage configuration
├── .env.example                 # Environment variables template
├── .gitignore
├── CHANGELOG.md
├── LICENSE                      # MIT License
├── README.md
├── pytest.ini                   # pytest configuration
├── requirements.txt             # Production dependencies
└── requirements-dev.txt         # Development dependencies
```

## Technologies Used

| Technology | Purpose |
|-----------|---------|
| Python 3.10+ | Core language |
| Pandas / NumPy | Data analysis |
| Streamlit | Web dashboard |
| Plotly | Interactive charts |
| SQLite | Local database |
| CCXT / Binance | Price data source |
| pytest | Testing framework |
| GitHub Actions | CI/CD |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file.

## Roadmap

- [ ] Real-time price updates via WebSocket
- [ ] Portfolio tracking and alerts
- [ ] Technical indicators (RSI, MACD, Bollinger Bands)
- [ ] Comparison charts between multiple coins
- [ ] Export reports to PDF
- [ ] Docker containerization
- [ ] Redis caching for API responses
- [ ] Historical market cycle analysis
