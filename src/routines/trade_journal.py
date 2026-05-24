"""Trade-Journal CLI — Robin runs this AFTER executing a Trade-Republic order.

Usage:
    python -m src.routines.trade_journal NVDA --entry 142.30 --shares 3
    # uses Strategy-v1 defaults for SL (-8%) and TP (+16%)

    python -m src.routines.trade_journal NVDA --entry 142.30 --stop 131.00 --target 165.00 --shares 3

Optional flags:
    --setup "20EMA-Pullback"
    --notes "Brach Vor-Tag-High mit Volumen"
    --date 2026-05-24   (default: today UTC)
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

from ..config import STRATEGY, ACCOUNT_EQUITY_EUR
from ..notion import write_trade


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("symbol")
    p.add_argument("--entry", type=float, required=True)
    p.add_argument("--shares", type=int, required=True)
    p.add_argument("--stop", type=float, default=None)
    p.add_argument("--target", type=float, default=None)
    p.add_argument("--setup", default="20EMA-Pullback")
    p.add_argument("--notes", default="")
    p.add_argument("--date", default=datetime.utcnow().strftime("%Y-%m-%d"))
    args = p.parse_args()

    stop = args.stop if args.stop is not None else round(args.entry * (1 - STRATEGY["stop_pct"] / 100.0), 2)
    target = args.target if args.target is not None else round(args.entry * (1 + STRATEGY["target_pct"] / 100.0), 2)
    risk_eur = round((args.entry - stop) * args.shares, 2)
    risk_pct = round(risk_eur / ACCOUNT_EQUITY_EUR * 100, 2)

    print(f"[trade_journal] {args.symbol} {args.date}")
    print(f"  entry={args.entry} stop={stop} target={target} shares={args.shares}")
    print(f"  risk={risk_eur}€ ({risk_pct}% of {ACCOUNT_EQUITY_EUR}€)")
    if risk_pct > STRATEGY["risk_per_trade_pct"] * 1.5:
        print(f"  WARN: risk {risk_pct}% exceeds 1.5× target ({STRATEGY['risk_per_trade_pct']}%).")

    res = write_trade(
        symbol=args.symbol.upper(),
        entry_date=args.date,
        entry=args.entry,
        stop=stop,
        target=target,
        shares=args.shares,
        risk_eur=risk_eur,
        setup_tag=args.setup,
        notes=args.notes,
    )
    print(f"[trade_journal] Notion page created: {res.get('id', '?')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
