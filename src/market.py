"""Market-data layer: yfinance prices, EMA, earnings windows."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
import yfinance as yf


@dataclass
class Bars:
    symbol: str
    df: pd.DataFrame  # columns: Open High Low Close Volume; DatetimeIndex (UTC)

    @property
    def last_close(self) -> float:
        return float(self.df["Close"].iloc[-1])

    @property
    def last_high(self) -> float:
        return float(self.df["High"].iloc[-1])

    @property
    def last_open(self) -> float:
        return float(self.df["Open"].iloc[-1])

    @property
    def prev_high(self) -> float:
        return float(self.df["High"].iloc[-2])


def fetch_bars(symbol: str, days: int = 120) -> Optional[Bars]:
    """Fetch daily bars. Returns None on hard failure."""
    try:
        t = yf.Ticker(symbol)
        df = t.history(period=f"{days}d", interval="1d", auto_adjust=False)
        if df is None or df.empty or len(df) < 60:
            return None
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        return Bars(symbol=symbol, df=df)
    except Exception:
        return None


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def next_earnings_date(symbol: str) -> Optional[datetime]:
    """Return next scheduled earnings date (UTC midnight) or None."""
    try:
        t = yf.Ticker(symbol)
        # yfinance API surface drifts; try both
        cal = getattr(t, "calendar", None)
        if isinstance(cal, dict):
            dt = cal.get("Earnings Date")
            if isinstance(dt, list) and dt:
                dt = dt[0]
            if dt is not None:
                return _to_utc(dt)
        try:
            ed = t.earnings_dates
            if ed is not None and not ed.empty:
                today = datetime.now(timezone.utc)
                future = ed.index[ed.index >= today]
                if len(future):
                    return _to_utc(future[0])
        except Exception:
            pass
    except Exception:
        pass
    return None


def _to_utc(x) -> datetime:
    if isinstance(x, datetime):
        return x.astimezone(timezone.utc) if x.tzinfo else x.replace(tzinfo=timezone.utc)
    if isinstance(x, pd.Timestamp):
        ts = x.to_pydatetime()
        return ts.astimezone(timezone.utc) if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(x)).replace(tzinfo=timezone.utc)


def in_earnings_blackout(symbol: str, days: int) -> bool:
    nxt = next_earnings_date(symbol)
    if nxt is None:
        return False
    delta = nxt - datetime.now(timezone.utc)
    return timedelta(0) <= delta <= timedelta(days=days)
