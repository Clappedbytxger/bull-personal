"""Static config + env loading."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

WATCHLIST: list[str] = [
    "NVDA", "MSFT", "GOOGL", "META", "AAPL",
    "CRM", "AVGO", "AMD", "TSM", "AMZN",
    "COST", "NFLX", "V", "JPM", "CAT",
    "GE", "XOM", "LLY", "UNH", "TSLA",
]

# Strategy v1 params — locked until 4-week paper review
STRATEGY = {
    "version": "v1",
    "ema_fast": 20,
    "ema_slow": 50,
    "pullback_tolerance_pct": 2.0,   # low touched 20-EMA ± 2%
    "pullback_lookback": 3,           # last N daily bars
    "stop_pct": 8.0,
    "target_pct": 16.0,
    "risk_per_trade_pct": 1.5,
    "max_positions": 3,
    "earnings_blackout_days": 3,
    "entry_buffer_pct": 0.1,          # stop-buy 0.1% above confirmation high
}

# Env
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DB_PREMARKET = os.getenv("NOTION_DB_PREMARKET", "")
NOTION_DB_JOURNAL = os.getenv("NOTION_DB_JOURNAL", "")
CALLMEBOT_API_KEY = os.getenv("CALLMEBOT_API_KEY", "")
WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE", "")
ACCOUNT_EQUITY_EUR = float(os.getenv("ACCOUNT_EQUITY_EUR", "1000"))


def require(name: str, value: str) -> str:
    if not value:
        raise RuntimeError(f"Missing env var: {name}")
    return value
