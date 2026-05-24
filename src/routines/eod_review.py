"""End-of-day review (21:30 DE Mon-Fri).

Pulls every Notion Trade-Journal page with Status=Open, fetches current close,
and emits per-position actions: HOLD / EXIT-TARGET / EXIT-STOP / TRAIL.
WhatsApps Robin only if at least one action needs his manual attention.
"""
from __future__ import annotations

import sys
from datetime import datetime

from ..notion import (
    list_open_trades, read_number, read_text, read_title,
)
from ..market import fetch_bars
from ..notify import send_whatsapp


def evaluate_position(symbol: str, entry: float, stop: float, target: float) -> dict:
    bars = fetch_bars(symbol, days=30)
    if bars is None:
        return {"symbol": symbol, "action": "DATA-FAIL", "close": None, "r": None, "msg": "no bars"}
    close = bars.last_close
    risk = entry - stop
    r = (close - entry) / risk if risk > 0 else 0.0

    # Daily-bar-based check (TR has no overnight stops anyway; intraday tick irrelevant for swing)
    if close <= stop:
        action, msg = "EXIT-STOP", f"close {close:.2f} ≤ SL {stop:.2f}"
    elif close >= target:
        action, msg = "EXIT-TARGET", f"close {close:.2f} ≥ TP {target:.2f}"
    elif r >= 1.0:
        # at +1R, trail SL to break-even (manual hint)
        action, msg = "TRAIL-BE", f"r={r:.2f} → SL auf Entry {entry:.2f} ziehen"
    else:
        action, msg = "HOLD", f"close {close:.2f} r={r:.2f}"
    return {"symbol": symbol, "action": action, "close": round(close, 2), "r": round(r, 2), "msg": msg}


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
        sym = (read_text(pg, "Symbol") or read_title(pg).split()[0]).upper()
        entry = read_number(pg, "Entry")
        stop = read_number(pg, "SL")
        target = read_number(pg, "TP")
        if None in (entry, stop, target):
            results.append({"symbol": sym, "action": "DATA-FAIL", "msg": "missing entry/SL/TP in Notion"})
            continue
        r = evaluate_position(sym, entry, stop, target)
        results.append(r)
        print(f"  · {r['symbol']:<6} {r['action']:<12} {r['msg']}")

    actionables = [r for r in results if r["action"] not in ("HOLD",)]
    if not actionables:
        print("[eod_review] all HOLD — no WhatsApp")
        return 0

    lines = [f"Bull-Personal EOD {datetime.utcnow().strftime('%Y-%m-%d')}", ""]
    for r in actionables:
        lines.append(f"• {r['symbol']}: {r['action']} — {r['msg']}")
    lines += ["", "Manuelle Aktion in TR-App nötig."]
    res = send_whatsapp("\n".join(lines))
    print(f"[eod_review] WhatsApp: {res}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
