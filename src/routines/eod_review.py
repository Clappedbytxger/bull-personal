"""End-of-day review (runs inside Bull's 05-close-summary at 21:15 UTC).

Pulls every Notion Trade-Journal page with Status=Open, fetches current close,
and emits per-position actions: HOLD / EXIT-STOP / EXIT-TARGET / TRAIL-BE.
WhatsApps Robin only if ≥1 position needs his manual attention.
"""
from __future__ import annotations

import sys
from datetime import datetime

from ..notion import list_open_trades, read_number, read_text, read_select
from ..market import fetch_bars
from ..notify import send_whatsapp


def evaluate_position(ticker: str, entry: float, stop: float, target: float,
                      direction: str = "Long") -> dict:
    bars = fetch_bars(ticker, days=30)
    if bars is None:
        return {"ticker": ticker, "action": "DATA-FAIL", "close": None, "r": None, "msg": "no bars"}
    close = bars.last_close
    risk = (entry - stop) if direction == "Long" else (stop - entry)
    move = (close - entry) if direction == "Long" else (entry - close)
    r = move / risk if risk > 0 else 0.0

    hit_stop = close <= stop if direction == "Long" else close >= stop
    hit_target = close >= target if direction == "Long" else close <= target

    if hit_stop:
        action, msg = "EXIT-STOP", f"close {close:.2f} hit SL {stop:.2f}"
    elif hit_target:
        action, msg = "EXIT-TARGET", f"close {close:.2f} hit TP {target:.2f}"
    elif r >= 1.0:
        action, msg = "TRAIL-BE", f"r={r:.2f} → SL auf Entry {entry:.2f} ziehen"
    else:
        action, msg = "HOLD", f"close {close:.2f} r={r:.2f}"
    return {"ticker": ticker, "action": action, "close": round(close, 2), "r": round(r, 2), "msg": msg}


def main() -> int:
    print(f"[eod_review] {datetime.utcnow().isoformat(timespec='seconds')}Z")
    try:
        pages = list_open_trades()
    except Exception as exc:
        print(f"[eod_review] Notion query failed: {exc}")
        return 1

    print(f"[eod_review] {len(pages)} open trade(s)")
    if not pages:
        print("[eod_review] flat — nothing to do")
        return 0

    results = []
    for pg in pages:
        ticker = (read_text(pg, "Ticker") or "").upper()
        entry = read_number(pg, "Entry Price")
        stop = read_number(pg, "Stop Loss")
        target = read_number(pg, "Target")
        direction = read_select(pg, "Direction") or "Long"
        if None in (entry, stop, target) or not ticker:
            results.append({"ticker": ticker or "?", "action": "DATA-FAIL",
                             "msg": "missing Ticker/Entry/SL/Target in Notion"})
            continue
        r = evaluate_position(ticker, entry, stop, target, direction)
        results.append(r)
        print(f"  · {r['ticker']:<6} {r['action']:<12} {r['msg']}")

    actionables = [r for r in results if r["action"] not in ("HOLD",)]
    if not actionables:
        print("[eod_review] all HOLD — no WhatsApp")
        return 0

    lines = [f"Bull-Personal EOD {datetime.utcnow().strftime('%Y-%m-%d')}", ""]
    for r in actionables:
        lines.append(f"• {r['ticker']}: {r['action']} — {r['msg']}")
    lines += ["", "Manuelle Aktion in TR-App nötig."]
    res = send_whatsapp("\n".join(lines))
    print(f"[eod_review] WhatsApp: {res}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
