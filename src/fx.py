"""USD↔EUR FX lookup via yfinance."""
from __future__ import annotations

import yfinance as yf

_DEFAULT_USDEUR = 0.93  # fallback if yfinance fails


def usd_to_eur_rate() -> float:
    """Return EUR per 1 USD (e.g. 0.93). Falls back to a sane constant."""
    try:
        df = yf.Ticker("EURUSD=X").history(period="5d", interval="1d")
        if df is None or df.empty:
            return _DEFAULT_USDEUR
        last_eurusd = float(df["Close"].iloc[-1])  # 1 EUR = X USD
        if last_eurusd <= 0:
            return _DEFAULT_USDEUR
        return 1.0 / last_eurusd
    except Exception:
        return _DEFAULT_USDEUR


def usd_to_eur(usd: float, rate: float | None = None) -> float:
    r = rate if rate is not None else usd_to_eur_rate()
    return round(usd * r, 2)
