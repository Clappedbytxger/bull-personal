"""Setup scanner: 20-EMA pullback in confirmed uptrend (Strategy v1)."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

from .config import STRATEGY, ACCOUNT_EQUITY_EUR
from .fx import usd_to_eur_rate
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
    one_share_risk_eur: float        # what 1 share would cost in EUR risk
    one_share_risk_pct: float        # 1-share risk as % of equity
    affordable: bool                 # True if shares >= 1 within risk budget
    notes: str

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate(symbol: str, fx_rate: Optional[float] = None) -> Optional[Setup]:
    """Returns Setup if Strategy-v1 conditions met, else None.

    `fx_rate` is EUR per 1 USD (e.g. 0.8583). If omitted, fetched on demand.
    """
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
    risk_per_share_usd = entry - stop  # USD
    risk_eur = ACCOUNT_EQUITY_EUR * STRATEGY["risk_per_trade_pct"] / 100.0
    # Trade Republic does NOT support fractional shares on Stop-Buy /
    # Stop-Market / Limit orders (only Market). Strategy uses Stop-Buy
    # for entry → must size integer shares. If 1 share already exceeds
    # the risk budget, flag as unaffordable rather than silently breaking
    # the 1% rule.
    fx = fx_rate if fx_rate is not None else usd_to_eur_rate()
    risk_per_share_eur = risk_per_share_usd * fx if fx > 0 else 0.0
    one_share_risk_eur = round(risk_per_share_eur, 2)
    one_share_risk_pct = round(
        (risk_per_share_eur / ACCOUNT_EQUITY_EUR * 100.0) if ACCOUNT_EQUITY_EUR > 0 else 0.0,
        2,
    )
    if risk_per_share_eur <= 0:
        shares = 0
    else:
        shares = int(risk_eur // risk_per_share_eur)  # floor
    affordable = shares >= 1

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
        one_share_risk_eur=one_share_risk_eur,
        one_share_risk_pct=one_share_risk_pct,
        affordable=affordable,
        notes=f"close {close:.2f} vs 20EMA {e20:.2f} ({(close/e20-1)*100:+.1f}%)",
    )


def scan(symbols: list[str], fx_rate: Optional[float] = None) -> list[Setup]:
    """Scan symbols for setups. `fx_rate` propagates to sizing; fetched lazily if None."""
    if fx_rate is None:
        fx_rate = usd_to_eur_rate()
    out: list[Setup] = []
    for s in symbols:
        try:
            setup = evaluate(s, fx_rate=fx_rate)
            if setup is not None:
                out.append(setup)
        except Exception as exc:
            print(f"[scan] {s}: {exc}")
    return out
