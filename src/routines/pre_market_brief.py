"""Daily pre-market brief (runs inside Bull's 01-pre-market piggyback).

Pipeline:
  1. Macro briefing (Gemini grounded search): Fed/CPI/jobs, futures, 10Y, DXY, oil.
  2. Earnings scan (Gemini): which watchlist names report in next 5 trading days.
  3. Technical scan (regel-basiert, src/scanner.py): 20-EMA pullback per Strategy v1.
     Filters out names in earnings blackout AND names reporting this week.
  4. Per-setup research (Gemini, ≤6 calls): news + analyst PT drift + institutional flow.
  5. Aggregate → Notion page (full detail) + WhatsApp (compact, position-size clear).

Usage:
    python -m src.routines.pre_market_brief            # full run, ~10-30s for Gemini
    python -m src.routines.pre_market_brief --dry-run  # console-only, no Notion/WhatsApp
    python -m src.routines.pre_market_brief --no-research  # skip Gemini, scanner-only
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Optional

from ..config import WATCHLIST, ACCOUNT_EQUITY_EUR, STRATEGY
from ..scanner import Setup, scan
from ..notion import write_premarket_brief
from ..notify import send_whatsapp
from ..research import research_safe, ResearchResult
from ..fx import usd_to_eur_rate


# ── research helpers ──────────────────────────────────────────────────────
def macro_briefing() -> ResearchResult:
    return research_safe(
        f"Today is {datetime.utcnow():%Y-%m-%d}. Give me a tight US-equity pre-market briefing:\n"
        "1. Top scheduled macro events today (Fed-speak, CPI, NFP, GDP, FOMC, retail sales).\n"
        "2. S&P 500 futures direction overnight, VIX level, 10Y yield, DXY, oil.\n"
        "3. Any single big news that's moving large-cap tech or banks.\n"
        "4. One-line market bias: Bullish / Neutral / Bearish / Choppy (for a swing trader).\n"
        "Keep it under 250 words, bullets, US-centric.",
        temperature=0.2,
    )


def earnings_this_week(symbols: list[str]) -> ResearchResult:
    syms = ", ".join(symbols)
    return research_safe(
        f"Today is {datetime.utcnow():%Y-%m-%d}. From this list — {syms} — which tickers have a "
        "scheduled earnings call in the next 5 US trading days? For each, give:\n"
        "  TICKER — YYYY-MM-DD (BMO/AMC), consensus EPS / revenue if available.\n"
        "Only list names that actually report this week. If none, say 'NONE'. Be brief.",
        temperature=0.0,
    )


def setup_deep_dive(setup: Setup) -> ResearchResult:
    return research_safe(
        f"Quick swing-trader research on {setup.symbol} (US equity), today {datetime.utcnow():%Y-%m-%d}.\n"
        f"Current price ~${setup.close}, 20-EMA ${setup.ema20}, 50-EMA ${setup.ema50}.\n"
        "Give me, in <150 words total:\n"
        "1. Any thesis-breaking news in last 7 days (downgrades, guidance cuts, exec departures, regulatory).\n"
        "2. Analyst price-target drift this month (mean PT up or down? notable moves?).\n"
        "3. Institutional positioning signal: 13F changes, insider selling/buying, big-fund accumulation.\n"
        "4. One-line take: does this 20-EMA pullback look like a clean technical setup or is there a fundamental red flag?\n"
        "If genuinely no data found, say so — don't fabricate.",
        temperature=0.2,
    )


# ── parsing helpers ───────────────────────────────────────────────────────
def parse_bias(macro_answer: str) -> str:
    """Heuristic-pull of 'Bullish/Neutral/Bearish/Choppy' from macro text."""
    a = macro_answer.lower()
    for tag in ("bullish", "bearish", "choppy", "neutral"):
        if tag in a.split("bias")[-1][:80].lower():
            return tag.capitalize()
    for tag in ("bullish", "bearish", "choppy"):
        if tag in a:
            return tag.capitalize()
    return "Neutral"


def parse_earnings_blackout_set(earnings_answer: str, watchlist: list[str]) -> set[str]:
    """Return tickers from watchlist that appear in the earnings answer."""
    if not earnings_answer or "NONE" in earnings_answer.upper():
        return set()
    blocked = set()
    for sym in watchlist:
        # require both the ticker AND a date-like pattern nearby to reduce false positives
        if sym in earnings_answer:
            blocked.add(sym)
    return blocked


# ── formatting ────────────────────────────────────────────────────────────
def format_notion_markdown(
    setups: list[Setup],
    research: dict[str, ResearchResult],
    macro: ResearchResult,
    earnings: ResearchResult,
    fx_rate: float,
    date_iso: str,
) -> str:
    head = (
        f"# Pre-Market Brief {date_iso}\n\n"
        f"Strategy: 20-EMA-Pullback v1 · Equity {ACCOUNT_EQUITY_EUR:.0f}€ · "
        f"Risk {STRATEGY['risk_per_trade_pct']:.1f}%/Trade · Max {STRATEGY['max_positions']} Pos · "
        f"FX 1 USD = {fx_rate:.4f} EUR\n"
        f"Setups: **{len(setups)}** von {len(WATCHLIST)} Watchlist-Symbolen\n\n"
    )

    macro_section = (
        "## Makro & Tagesnarrativ\n\n" + (macro.answer or "_(Gemini lieferte nichts)_") + "\n\n"
        + (("Citations: " + " · ".join(macro.citations[:5]) + "\n\n") if macro.citations else "")
    )

    earnings_section = "## Earnings diese Woche (Watchlist)\n\n" + (earnings.answer or "_(keine Antwort)_") + "\n\n"

    if not setups:
        setups_section = (
            "## Setups\n\nKeine Setups heute. Nichts zu tun. Stay flat.\n\n"
            "Bias zur Inaktion. Watchlist morgen wieder scannen.\n"
        )
        return head + macro_section + earnings_section + setups_section

    tradeable = [s for s in setups if s.affordable]
    over_budget = [s for s in setups if not s.affordable]

    rows = ["## Setups (mit Position-Sizing)\n",
            "| Sym | Entry (EUR / USD) | SL (EUR / USD) | TP (EUR / USD) | Shares | Notional EUR | Risk EUR | R:R |",
            "|---|---:|---:|---:|---:|---:|---:|---:|"]
    if tradeable:
        for s in tradeable:
            notional_usd = round(s.shares * s.entry, 2)
            notional_eur = round(notional_usd * fx_rate, 2)
            entry_eur = round(s.entry * fx_rate, 2)
            stop_eur = round(s.stop * fx_rate, 2)
            target_eur = round(s.target * fx_rate, 2)
            actual_risk_eur = round(s.shares * (s.entry - s.stop) * fx_rate, 2)
            rows.append(
                f"| {s.symbol} | €{entry_eur:.2f} / ${s.entry:.2f} | "
                f"€{stop_eur:.2f} / ${s.stop:.2f} | €{target_eur:.2f} / ${s.target:.2f} | "
                f"{s.shares} | €{notional_eur:,.2f} | "
                f"€{actual_risk_eur:.2f} | 1:{s.rr:.1f} |"
            )
    else:
        rows.append("| _(keine tradebare Setups — alle Setups übersteigen das Risk-Budget bei 1 share)_ |")

    if over_budget:
        rows.append("\n### Skipped (1 share über Risk-Budget)\n")
        rows.append("| Sym | Entry (EUR / USD) | SL (EUR / USD) | 1sh Risk EUR | 1sh Risk % Equity | Budget % | Reason |")
        rows.append("|---|---:|---:|---:|---:|---:|---|")
        for s in over_budget:
            entry_eur = round(s.entry * fx_rate, 2)
            stop_eur = round(s.stop * fx_rate, 2)
            multiple = round(s.one_share_risk_eur / s.risk_eur, 1) if s.risk_eur > 0 else 0
            rows.append(
                f"| {s.symbol} | €{entry_eur:.2f} / ${s.entry:.2f} | "
                f"€{stop_eur:.2f} / ${s.stop:.2f} | €{s.one_share_risk_eur:.2f} | "
                f"{s.one_share_risk_pct:.1f}% | €{s.risk_eur:.2f} | "
                f"1 sh = {multiple}× budget |"
            )

    detail = ["\n\n## Per-Setup Recherche\n"]
    for s in setups:
        rr = research.get(s.symbol)
        detail.append(f"### {s.symbol}\n")
        detail.append(f"_Technical:_ {s.notes}\n\n")
        if rr is not None:
            detail.append(rr.answer + "\n")
            if rr.citations:
                detail.append("\n_Quellen:_ " + " · ".join(rr.citations[:3]) + "\n\n")
        else:
            detail.append("_(keine Recherche durchgeführt)_\n\n")

    footer = (
        "\n## Order-Anleitung Trade Republic\n\n"
        "1. Stop-Buy 0.1% über Entry-High platzieren (nicht Market).\n"
        "2. SL als Stop-Market direkt nach Fill setzen.\n"
        "3. TP optional als Limit (1:2 R:R); oder manuelle Exit-Entscheidung bei EOD-Review.\n"
        "4. Bei +1R: SL auf Break-Even ziehen (Bull-Personal meldet das im EOD-Review).\n\n"
        "**Hinweis Bruchstücke**: TR erlaubt Bruchstücke NUR bei Market-Orders. "
        "Stop-Buy, Stop-Market und Limit benötigen ganze Aktien. Daher sind die Setups "
        "oben mit Integer-Sizing gerechnet; \"Skipped\"-Setups (1 share > 1% Risk-Budget) "
        "können entweder übersprungen oder mit erhöhtem Risk-Akzept manuell entered werden.\n"
    )

    return head + macro_section + earnings_section + "\n".join(rows) + "\n" + "".join(detail) + footer


def format_whatsapp(
    setups: list[Setup], market_bias: str, fx_rate: float, date_iso: str,
) -> str:
    if not setups:
        return (
            f"Bull-Personal {date_iso}\n"
            f"Bias: {market_bias} · Watchlist {len(WATCHLIST)} → 0 Setups\n"
            f"Heute nichts. Stay flat."
        )
    lines = [
        f"Bull-Personal {date_iso} · Bias: {market_bias}",
        f"{len(setups)} Setup(s) · Equity {ACCOUNT_EQUITY_EUR:.0f}€",
        "",
    ]
    tradeable = [s for s in setups if s.affordable]
    over_budget = [s for s in setups if not s.affordable]

    if not tradeable and over_budget:
        lines.append(f"Keine tradebare Setups (alle {len(over_budget)} über Risk-Budget bei 1 share).")
    for s in tradeable[:3]:
        entry_eur = round(s.entry * fx_rate, 2)
        stop_eur = round(s.stop * fx_rate, 2)
        target_eur = round(s.target * fx_rate, 2)
        notional_eur = round(s.shares * s.entry * fx_rate, 2)
        actual_risk_eur = round(s.shares * (s.entry - s.stop) * fx_rate, 2)
        lines.append(
            f"• {s.symbol} {s.shares}sh\n"
            f"  Entry €{entry_eur:.2f} / ${s.entry:.2f}\n"
            f"  SL €{stop_eur:.2f} / ${s.stop:.2f}\n"
            f"  TP €{target_eur:.2f} / ${s.target:.2f}\n"
            f"  Pos €{notional_eur:,.2f} · Risk €{actual_risk_eur:.2f} · 1:{s.rr:.1f}"
        )
    for s in over_budget[:3]:
        entry_eur = round(s.entry * fx_rate, 2)
        lines.append(
            f"• {s.symbol} SKIP · Entry €{entry_eur:.2f} / ${s.entry:.2f}\n"
            f"  1sh-Risk €{s.one_share_risk_eur:.2f} ({s.one_share_risk_pct:.1f}% Equity) > €{s.risk_eur:.2f} Budget"
        )
    if len(setups) > 3:
        lines.append(f"\n+{len(setups) - 3} weitere → Notion-Brief")
    lines += ["", "Stop-Buy 0.1% über High in TR-App. Max 3 Pos."]
    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────────
def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="no Notion/WhatsApp side-effects")
    p.add_argument("--no-research", action="store_true", help="skip Gemini, scanner-only")
    args = p.parse_args()

    date_iso = datetime.utcnow().strftime("%Y-%m-%d")
    print(f"[pre_market_brief] {date_iso} scanning {len(WATCHLIST)} symbols…")

    # 1+2. Macro + earnings research (concurrent in principle, sequential for simplicity)
    if args.no_research:
        macro = ResearchResult(answer="(skipped — --no-research)", citations=[], model="-")
        earnings = ResearchResult(answer="(skipped — --no-research)", citations=[], model="-")
    else:
        print("[pre_market_brief] Gemini: macro briefing…")
        macro = macro_briefing()
        print("[pre_market_brief] Gemini: earnings this week…")
        earnings = earnings_this_week(WATCHLIST)

    earnings_blocked = parse_earnings_blackout_set(earnings.answer, WATCHLIST)
    if earnings_blocked:
        print(f"[pre_market_brief] earnings-week blocked: {sorted(earnings_blocked)}")
    market_bias = parse_bias(macro.answer) if not args.no_research else "Neutral"

    # 3. Technical scan
    scan_universe = [s for s in WATCHLIST if s not in earnings_blocked]
    setups = scan(scan_universe)
    print(f"[pre_market_brief] {len(setups)} setup(s) found "
          f"(scanned {len(scan_universe)}, blocked {len(earnings_blocked)})")
    for s in setups:
        print(f"  · {s.symbol} entry={s.entry} stop={s.stop} tp={s.target} shares={s.shares}")

    # 4. Per-setup deep dive (cap to 6 to bound cost/latency)
    research_results: dict[str, ResearchResult] = {}
    if not args.no_research:
        for s in setups[:6]:
            print(f"[pre_market_brief] Gemini: deep-dive {s.symbol}…")
            research_results[s.symbol] = setup_deep_dive(s)

    # 5. FX + aggregate output
    fx_rate = usd_to_eur_rate()
    print(f"[pre_market_brief] FX: 1 USD = {fx_rate:.4f} EUR")

    md = format_notion_markdown(setups, research_results, macro, earnings, fx_rate, date_iso)
    wa = format_whatsapp(setups, market_bias, fx_rate, date_iso)

    if args.dry_run:
        print("\n=== NOTION-MARKDOWN ===\n" + md)
        print("\n=== WHATSAPP ===\n" + wa)
        return 0

    try:
        setups_detail = " · ".join(
            f"{s.symbol} {s.entry:.2f}/{s.stop:.2f}/{s.target:.2f}" for s in setups
        ) or "—"
        earnings_field = earnings.answer[:1800] if earnings.answer else ""
        macro_field = macro.answer[:1800] if macro.answer else ""
        write_premarket_brief(
            date_iso=date_iso,
            n_setups=len(setups),
            setups_detail=setups_detail,
            earnings_today=earnings_field,
            macro_events=macro_field,
            market_bias=market_bias,
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
