"""Friday weekly review (runs inside Bull's 06-weekly-review).

Aggregates this week's closed trades from Notion Trade-Journal:
  - winrate, avg Actual R, total R
  - discipline score (penalty for Rule Violation flag and R:R deviations)
Writes a summary page (re-using Pre-Market-Briefs DB with a "Weekly" title) and
sends a German WhatsApp summary.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta

from ..notion import (
    query_db, read_number, read_select, read_text, read_date,
    write_premarket_brief,
)
from ..config import NOTION_DB_JOURNAL, require
from ..notify import send_whatsapp


def main() -> int:
    print(f"[weekly_review] {datetime.utcnow().isoformat(timespec='seconds')}Z")
    db = require("NOTION_DB_JOURNAL", NOTION_DB_JOURNAL)
    today = datetime.utcnow().date()
    monday = today - timedelta(days=today.weekday())
    print(f"[weekly_review] window {monday} → {today}")

    try:
        pages = query_db(db, page_size=100)
    except Exception as exc:
        print(f"[weekly_review] Notion query failed: {exc}")
        return 1

    closed_this_week = []
    for pg in pages:
        status = read_select(pg, "Status") or ""
        if status not in ("Closed Win", "Closed Loss"):
            continue
        exit_d_str = read_date(pg, "Exit Date") or read_date(pg, "Entry Date")
        if not exit_d_str:
            continue
        try:
            d = datetime.fromisoformat(exit_d_str[:10]).date()
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
    rule_violations = 0
    setups_summary: dict[str, int] = {}
    for pg in closed_this_week:
        r = read_number(pg, "Actual R") or 0.0
        status = read_select(pg, "Status") or ""
        setup = read_select(pg, "Setup") or "?"
        setups_summary[setup] = setups_summary.get(setup, 0) + 1
        if status == "Closed Win" or r > 0:
            wins += 1
        rs.append(r)
        # Rule Violation property is checkbox → text "__YES__" / "__NO__" / None
        rv = pg.get("properties", {}).get("Rule Violation", {}).get("checkbox", False)
        if rv:
            rule_violations += 1

    winrate = wins / n * 100
    avg_r = sum(rs) / n
    total_r = sum(rs)
    discipline = max(0.0, 100.0 - rule_violations / n * 100)

    date_iso = today.strftime("%Y-%m-%d")
    md = (
        f"# Wochen-Review {monday} → {today}\n\n"
        f"- Trades: **{n}**\n"
        f"- Winrate: **{winrate:.0f}%** ({wins}/{n})\n"
        f"- avg Actual R: **{avg_r:+.2f}**\n"
        f"- Total R: **{total_r:+.2f}**\n"
        f"- Disziplin-Score: **{discipline:.0f}/100** "
        f"({rule_violations} Rule Violations)\n"
        f"- Setups: " + ", ".join(f"{k}={v}" for k, v in setups_summary.items()) + "\n"
    )

    setups_detail = " · ".join(f"{k}:{v}" for k, v in setups_summary.items())
    try:
        write_premarket_brief(
            date_iso=f"Weekly-{date_iso}",
            n_setups=n,
            setups_detail=setups_detail,
            market_bias="Neutral",
            brief_markdown=md,
        )
    except Exception as exc:
        print(f"[weekly_review] Notion write failed: {exc}")

    wa = (
        f"Bull-Personal Wochen-Review {monday} → {today}\n"
        f"Trades: {n} · Winrate {winrate:.0f}% · avg R {avg_r:+.2f} · Total {total_r:+.2f}R\n"
        f"Disziplin: {discipline:.0f}/100 ({rule_violations} Violations)\n"
        f"Setups: {setups_detail}\n"
        f"Detail-Page in Notion."
    )
    res = send_whatsapp(wa)
    print(f"[weekly_review] WhatsApp: {res}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
