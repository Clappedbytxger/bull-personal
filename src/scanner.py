"""Setup scanner: 20-EMA pullback in confirmed uptrend (Strategy v1)."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

from .config import STRATEGY, ACCOUNT_EQUITY_EUR
from .market import Bars, ema, fetch_bars, in_earnings_blackout


@dataclass
class Setup:
    symbol: str
    close: float
    ema20: float
    ema50: float
    pullback_low: float
    entry: float
    stop: float
    target: float
    risk_pct: float
    reward_pct: float
    rr: float
    shares: int
    risk_eur: float
    notes: str

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate(symbol: str) -> Optional[Setup]:
    """Returns Setup if Strategy-v1 conditions met, else None."""
    bars = fetch_bars(symbol, days=120)
    if bars is None:
        return None
    df = bars.df

    e20_series = ema(df["Close"], STRATEGY["ema_fast"])
    e50_series = ema(df["Close"], STRATEGY["ema_slow"])
    e20 = float(e20_series.iloc[-1])
    e50 = float(e50_series.iloc[-1])
    close = bars.last_close

    # 1. Trend
    if not (close > e50 and e20 > e50):
        return None

    # 2. Pullback: any of last N lows touched 20-EMA ± tol%
    tol = STRATEGY["pullback_tolerance_pct"] / 100.0
    lookback = STRATEGY["pullback_lookback"]
    recent_lows = df["Low"].iloc[-lookback:]
    recent_e20 = e20_series.iloc[-lookback:]
    touched = ((recent_lows <= recent_e20 * (1 + tol)) &
               (recent_lows >= recent_e20 * (1 - tol))).any()
    if not touched:
        return None

    # 3. Confirmation: today bullish AND close > prev high
    if not (bars.last_close > bars.last_open and bars.last_close > bars.prev_high):
        return None

    # 4. Earnings blackout
    if in_earnings_blackout(symbol, STRATEGY["earnings_blackout_days"]):
        return None

    # 5. Build trade plan
    buf = STRATEGY["entry_buffer_pct"] / 100.0
    entry = round(bars.last_high * (1 + buf), 2)
    stop = round(entry * (1 - STRATEGY["stop_pct"] / 100.0), 2)
    target = round(entry * (1 + STRATEGY["target_pct"] / 100.0), 2)
    risk_per_share = entry - stop
    risk_eur = ACCOUNT_EQUITY_EUR * STRATEGY["risk_per_trade_pct"] / 100.0
    shares = max(int(risk_eur / risk_per_share), 0) if risk_per_share > 0 else 0

    pullback_low = float(recent_lows.min())

    return Setup(
        symbol=symbol,
        close=round(close, 2),
        ema20=round(e20, 2),
        ema50=round(e50, 2),
        pullback_low=round(pullback_low, 2),
        entry=entry,
        stop=stop,
        target=target,
        risk_pct=STRATEGY["stop_pct"],
        reward_pct=STRATEGY["target_pct"],
        rr=round(STRATEGY["target_pct"] / STRATEGY["stop_pct"], 2),
        shares=shares,
        risk_eur=round(risk_eur, 2),
        notes=f"close {close:.2f} vs 20EMA {e20:.2f} ({(close/e20-1)*100:+.1f}%)",
    )


def scan(symbols: list[str]) -> list[Setup]:
    out: list[Setup] = []
    for s in symbols:
        try:
            setup = evaluate(s)
            if setup is not None:
                out.append(setup)
        except Exception as exc:
            print(f"[scan] {s}: {exc}")
    return out
