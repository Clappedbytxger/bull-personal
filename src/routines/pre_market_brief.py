"""Daily 14:30 DE pre-market brief.

Scan watchlist for Strategy-v1 setups, write Notion page + WhatsApp summary.
Usage:
    python -m src.routines.pre_market_brief            # full run
    python -m src.routines.pre_market_brief --dry-run  # no Notion/WhatsApp side-effects
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

from ..config import WATCHLIST, ACCOUNT_EQUITY_EUR, STRATEGY
from ..scanner import Setup, scan
from ..notion import write_premarket_brief
from ..notify import send_whatsapp


def format_markdown(setups: list[Setup], date_iso: str) -> str:
    head = (
        f"# Pre-Market Brief {date_iso}\n\n"
        f"Strategy: 20-EMA-Pullback v1 · Equity {ACCOUNT_EQUITY_EUR:.0f}€ · "
        f"Risk {STRATEGY['risk_per_trade_pct']:.1f}%/Trade · Max {STRATEGY['max_positions']} Pos\n"
        f"Watchlist {len(WATCHLIST)} Symbole · Setups gefunden: **{len(setups)}**\n\n"
    )
    if not setups:
        return head + "Keine Setups heute. Nichts zu tun. Stay flat.\n"
    rows = [
        "| Sym | Entry | SL | TP | Shares | Risk € | Notes |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for s in setups:
        rows.append(
            f"| {s.symbol} | {s.entry:.2f} | {s.stop:.2f} | {s.target:.2f} | "
            f"{s.shares} | {s.risk_eur:.2f} | {s.notes} |"
        )
    return head + "\n".join(rows) + "\n\nR:R 1:2 fix. Stop-Buy 0.1% über High. Keine Earnings-Holds.\n"


def format_whatsapp(setups: list[Setup], date_iso: str) -> str:
    if not setups:
        return (
            f"Bull-Personal {date_iso}\n"
            f"Watchlist {len(WATCHLIST)} gescannt — 0 Setups.\n"
            f"Heute nichts. Stay flat."
        )
    lines = [
        f"Bull-Personal {date_iso}",
        f"{len(setups)} Setup(s) heute (20-EMA-Pullback):",
        "",
    ]
    for s in setups[:5]:  # cap to keep <950 chars
        lines.append(
            f"• {s.symbol}: Entry {s.entry:.2f} | SL {s.stop:.2f} | TP {s.target:.2f} "
            f"| {s.shares}sh | Risk {s.risk_eur:.2f}€"
        )
    if len(setups) > 5:
        lines.append(f"…+{len(setups) - 5} weitere im Notion-Brief")
    lines += ["", "Stop-Buy in TR ~0.1% über High. Max 3 Pos."]
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="no Notion/WhatsApp side-effects")
    args = p.parse_args()

    date_iso = datetime.utcnow().strftime("%Y-%m-%d")
    print(f"[pre_market_brief] {date_iso} scanning {len(WATCHLIST)} symbols…")

    setups = scan(WATCHLIST)
    print(f"[pre_market_brief] {len(setups)} setup(s) found")
    for s in setups:
        print(f"  · {s.symbol} entry={s.entry} stop={s.stop} tp={s.target} shares={s.shares}")

    md = format_markdown(setups, date_iso)
    wa = format_whatsapp(setups, date_iso)

    if args.dry_run:
        print("\n=== NOTION-MARKDOWN ===\n" + md)
        print("\n=== WHATSAPP ===\n" + wa)
        return 0

    try:
        setups_detail = " · ".join(
            f"{s.symbol} {s.entry:.2f}/{s.stop:.2f}/{s.target:.2f}" for s in setups
        ) or "—"
        write_premarket_brief(
            date_iso=date_iso,
            n_setups=len(setups),
            setups_detail=setups_detail,
            market_bias="Neutral",
            brief_markdown=md,
        )
        print("[pre_market_brief] Notion page written")
    except Exception as exc:
        print(f"[pre_market_brief] Notion write failed: {exc}")

    res = send_whatsapp(wa)
    print(f"[pre_market_brief] WhatsApp: {res}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
