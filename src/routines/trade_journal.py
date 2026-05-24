"""Trade-Journal CLI — Robin runs this AFTER executing a Trade-Republic order.

Usage:
    python -m src.routines.trade_journal NVDA --entry 142.30 --shares 3
    # uses Strategy-v1 defaults for SL (-8%) and TP (+16%); direction=Long; Paper

    python -m src.routines.trade_journal NVDA --entry 142.30 --stop 131.00 \\
        --target 165.00 --shares 3 --setup "Pullback 20-EMA" --rationale "Bounce off 20EMA, volumen ok"
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

from ..config import STRATEGY, ACCOUNT_EQUITY_EUR
from ..notion import write_trade


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("ticker")
    p.add_argument("--entry", type=float, required=True)
    p.add_argument("--shares", type=float, required=True)
    p.add_argument("--stop", type=float, default=None)
    p.add_argument("--target", type=float, default=None)
    p.add_argument("--direction", choices=["Long", "Short"], default="Long")
    p.add_argument("--paper-or-live", choices=["Paper", "Live"], default="Paper")
    p.add_argument("--setup", default="Pullback 20-EMA",
                   choices=["Pullback 20-EMA", "VCP Breakout", "Mean Reversion", "Other"])
    p.add_argument("--rationale", default="")
    p.add_argument("--date", default=datetime.utcnow().strftime("%Y-%m-%d"))
    args = p.parse_args()

    if args.direction == "Long":
        stop = args.stop if args.stop is not None else round(args.entry * (1 - STRATEGY["stop_pct"] / 100.0), 2)
        target = args.target if args.target is not None else round(args.entry * (1 + STRATEGY["target_pct"] / 100.0), 2)
        risk_per_share = args.entry - stop
    else:
        stop = args.stop if args.stop is not None else round(args.entry * (1 + STRATEGY["stop_pct"] / 100.0), 2)
        target = args.target if args.target is not None else round(args.entry * (1 - STRATEGY["target_pct"] / 100.0), 2)
        risk_per_share = stop - args.entry

    risk_eur = round(risk_per_share * args.shares, 2)
    risk_pct = round(risk_eur / ACCOUNT_EQUITY_EUR * 100, 2)

    print(f"[trade_journal] {args.direction} {args.ticker} {args.date}")
    print(f"  entry={args.entry} stop={stop} target={target} shares={args.shares}")
    print(f"  risk={risk_eur}€ ({risk_pct}% of {ACCOUNT_EQUITY_EUR}€) · setup={args.setup} · {args.paper_or_live}")
    if risk_pct > STRATEGY["risk_per_trade_pct"] * 1.5:
        print(f"  WARN: risk {risk_pct}% exceeds 1.5× target ({STRATEGY['risk_per_trade_pct']}%).")

    res = write_trade(
        ticker=args.ticker.upper(),
        entry_date=args.date,
        entry=args.entry,
        stop=stop,
        target=target,
        shares=args.shares,
        risk_eur=risk_eur,
        setup=args.setup,
        direction=args.direction,
        paper_or_live=args.paper_or_live,
        rationale=args.rationale,
    )
    print(f"[trade_journal] Notion page created: {res.get('id', '?')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
