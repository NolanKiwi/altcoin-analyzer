"""Configuration and constants for the altcoin analyzer."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
LOG_DIR = PROJECT_ROOT / "logs"
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", DATA_DIR / "altcoins.db"))
PRICES_CSV = DATA_DIR / "altcoin_prices.csv"
RESULTS_CSV = DATA_DIR / "analysis_results.csv"

# Binance via CCXT
RATE_LIMIT_DELAY = 0.1  # seconds between requests (~1200 req/min on Binance)
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # exponential backoff multiplier
QUOTE_CURRENCY = "USDT"

# Symbols to exclude (BTC, ETH, stablecoins)
EXCLUDE_SYMBOLS = frozenset({
    "BTC", "ETH", "USDT", "USDC", "DAI", "BUSD",
    "TUSD", "USDD", "FRAX", "USDP", "FDUSD",
    "USDE", "USD", "PYUSD",
})

# Analysis
MIN_DATA_DAYS = 30
TOP_N_RANKING = 50
DEFAULT_COIN_LIMIT = 200

# Date range
START_DATE = "2025-01-01"

# Dashboard
CACHE_TTL = 3600  # 1 hour
