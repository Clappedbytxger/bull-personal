"""Friday 22:00 DE weekly review.

Aggregates this week's closed trades from Notion Trade-Journal:
  - winrate, avg R, total R
  - discipline score (R:R = 2.0 ± 0.2 honored? size on plan?)
Writes a summary page (re-using the Pre-Market-Briefs DB with a "Weekly" prefix)
and sends a German WhatsApp summary.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta

from ..notion import (
    query_db, read_number, read_select, read_text, read_title,
    write_premarket_brief,
)
from ..config import NOTION_DB_JOURNAL, require
from ..notify import send_whatsapp


def _date_str(page: dict) -> str:
    d = page.get("properties", {}).get("Datum", {}).get("date") or {}
    return (d.get("start") or "")[:10]


def main() -> int:
    print(f"[weekly_review] {datetime.utcnow().isoformat(timespec='seconds')}Z")
    db = require("NOTION_DB_JOURNAL", NOTION_DB_JOURNAL)
    today = datetime.utcnow().date()
    monday = today - timedelta(days=today.weekday())  # week Monday
    print(f"[weekly_review] window {monday} → {today}")

    try:
        pages = query_db(db, page_size=100)
    except Exception as exc:
        print(f"[weekly_review] Notion query failed: {exc}")
        return 1

    closed_this_week = []
    for pg in pages:
        status = read_select(pg, "Status") or ""
        if status == "Open":
            continue
        d_str = _date_str(pg)
        if not d_str:
            continue
        try:
            d = datetime.fromisoformat(d_str).date()
        except ValueError:
            continue
        if monday <= d <= today:
            closed_this_week.append(pg)

    n = len(closed_this_week)
    print(f"[weekly_review] {n} closed trade(s) this week")
    if n == 0:
        text = (
            f"Bull-Personal Wochen-Review {monday} → {today}\n"
            f"0 abgeschlossene Trades.\n"
            f"Disziplin: nichts zu bewerten. Watchlist weiter scannen."
        )
        send_whatsapp(text)
        return 0

    rs: list[float] = []
    wins = 0
    rr_violations = 0
    setups_summary: dict[str, int] = {}
    for pg in closed_this_week:
        r = read_number(pg, "R Multiple") or 0.0
        status = read_select(pg, "Status") or ""
        setup = read_select(pg, "Setup") or "?"
        setups_summary[setup] = setups_summary.get(setup, 0) + 1
        if status.startswith("Closed-Win") or r > 0:
            wins += 1
        rs.append(r)
        # discipline: planned R:R = 2.0 — flag if abs(R) > 2.5 (overshoot) or 0 < R < 0.8 (early exit)
        if (r > 2.5) or (0 < r < 0.8):
            rr_violations += 1

    winrate = wins / n * 100
    avg_r = sum(rs) / n
    total_r = sum(rs)
    discipline = max(0.0, 100.0 - rr_violations / n * 100)

    date_iso = today.strftime("%Y-%m-%d")
    md = (
        f"# Wochen-Review {monday} → {today}\n\n"
        f"- Trades: **{n}**\n"
        f"- Winrate: **{winrate:.0f}%** ({wins}/{n})\n"
        f"- avg R: **{avg_r:+.2f}**\n"
        f"- Total R: **{total_r:+.2f}**\n"
        f"- Disziplin-Score: **{discipline:.0f}/100** "
        f"({rr_violations} R:R-Abweichungen)\n"
        f"- Setups: " + ", ".join(f"{k}={v}" for k, v in setups_summary.items()) + "\n"
    )

    detail_lines = ["\n## Trade-Details\n", "| Sym | Datum | R | Status |", "|---|---|---:|---|"]
    for pg in closed_this_week:
        sym = (read_text(pg, "Symbol") or read_title(pg).split()[0]).upper()
        detail_lines.append(
            f"| {sym} | {_date_str(pg)} | {read_number(pg, 'R Multiple') or 0:+.2f} "
            f"| {read_select(pg, 'Status') or '?'} |"
        )
    md += "\n".join(detail_lines) + "\n"

    try:
        write_premarket_brief(f"Weekly-{date_iso}", n, "—", md)
    except Exception as exc:
        print(f"[weekly_review] Notion write failed: {exc}")

    wa = (
        f"Bull-Personal Wochen-Review {monday} → {today}\n"
        f"Trades: {n} · Winrate {winrate:.0f}% · avg R {avg_r:+.2f} · Total {total_r:+.2f}R\n"
        f"Disziplin: {discipline:.0f}/100 ({rr_violations} Abweichungen)\n"
        f"Setups: " + ", ".join(f"{k}={v}" for k, v in setups_summary.items()) + "\n"
        f"Detail-Page in Notion."
    )
    res = send_whatsapp(wa)
    print(f"[weekly_review] WhatsApp: {res}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
